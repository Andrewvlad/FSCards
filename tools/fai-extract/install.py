#!/usr/bin/env python3
"""Install the staged FAI sets over assets/diagrams/<disc>/FAI, pixel-aware.

Twin of axis-extract/install.py (same re-render tolerance + half-set orphan-delete guard), with
the two merges the FAI set needs:
  - 4-way R/Bundy (rext.py stages it into the FS out dir) installs like any other card.
  - The indoor 8-way set (usis.py) ships MERGED into 8-way/FAI: only the cells whose indoor art
    differs from the outdoor card install, renamed <key>_indoor.webp, plus the two
    starting-formation reference cards (indoor-only, no outdoor counterpart). A cell byte-equal
    to outdoor (every key but 13/17/20 today) is not shipped, so the indoor-variant set is read
    from the art, never a hardcoded 13/17/20 list.

A repo file is replaced only when the staged pixels differ by more than RECUT_TOLERANCE, so the
byte drift of a re-encode or a re-rendered source never floods the diff - a real ink edit flips to
255. Run extract.py (+ rext.py) and/or usis.py first - whichever staging dirs exist get installed,
so a fs.pdf-only or indoor.pdf-only re-extract touches only its half.
"""
import glob, os, shutil, sys
import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
sys.path.insert(0, f"{ROOT}/tools")
import legacy_archive as la
FAI_OUT = "/tmp/faiext/out"            # extract.py (4-way, 8-way) + rext.py (4-way R)
USIS_OUT = "/tmp/usisext/8-way/USIS"   # usis.py (all indoor 8-way cells + starting formations)
SRC = f"{ROOT}/assets/sources/fai"
DEP_ROOT = f"{SRC}/legacy/deprecated"  # superseded art parked as <disc>/<key>_dep-<year> on a re-cut
MIN_STAGED_RATIO = 0.5   # refuse orphan deletes when staging covers under half the set (botched run guard)
RECUT_TOLERANCE = 200    # max channel delta of a re-render/re-encode diff - real ink edits flip to 255
INDOOR_NOISE = 40        # per-channel delta a re-render's anti-alias jitter stays under
INDOOR_MINDIFF = 300     # pixels past INDOOR_NOISE for an indoor cell to count a variant (13/17/20 are 2.5k+, jitter 0)

pixels = lambda f: np.asarray(Image.open(f).convert("RGB"))
# Pool order: randoms A-Z first, then blocks numerically (10 after 2)
pool_order = lambda k: (k[0].isdigit(), int("".join(filter(str.isdigit, k)) or "0"), k)
to_keys = lambda rels: sorted(dict.fromkeys(os.path.splitext(os.path.basename(r))[0] for r in rels), key=pool_order)
is_indoor = lambda rel: "_indoor" in rel or os.path.basename(rel).startswith("starting-formation")

def indoor_variant(ind, outd):
    """True when an indoor cell's art differs from its outdoor card by more than INDOOR_MINDIFF
    pixels past the per-channel noise floor -- a re-render's jitter scores ~0, 13/17/20 score 2.5k+."""
    if ind.shape != outd.shape:
        return True
    changed = (np.abs(ind.astype(int) - outd.astype(int)).max(2) > INDOOR_NOISE).sum()
    return int(changed) > INDOOR_MINDIFF

def install_pairs(pairs, repo_dir, repo_rels, disc, guard_categories=True):
    """Copy each (repo-relative dst, staged src) whose pixels differ from the repo file by more
    than RECUT_TOLERANCE - delete the orphan rels (repo files this run did not produce), refused
    wholesale under the half-set guard or when a key category staged nothing (la.orphan_guard).
    The old art of every replaced or deleted card is parked under DEP_ROOT as <key>_dep-<year>
    (the re-cut year, diagrams only). Returns (installed, deleted, tolerated, refused,
    archived) rels."""
    installed, tolerated, deleted, refused, archived = [], [], [], [], []
    for rel, src in pairs:
        dst = os.path.join(repo_dir, rel)
        existed = os.path.exists(dst)
        if existed:
            sp, dp = pixels(src), pixels(dst)
            if np.array_equal(sp, dp):
                continue
            if sp.shape == dp.shape:
                md = int(np.abs(sp.astype(int) - dp.astype(int)).max())
                if md < RECUT_TOLERANCE:
                    tolerated.append((rel, md)); continue
        if existed and not rel.startswith("figures/"):  # real change: archive the outgoing diagram (figures are derived)
            archived.append(la.archive_image(DEP_ROOT, disc, rel, dst))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        installed.append(rel)
    staged_rels = {rel for rel, _ in pairs}
    deletable, refused = la.orphan_guard(staged_rels, repo_rels, MIN_STAGED_RATIO, guard_categories)
    for rel in deletable:
        if not rel.startswith("figures/"):     # archive the outgoing diagram only (figures are derived)
            archived.append(la.archive_image(DEP_ROOT, disc, rel, os.path.join(repo_dir, rel)))
        os.remove(os.path.join(repo_dir, rel)); deleted.append(rel)
    return installed, tolerated, deleted, refused, archived

def report(disc, installed, tolerated, deleted, refused, archived):
    print(f"{disc}: {len(installed)} installed, {len(deleted)} deleted"
          + (f", {len(tolerated)} re-render" if tolerated else "")
          + (f", {len(archived)} archived" if archived else ""), file=sys.stderr)
    for rel in installed: print(f"    installed {rel}", file=sys.stderr)
    for rel in deleted: print(f"    deleted {rel} (left the set)", file=sys.stderr)
    for rel, md in tolerated: print(f"    re-render {rel} (maxd {md} < {RECUT_TOLERANCE}, kept repo)", file=sys.stderr)
    for rel in archived: print(f"    archived {rel}", file=sys.stderr)
    if refused: print(f"    !! refusing {len(refused)} deletion(s), staging under half the set", file=sys.stderr)

all_installed, all_deleted, all_tolerated, all_refused, all_archived = [], [], [], [], []

# ---- FS sets (extract.py 4-way + 8-way, rext.py R): outdoor cards only ----
for disc in ("4-way", "8-way"):
    od = f"{FAI_OUT}/{disc}"
    if not os.path.isdir(od):
        continue   # this discipline not part of the run (fs.pdf unchanged)
    repo_dir = f"{ROOT}/assets/diagrams/{disc}/FAI"
    staged = sorted(glob.glob(f"{od}/*.webp") + glob.glob(f"{od}/figures/*.webp"))
    pairs = [(os.path.relpath(s, od), s) for s in staged]
    # Orphans among OUTDOOR cards only -- the 8-way dir also holds usis _indoor/starting files
    repo_rels = {os.path.relpath(f, repo_dir)
                 for f in glob.glob(f"{repo_dir}/*.webp") + glob.glob(f"{repo_dir}/figures/*.webp")
                 if not is_indoor(os.path.relpath(f, repo_dir))}
    res = install_pairs(pairs, repo_dir, repo_rels, disc)
    report(disc, *res)
    all_installed += to_keys(res[0]); all_tolerated += to_keys(r for r, _ in res[1])
    all_deleted += to_keys(res[2]);   all_refused += to_keys(res[3]); all_archived += res[4]

# ---- indoor 8-way (usis.py), merged into 8-way/FAI as <key>_indoor + starting formations ----
if os.path.isdir(USIS_OUT):
    repo_dir = f"{ROOT}/assets/diagrams/8-way/FAI"
    pairs = []
    for src in sorted(glob.glob(f"{USIS_OUT}/*.webp") + glob.glob(f"{USIS_OUT}/figures/*.webp")):
        rel = os.path.relpath(src, USIS_OUT)
        base = os.path.basename(rel)[:-5]
        if base.startswith("starting-formation"):
            pairs.append((rel, src))                       # indoor-only reference, always shipped
            continue
        outdoor = os.path.join(repo_dir, rel)              # compare against the outdoor card
        if not os.path.exists(outdoor):
            continue
        if indoor_variant(pixels(src), pixels(outdoor)):
            d = os.path.dirname(rel)
            pairs.append((os.path.join(d, f"{base}_indoor.webp"), src))
    repo_indoor = {os.path.relpath(f, repo_dir)
                   for f in glob.glob(f"{repo_dir}/*.webp") + glob.glob(f"{repo_dir}/figures/*.webp")
                   if is_indoor(os.path.relpath(f, repo_dir))}
    # Non-contiguous indoor-variant subset: empty staging is legitimate, so no category-wipe guard
    res = install_pairs(pairs, repo_dir, repo_indoor, "8-way", guard_categories=False)
    report("8-way indoor", *res)
    all_installed += to_keys(res[0]); all_tolerated += to_keys(r for r, _ in res[1])
    all_deleted += to_keys(res[2]);   all_refused += to_keys(res[3]); all_archived += res[4]

# Grouped summary to stdout - the only thing tee'd into install.log, so the PR body shows just this
total = len(all_installed) + len(all_deleted)
print(f"Total: {total} file(s) changed (including figures)")
if all_installed: print(f"- New/updated ({len(all_installed)}): {', '.join(all_installed)}")
if all_deleted:   print(f"- Deleted ({len(all_deleted)}): {', '.join(all_deleted)} (left the set)")
if all_tolerated: print(f"- Kept ({len(all_tolerated)}): {', '.join(all_tolerated)} (change was not noticed)")
if all_archived:  print(f"- Archived ({len(all_archived)}) to legacy/deprecated/: {', '.join(os.path.basename(a) for a in all_archived)}")
if all_refused:   print(f"- [ERROR] Refusing {len(all_refused)} deletions, staging under half the set: {', '.join(all_refused)}")
