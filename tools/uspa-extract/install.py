#!/usr/bin/env python3
"""Install the staged /tmp/fsx_out sets over assets/diagrams/<d>/USPA, pixel-aware.

Twin of axis-extract/install.py - same reasoning. A repo file is replaced only when the
staged card's decoded pixels differ by more than RECUT_TOLERANCE, so the byte drift of a
re-encode (or the anti-alias jitter of a re-exported source vector) never floods the diff
with phantom re-cuts - a real formation edit flips hard ink to a 255 delta, far above that.
Repo keys absent from staging are pool drops and get deleted, refused wholesale when the
staging holds under half the installed set (a botched extraction must not wipe a set).
A change that only adds white rows or columns (a grown canvas, see canvas.py) installs without an
archive copy, and the cards left in place (R) are then padded to their set's canvas.

The drivers stage per chapter (/tmp/fsx_out/ch9/<d>, /tmp/fsx_out/ch7/<d>) - we install
whichever chapters are present, so a Ch.9-only run never touches the Collegiate sets.

PROTECT exempts 4-way R/Bundy from the orphan sweep: it is CISM-only, absent from the SCM, so
never staged - without the exemption its preserved legacy pair would be dropped as an orphan.
Cards that DO appear in the source (8-way D/Hope Diamond's foot graft over the PDF's flat-sliced
feet, say) re-propose on each re-cut like any other - reject them in the review PR to keep the
committed hand-mend."""
import glob, os, shutil, sys
import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
sys.path.insert(0, f"{ROOT}/tools")
import legacy_archive as la
import canvas
SRC = f"{ROOT}/assets/sources/uspa"
DEP_ROOT = f"{SRC}/legacy/deprecated"    # superseded art parked as <disc>/<key>_dep-<year> on a re-cut
OUT = "/tmp/fsx_out"
MIN_STAGED_RATIO = 0.5   # refuse orphan deletes when staging covers under half the set (botched run guard)
RECUT_TOLERANCE = 200    # max channel delta of a re-render/re-encode diff - real ink edits flip to 255
PROTECT = {              # (discipline, repo-relative path) exempt from the orphan sweep - R is CISM-only, never in the SCM staging
    ("4-way", "R.webp"), ("4-way", "figures/R.webp"),
}

pixels = lambda f: np.asarray(Image.open(f).convert("RGB"))
# Pixels minus every pure-white row and column, so a canvas pad compares equal to its source
unpadded = lambda a: a[~(a == 255).all(axis=(1, 2))][:, ~(a == 255).all(axis=(0, 2))]
# Pool order: randoms A-Z first, then blocks numerically (10 after 2)
pool_order = lambda k: (k[0].isdigit(), int("".join(filter(str.isdigit, k)) or "0"), k)
# Card/figure rel paths -> pool keys, deduped (a card and its derived figure share one key)
to_keys = lambda rels: sorted(dict.fromkeys(os.path.splitext(os.path.basename(r))[0] for r in rels), key=pool_order)

# Discipline -> its staging dir, across whichever chapters ran
staged_dirs = {}
for chap in ("ch9", "ch7"):
    base = f"{OUT}/{chap}"
    if os.path.isdir(base):
        for d in os.listdir(base):
            staged_dirs[d] = f"{base}/{d}"

total = 0
all_installed, all_padded, all_fitted, all_deleted, all_tolerated, all_refused, all_archived = [], [], [], [], [], [], []
for d in sorted(staged_dirs):
    od = staged_dirs[d]
    repo_dir = f"{ROOT}/assets/diagrams/{d}/USPA"
    staged = sorted(glob.glob(f"{od}/*.webp") + glob.glob(f"{od}/figures/*.webp"))
    protect = {rel for disc, rel in PROTECT if disc == d}
    staged_rels = {os.path.relpath(s, od) for s in staged}
    repo_rels = {os.path.relpath(f, repo_dir)
                 for f in glob.glob(f"{repo_dir}/*.webp") + glob.glob(f"{repo_dir}/figures/*.webp")}
    installed, padded, tolerated, archived, identical = [], [], [], [], 0
    for src in staged:
        rel = os.path.relpath(src, od)
        dst = os.path.join(repo_dir, rel)
        exists = os.path.exists(dst)
        if exists:
            sp, dp = pixels(src), pixels(dst)
            if np.array_equal(sp, dp):
                identical += 1
                continue
            # Re-rendered/re-encoded unchanged card (anti-alias drift, no ink flip): keep repo render
            if sp.shape == dp.shape:
                md = int(np.abs(sp.astype(int) - dp.astype(int)).max())
                if md < RECUT_TOLERANCE:
                    tolerated.append((rel, md))
                    continue
            if np.array_equal(unpadded(sp), unpadded(dp)):
                shutil.copyfile(src, dst)
                padded.append(rel)
                continue
        if exists and not rel.startswith("figures/"):  # real change: archive the outgoing diagram (figures are derived)
            archived.append(la.archive_image(DEP_ROOT, d, rel, dst))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        installed.append(rel)
    # Orphans = repo files with no staged counterpart, minus the exempt R pair (never auto-dropped)
    # refused wholesale under the half-set guard or when a key category staged nothing (botched run)
    deleted = []
    deletable, refused = la.orphan_guard(staged_rels, repo_rels - protect, MIN_STAGED_RATIO)
    for rel in deletable:
        if not rel.startswith("figures/"):    # archive the outgoing diagram only (figures are derived)
            archived.append(la.archive_image(DEP_ROOT, d, rel, os.path.join(repo_dir, rel)))
        os.remove(os.path.join(repo_dir, rel))
        deleted.append(rel)
    fitted = [os.path.relpath(path, repo_dir) for path in
              canvas.fit_files([os.path.join(repo_dir, rel) for rel in sorted(repo_rels - staged_rels - set(deleted))])]
    total += len(installed) + len(padded) + len(fitted) + len(deleted)
    # Per-discipline detail to stderr: shown live in the action log, kept out of install.log (PR body)
    print(f"{d}: {identical} identical, {len(installed)} installed, {len(deleted)} deleted"
          + (f", {len(padded)} padded" if padded else "")
          + (f", {len(fitted)} fitted" if fitted else "")
          + (f", {len(tolerated)} re-render" if tolerated else "")
          + (f", {len(archived)} archived" if archived else ""), file=sys.stderr)
    for rel in installed:
        print(f"    installed {rel}", file=sys.stderr)
    for rel in padded:
        print(f"    padded {rel} (white rows/columns only, not archived)", file=sys.stderr)
    for rel in fitted:
        print(f"    fitted {rel} to the set's canvas", file=sys.stderr)
    for rel in deleted:
        print(f"    deleted {rel} (key left the pool)", file=sys.stderr)
    for rel, md in tolerated:
        print(f"    re-render {rel} (maxd {md} < {RECUT_TOLERANCE}, kept repo render)", file=sys.stderr)
    for rel in archived:
        print(f"    archived {rel}", file=sys.stderr)
    if refused:
        print(f"    !! refusing {len(refused)} deletion(s), staging holds under half the installed set", file=sys.stderr)
    all_installed += to_keys(installed)
    all_padded    += [k for k in to_keys(padded) if k not in to_keys(installed)]
    all_fitted    += to_keys(fitted)
    all_deleted   += to_keys(deleted)
    all_archived  += archived
    all_tolerated += to_keys(r for r, _ in tolerated)
    all_refused   += to_keys(refused)

# Grouped summary to stdout - the only thing tee'd into install.log, so the PR body shows just this
print(f"Total: {total} file(s) changed (including figures)")
if all_installed:
    print(f"- New/updated ({len(all_installed)}): {', '.join(all_installed)}")
if all_padded:
    print(f"- Padded ({len(all_padded)}): {', '.join(all_padded)} (white padding only, art unchanged)")
if all_fitted:
    print(f"- Fitted ({len(all_fitted)}): {', '.join(all_fitted)} (kept card padded to the grown canvas)")
if all_deleted:
    print(f"- Deleted ({len(all_deleted)}): {', '.join(all_deleted)} (key left the pool)")
if all_tolerated:
    print(f"- Kept ({len(all_tolerated)}): {', '.join(all_tolerated)} (change was not noticed)")
if all_archived:
    print(f"- Archived ({len(all_archived)}) to legacy/deprecated/: {', '.join(os.path.basename(a) for a in all_archived)}")
if all_refused:
    print(f"- [ERROR] Refusing {len(all_refused)} deletions, staging holds under half the set, review manually: {', '.join(all_refused)}")
