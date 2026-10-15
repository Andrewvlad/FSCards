#!/usr/bin/env python3
"""Log a USPA SCM revision: list each changed chapter's renamed, removed, added and moved
formations, read by key from its pool pages' text layer, then diff the rest of its text against the
edition it replaces. Insert the month's section at the top of the legacy README and print it for
the PR body.

Usage: log_revision.py <old.pdf> <new.pdf> [<old.pdf> <new.pdf> ...]
Each new PDF is its legacy archive copy, which the README section links to.
"""
import difflib, html, json, math, os, re, subprocess, sys
from collections import Counter
from datetime import date
import find_pages

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
SOURCES = "assets/sources/uspa"
LEGACY = os.path.join(ROOT, SOURCES, "legacy")
CHAPTERS = json.load(open(os.path.join(ROOT, "tools/uspa_sources.json")))["chapters"]
FOOTER = re.compile(r"SKYDIVER.S COMPETITION MANUAL", re.IGNORECASE)
PRINTED_DATE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})", re.IGNORECASE)
WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>')
KEY = re.compile(r"[A-Z]|\d{1,2}")
TOC_LEADER = re.compile(r"\.{3,}")
SECTION_NUMBER = re.compile(r"^\d+\.(?:\d+\.?)*\s+")
HYPHEN_BREAK = re.compile(r"(\w)- (\w)")
DISCIPLINES = {("FS", 2): "2-Way", ("FS", 4): "4-Way", ("FS", 6): "6-Way Speed", ("FS", 8): "8-Way", ("FS", 10): "10-Way Speed",
               ("FS", 16): "16-Way", ("VFS", 2): "VFS 2-Way", ("VFS", 4): "VFS 4-Way", ("MFS", 2): "MFS 2-Way"}
NOUNS = ("Random", "Block", "Formation")


def page_lines(pdf):
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    return [[" ".join(line.split()) for line in page.splitlines() if line.strip()] for page in text.split("\f")[:-1]]


def printed_date(pages):
    footers = " ".join(line for lines in pages for line in lines if FOOTER.search(line))
    dates = Counter(f"{month.title()} {year}" for month, year in PRINTED_DATE.findall(footers))
    return dates.most_common(1)[0][0] if dates else None


def rule_lines(pages, pool_pages):
    """Each page's lines minus footers and running headers, with the pool pages left empty."""
    pages = [[line for line in lines if not FOOTER.search(line)] for lines in pages]
    repeated = Counter(folded for lines in pages for folded in {line.casefold() for line in lines})
    return [[] if number in pool_pages else [line for line in lines if repeated[line.casefold()] <= len(pages) / 2]
            for number, lines in enumerate(pages, 1)]


def paged_lines(pages):
    return [(line, page) for page, lines in enumerate(pages, 1) for line in lines if not TOC_LEADER.search(line)]


def strip_numbers(block):
    return [SECTION_NUMBER.sub("", line) for line, _ in block]


def words(block):
    return HYPHEN_BREAK.sub(r"\1\2", " ".join(strip_numbers(block))).casefold()


def mark(sign, block):
    return [f"{sign} {line} ({page})" for line, page in block]


def text_diff(old_pages, new_pages):
    old, new = paged_lines(old_pages), paged_lines(new_pages)
    matcher = difflib.SequenceMatcher(None, strip_numbers(old), strip_numbers(new), autojunk=False)
    hunks, previous_end = [], None
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal" or words(old[old_start:old_end]) == words(new[new_start:new_end]):
            continue
        changed = mark("-", old[old_start:old_end]) + mark("+", new[new_start:new_end]) + mark(" ", new[new_end:new_end + 1])
        if new_start - 1 == previous_end:
            hunks[-1] += changed
        else:
            hunks.append(mark(" ", new[max(new_start - 1, 0):new_start]) + changed)
        previous_end = new_end
    return "\n\n".join("\n".join(hunk) for hunk in hunks)


def page_boxes(pdf):
    """Each page's word boxes, (x0, y0, x1, y1, text) in points."""
    document = subprocess.run(["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True, check=True).stdout
    return [[(*map(float, corners), html.unescape(text)) for *corners, text in WORD.findall(page)] for page in document.split("<page ")[1:]]


def rows(boxes):
    """Word boxes grouped into text lines, top to bottom, each left to right."""
    lines = []
    for box in sorted(boxes, key=lambda box: (box[1], box[0])):
        if lines and abs(lines[-1][0][1] - box[1]) <= 2:
            lines[-1].append(box)
        else:
            lines.append([box])
    return [sorted(line) for line in lines]


def joined(line):
    return " ".join(box[4] for box in line)


def cell_names(page, name_height):
    """{key: its cell's name lines} for one pool page. Keys are the page's tallest lone letters and
    numbers, each heading a cell that runs right to the next key and down to the next key row or the
    footer. Names share the "Inter" label's height, between the rotation labels' and the keys'."""
    height = lambda box: box[3] - box[1]
    footer = min((line[0][1] for line in rows(page) if PRINTED_DATE.search(joined(line))), default=math.inf)
    keys = [box for box in page if KEY.fullmatch(box[4])]
    tallest = max(map(height, keys), default=0)
    key_rows = rows([box for box in keys if height(box) > tallest - 0.5])
    names = [box for box in page if abs(height(box) - name_height) < 0.6 and box[3] < footer]
    cells = {}
    for row, bottom in zip(key_rows, [next_row[0][1] for next_row in key_rows[1:]] + [footer]):
        for key, right in zip(row, [next_key[0] for next_key in row[1:]] + [math.inf]):
            inside = [box for box in names if row[0][1] < box[1] < bottom and key[0] <= (box[0] + box[2]) / 2 < right]
            cells[key[4]] = [joined(line) for line in rows(inside)]
    return cells


def pools(pdf):
    """({(discipline, noun): {key: name}} for every pool the chapter prints, a block named by its
    first and last formation, and the pages those pools fill."""
    boxes = page_boxes(pdf)
    name_height = Counter(round(box[3] - box[1], 1) for page in boxes for box in page if box[4] == "Inter").most_common(1)[0][0]
    located = find_pages.locate(pdf)
    pages = {}
    for number, (style, width, _) in sorted(located.items()):
        style = style or "FS"
        pages.setdefault(DISCIPLINES.get((style, width), f"{style} {width}-Way"), []).append(number)
    # The Collegiate 2-way randoms page has printed no appendix subtitle since March 2022, so take the page after its blocks
    if "2-Way" in pages and all(located[number][2] != "random" for number in pages["2-Way"]):
        pages["2-Way"].append(max(pages["2-Way"]) + 1)
    found = {}
    for discipline, numbers in pages.items():
        for number in numbers:
            for key, lines in cell_names(boxes[number - 1], name_height).items():
                if "Inter" in lines:
                    first, last = lines.index("Inter"), len(lines) - lines[::-1].index("Inter")
                    found.setdefault((discipline, "Block"), {})[key] = f"{' '.join(lines[:first])} - {' '.join(lines[last:])}"
                elif lines:
                    found.setdefault((discipline, "Formation" if key.isdigit() else "Random"), {})[key] = " ".join(lines)
    in_order = {pool: dict(sorted(names.items(), key=lambda item: (len(item[0]), item[0]))) for pool, names in found.items()}
    return in_order, {number for numbers in pages.values() for number in numbers}


def pool_changes(noun, old, new):
    """One pool's renames in place, removals, runs of moved keys and additions. Names are matched
    across editions, so a removal reads as one line and the shift it causes as another."""
    gone = [key for key in old if old[key] != new.get(key)]
    came = [key for key in new if new[key] != old.get(key)]
    moved = []
    for key in list(gone):
        match = next((other for other in came if new[other] == old[key]), None)
        if match:
            moved.append((key, match))
            gone.remove(key)
            came.remove(match)
    lines = [f"{noun} {key} changed from *{old[key]}* to *{new[key]}*" for key in gone if key in came]
    lines += [f"{noun} {key}, *{old[key]}*, removed" for key in gone if key not in came]
    old_index, new_index = {key: index for index, key in enumerate(old)}, {key: index for index, key in enumerate(new)}
    runs = []
    for old_key, new_key in moved:
        if runs and (old_index[old_key], new_index[new_key]) == (old_index[runs[-1][-1][0]] + 1, new_index[runs[-1][-1][1]] + 1):
            runs[-1].append((old_key, new_key))
        else:
            runs.append([(old_key, new_key)])
    for run in runs:
        (first_old, first_new), (last_old, last_new) = run[0], run[-1]
        if len(run) == 1:
            lines.append(f"{noun} {first_old}, *{old[first_old]}*, is now {first_new}")
        else:
            joint = " and " if len(run) == 2 else " to "
            lines.append(f"{noun}s {first_old}{joint}{last_old} are now {first_new}{joint}{last_new}")
    lines += [f"{noun} {key}, *{new[key]}*, added" for key in came if key not in gone]
    return lines


def formation_changes(old_pools, new_pools):
    lines = []
    for discipline in dict.fromkeys(discipline for discipline, _ in [*new_pools, *old_pools]):
        changes = [change for noun in NOUNS for change in pool_changes(noun, old_pools.get((discipline, noun), {}), new_pools.get((discipline, noun), {}))]
        if changes:
            lines += [f"- {discipline}"] + [f"  - {change}" for change in changes]
    return "\n".join(lines)


def compare(old_pdf, new_pdf):
    new_lines = page_lines(new_pdf)
    if not os.path.exists(old_pdf):
        return None, printed_date(new_lines), "First archived edition."
    old_lines = page_lines(old_pdf)
    (old_pools, old_pages), (new_pools, new_pages) = pools(old_pdf), pools(new_pdf)
    formations = formation_changes(old_pools, new_pools)
    rules = text_diff(rule_lines(old_lines, old_pages), rule_lines(new_lines, new_pages))
    sections = (["#### Formations", formations] if formations else []) + (["#### Rules", f"```diff\n{rules}\n```"] if rules else [])
    return printed_date(old_lines), printed_date(new_lines), "\n\n".join(sections) or "No text changes."


def main(pdfs):
    chapters = [(new_pdf, *compare(old_pdf, new_pdf)) for old_pdf, new_pdf in zip(pdfs[::2], pdfs[1::2])]
    # Printed date, else the fetch month when the footer has none or didn't move
    month = next((new_date for _, old_date, new_date, _ in chapters if new_date and new_date != old_date), date.today().strftime("%B %Y"))
    readme_parts, pr_parts = [f"## {month}"], [f"## {month}"]
    for new_pdf, _, _, body in chapters:
        title = CHAPTERS[f"{SOURCES}/{os.path.basename(new_pdf)}"]["title"]
        archived = os.path.relpath(new_pdf, LEGACY)
        readme_parts += [f"### {title} ([`{archived}`]({archived}))", body]
        pr_parts += [f"### {title} (`{os.path.relpath(new_pdf, ROOT)}`)", body]
    readme_path = os.path.join(LEGACY, "README.md")
    readme = open(readme_path).read()
    top = readme.index("\n## ") + 1
    with open(readme_path, "w") as file:
        file.write(readme[:top] + "\n\n".join(readme_parts) + "\n\n" + readme[top:])
    print("\n\n".join(pr_parts))


if __name__ == "__main__":
    main(sys.argv[1:])
