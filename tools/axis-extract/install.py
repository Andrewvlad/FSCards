#!/usr/bin/env python3
"""Install extract.py's staged /tmp/axis_out sets over assets/diagrams, pixel-aware.

A repo file is replaced only when the staged card's decoded pixels differ by more
than RECUT_TOLERANCE. Byte comparison would re-install every card whenever the
runner's libwebp encodes identical art to different bytes, and a regenerated source
PDF re-rasterizes unchanged cards (anti-alias greys drift, no ink flips): both bury
a real re-cut under hundreds of phantom diffs. Axis line art carries hard black ink,
so a real edit flips pixels to a 255 delta, far above the re-render drift (well under
130 across 2-way's 14 unchanged blocks, vs 255 for the one that changed). Repo files
absent from the staging are pool drops and get deleted, refused wholesale when the
staging holds under half the installed set (a botched extraction must not wipe a set).
Hand-mended files (CF4 figures/H) regress to fresh pipeline output by design (see
README), reject the change from the extract PR to keep the graft.
"""
import glob, os, shutil, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import JOBS, OUT

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
sys.path.insert(0, f"{ROOT}/tools")
import legacy_archive as la
SRC = f"{ROOT}/assets/sources/axis"
DEP_ROOT = f"{SRC}/legacy/deprecated"    # superseded art parked as <disc>/<key>_dep-<year> on a re-cut
MIN_STAGED_RATIO = 0.5   # refuse orphan deletes when staging covers under half the installed set (botched run guard)
RECUT_TOLERANCE = 200    # max channel delta of a re-render diff; real Axis ink edits flip to 255

pixels = lambda f: np.asarray(Image.open(f).convert("RGB"))
# Pool order: randoms A-Z first, then blocks numerically (10 after 2)
pool_order = lambda k: (k[0].isdigit(), int("".join(filter(str.isdigit, k)) or "0"), k)
# Card/figure rel paths -> pool keys, deduped (a card and its derived figure share one key)
to_keys = lambda rels: sorted(dict.fromkeys(os.path.splitext(os.path.basename(r))[0] for r in rels), key=pool_order)

total = 0
all_installed, all_deleted, all_tolerated, all_refused, all_archived = [], [], [], [], []
# JOBS keys, not listdir: stale staging from a renamed discipline must not install
for d in sorted(JOBS):
    od = os.path.join(OUT, d)
    if not os.path.isdir(od):
        continue   # discipline not part of this extraction run
    repo_dir = f"{ROOT}/assets/diagrams/{d}/Axis"
    staged = sorted(glob.glob(f"{od}/*.webp") + glob.glob(f"{od}/figures/*.webp"))
    staged_rels = {os.path.relpath(s, od) for s in staged}
    repo_rels = {os.path.relpath(f, repo_dir)
                 for f in glob.glob(f"{repo_dir}/*.webp") + glob.glob(f"{repo_dir}/figures/*.webp")}
    installed, tolerated, archived, identical = [], [], [], 0
    for src in staged:
        rel = os.path.relpath(src, od)
        dst = os.path.join(repo_dir, rel)
        exists = os.path.exists(dst)
        if exists:
            sp, dp = pixels(src), pixels(dst)
            if np.array_equal(sp, dp):
                identical += 1
                continue
        # Regenerated PDFs re-rasterize unchanged cards (anti-alias drift, no ink flip): keep repo render
        if exists and sp.shape == dp.shape:
            md = int(np.abs(sp.astype(int) - dp.astype(int)).max())
            if md < RECUT_TOLERANCE:
                tolerated.append((rel, md))
                continue
        if exists and not rel.startswith("figures/"):  # real change: archive the outgoing diagram (figures are derived)
            archived.append(la.archive_image(DEP_ROOT, d, rel, dst))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        installed.append(rel)
    # Refused wholesale under the half-set guard or when a key category staged nothing (botched run)
    deleted = []
    deletable, refused = la.orphan_guard(staged_rels, repo_rels, MIN_STAGED_RATIO)
    for rel in deletable:
        if not rel.startswith("figures/"):    # archive the outgoing diagram only (figures are derived)
            archived.append(la.archive_image(DEP_ROOT, d, rel, os.path.join(repo_dir, rel)))
        os.remove(os.path.join(repo_dir, rel))
        deleted.append(rel)
    total += len(installed) + len(deleted)
    # Per-discipline detail to stderr: shown live in the action log, kept out of install.log (PR body)
    print(f"{d}: {identical} identical, {len(installed)} installed, {len(deleted)} deleted"
          + (f", {len(tolerated)} re-render" if tolerated else "")
          + (f", {len(archived)} archived" if archived else ""), file=sys.stderr)
    for rel in installed:
        print(f"    installed {rel}", file=sys.stderr)
    for rel in deleted:
        print(f"    deleted {rel} (key left the pool)", file=sys.stderr)
    for rel, md in tolerated:
        print(f"    re-render {rel} (maxd {md} < {RECUT_TOLERANCE}, kept repo render)", file=sys.stderr)
    for rel in archived:
        print(f"    archived {rel}", file=sys.stderr)
    if refused:
        print(f"    !! refusing {len(refused)} deletion(s), staging holds under half the installed set", file=sys.stderr)
    all_installed += to_keys(installed)
    all_deleted   += to_keys(deleted)
    all_tolerated += to_keys(r for r, _ in tolerated)
    all_refused   += to_keys(refused)
    all_archived  += archived

# Grouped summary to stdout - the only thing tee'd into install.log, so the PR body shows just this
print(f"Total: {total} file(s) changed (including figures)")
if all_installed:
    print(f"- New/updated ({len(all_installed)}): {', '.join(all_installed)}")
if all_deleted:
    print(f"- Deleted ({len(all_deleted)}): {', '.join(all_deleted)} (key left the pool)")
if all_tolerated:
    print(f"- Kept ({len(all_tolerated)}): {', '.join(all_tolerated)} (change was not noticed)")
if all_archived:
    print(f"- Archived ({len(all_archived)}) to legacy/deprecated/: {', '.join(os.path.basename(a) for a in all_archived)}")
if all_refused:
    print(f"- [ERROR] Refusing {len(all_refused)} deletions, staging holds under half the set, review manually: {', '.join(all_refused)}")