#!/usr/bin/env python3
"""Fetch the current USPA SCM chapter PDFs (Ch.9 FS + Ch.7 Collegiate), the
sources behind the USPA image sets, into a directory so a workflow can diff them
against the committed copies under assets/sources/uspa/.

Unlike the Axis sets (stable pinned URLs in axis_sources.json), the SCM chapters
live in an S3-backed DnnSharp folder on uspa.org and are only reachable through a
per-file LinkClick token the page builds server-side - there is no pinnable
direct path. So this script *discovers* the download URL each run from the live
SCM page, walking the Evotiva file-library API by folder/file NAME
(tools/uspa_sources.json). Resolving by name is what makes it future-proof: a
yearly edition swap, a new file id, or a rotated token are all re-resolved from
the page, never hardcoded. (Confirmed durable against the Internet Archive: the
same LinkClick URL has served successive editions across years.)

Output: writes each fetched chapter into --out-dir by its committed basename and
prints a JSON report (changed / failed / per-file detail) the workflow parses.
No third-party deps - stdlib urllib only.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.error
import urllib.request as request
from http.cookiejar import CookieJar

# Browser UA: uspa.org (Cloudflare) 403s the default urllib agent
UA = "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0"
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
CONFIG = os.path.join(ROOT, "tools/uspa_sources.json")
API = "/API/Evotiva-UserFiles/GetItemsServices/GetItems"
DOWNLOAD = "/API/Evotiva-UserFiles/FileActionsServices/DownloadFileInline"
TIMEOUT = 120


def http(opener, url, headers=None, data=None, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
            with opener.open(req, timeout=TIMEOUT) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def scrape_context(opener, page_url):
    """Pull the DNN antiforgery token, Evotiva module id, tab id and root folder
    id out of the SCM page - everything the file-library API needs to authorize."""
    html = http(opener, page_url).decode("utf-8", "replace")
    def need(pat, what):
        m = re.search(pat, html)
        if not m:
            raise RuntimeError(f"could not scrape {what} from {page_url} (page layout changed?)")
        return m.group(1)
    return {
        "rvt": need(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', "verification token"),
        "moduleId": need(r'dnn_ctr(\d+)_View_pnlEvotivaFilesContainer', "Evotiva module id"),
        "tabId": need(r'"tabId"\s*:\s*(\d+)', "tab id"),
        "root": need(r'rootFolderId:\s*(\d+)', "root folder id"),
        "origin": "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(page_url)),
    }


def api_headers(ctx):
    return {"ModuleId": ctx["moduleId"], "TabId": ctx["tabId"],
            "RequestVerificationToken": ctx["rvt"], "Accept": "application/json"}


def list_items(opener, ctx, item_id):
    q = urllib.parse.urlencode({
        "itemId": item_id, "rootItemId": ctx["root"], "sortExpression": "ItemName,false",
        "searchText": "", "searchTags": "", "take": 200, "skip": 0, "page": 1, "pageSize": 200})
    url = ctx["origin"] + API + "?" + q
    return json.loads(http(opener, url, api_headers(ctx)).decode("utf-8", "replace")).get("Data", [])


def find_chapter(opener, ctx, folder_name, file_name):
    """Locate a chapter file by name: prefer the configured folder, else recurse
    every folder (one level) so a folder rename still resolves the file."""
    root = list_items(opener, ctx, ctx["root"])
    def in_folder(items):
        return next((it for it in items if not it["IsFolder"] and it["ItemName"] == file_name), None)
    hit = in_folder(root)
    if hit:
        return hit
    folders = [it for it in root if it["IsFolder"] and not it.get("IsGoBack")]
    folders.sort(key=lambda it: it["ItemName"] != folder_name)  # configured folder first
    for fol in folders:
        hit = in_folder(list_items(opener, ctx, fol["ItemID"]))
        if hit:
            return hit
    return None


def discover(opener, ctx, folder_name, file_name):
    """Resolve a chapter's current LinkClick download URL + its metadata."""
    item = find_chapter(opener, ctx, folder_name, file_name)
    if not item:
        raise RuntimeError(f"{file_name} not found under {folder_name} (renamed?)")
    link = json.loads(http(opener, ctx["origin"] + DOWNLOAD, {**api_headers(ctx),
        "Content-Type": "application/x-www-form-urlencoded"},
        data=f"ItemId={item['ItemID']}".encode()).decode("utf-8", "replace"))
    return {"url": urllib.parse.urljoin(ctx["origin"], link), "itemId": item["ItemID"],
            "size": item.get("SizeBytes"), "modified": item.get("LastModifiedDateTime")}


def is_pdf(data):
    return bool(data) and data[:1024].find(b"%PDF") != -1


def process(opener, ctx, path, cfg, out_dir):
    detail = {"slug": cfg["slug"]}
    try:
        found = discover(opener, ctx, cfg["folder"], cfg["file"])
        detail.update(itemId=found["itemId"], size=found["size"], modified=found["modified"])
        data = http(opener, found["url"])
    except Exception as e:
        detail["status"] = "failed"; detail["note"] = str(e)
        return detail
    if not is_pdf(data):
        detail["status"] = "failed"; detail["note"] = "fetched bytes are not a PDF (bot wall?)"
        return detail
    detail["bytes"] = len(data)

    committed = os.path.join(ROOT, path)
    prior = open(committed, "rb").read() if os.path.exists(committed) else None
    detail["status"] = "same" if prior == data else "changed"
    if detail["status"] == "changed":
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, os.path.basename(path)), "wb") as f:
            f.write(data)
    return detail


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default="fetched", help="where changed PDFs are written")
    ap.add_argument("--only", help="only process this committed path")
    args = ap.parse_args()

    conf = json.load(open(CONFIG))
    chapters = conf["chapters"]
    if args.only:
        chapters = {args.only: chapters[args.only]}

    opener = request.build_opener(request.HTTPCookieProcessor(CookieJar()))
    try:
        ctx = scrape_context(opener, conf["page"])
    except Exception as e:  # USPA unreachable / page changed - nothing to discover against
        report = {"changed": [], "failed": True, "setupError": str(e), "details": {}}
        print(json.dumps(report, indent=2))
        return 0

    details = {path: process(opener, ctx, path, cfg, args.out_dir) for path, cfg in chapters.items()}
    report = {
        "changed": [p for p, d in details.items() if d["status"] == "changed"],
        "failed": any(d["status"] == "failed" for d in details.values()),
        "details": details,
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
