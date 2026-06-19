#!/usr/bin/env python3
"""Build the FAI deprecated-image corpus + cross-edition regression test.

Runs the live extractor over every legacy CR under assets/sources/fai/legacy/<year>/, mapping cells
to the canonical pool order BY POSITION (extract.process(keys=...)) -- the baked-key glyph reader is
within-edition and older letterforms drift, so position is the reliable cross-edition map for the
contiguous outdoor pool, and validate_ordering enforces the same fixed order. Each key's diagram is
compared to the current shipped diagram with a shift / scale / whitespace-tolerant metric (ink-bbox
crop, 128x128 downscale, mean abs diff) - art that has since changed is written to
assets/sources/fai/legacy/deprecated/<disc>/<key>_dep-<year>.webp (diagram only).

The deprecation test compares the name-erased FIGURE (so a baked name-text fix -- e.g. "Open Acordian"
-> "Open Accordion", or a font tweak -- is not mistaken for an art change) with a threshold set above
the erasure-noise floor: the connected-component name erase removes a few different pixels across
editions, lifting the figure distance of UNCHANGED art to ~10-14, while a real redraw/swap moves the
figure >= 20. The CHANGED threshold (16) sits in that wide gap, so unchanged diagrams (4-way O/3/22/F,
8-way E/O -- erasure noise or name-only edits) are not archived. Only the named diagram is archived;
the name-erased figure is a derivation of it, re-creatable, so it is not kept.

Doubles as the regression test the README promises: on the current-art lineage the position extraction
reproduces the shipped set (printed at the end, max distance ~0 for the 2025 edition), so a clean run
proves the geometry survives the older editions. 2020 FS is absent (the only archived copy is
Common-Crawl-truncated, the live URL gone), so FS skips that year.

Indoor 8-way is NOT in this corpus. The indoor pool is an edition-varying, non-contiguous SUBSET (the
2020/2022 Indoor CRs carry 20 blocks, omitting 14 and 20 - 2023 grew it to the full 22), and usis.py
keys cells by grid position -- correct only for the current contiguous pool, it mis-maps the legacy
subset (2022 position-17 lands on the baked-18 cell). It is also moot: the shipped indoor variants were
INTRODUCED, not changed -- 13_indoor tracks outdoor and is stable throughout, 17_indoor and 20_indoor
first diverge from outdoor only in the 2023 edition (verified by shape-matching every edition's indoor
cells to the correctly-keyed outdoor pool). So no superseded indoor art exists to archive. Future
indoor CHANGES are caught by the live extract workflow (usis -> install diff), not here. The legacy
indoor CRs are still kept under ../<year>/indoor.pdf as the source-edition record.

Run: python3 legacy.py            (writes the corpus, prints the regression summary)
     python3 legacy.py --dry      (report only, write nothing)
"""
import os, sys, glob, shutil
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract as fx

ROOT = fx.ROOT
LEGACY = f"{ROOT}/assets/sources/fai/legacy"
DEP = f"{LEGACY}/deprecated"
SHIPPED = f"{ROOT}/assets/diagrams"
RAND = list("ABCDEFGHJKLMNOPQ"); BLOCK = [str(i) for i in range(1, 23)]
CHANGED = 16.0      # figure mean-abs-diff >= this is a real art change - unchanged art (erasure/name
                    # noise) stays <= 14.3, real redraws/swaps >= 19.8 -- the threshold sits in the gap
DRY = "--dry" in sys.argv

# Human descriptions per deprecation (disc, key, dep_year), read off the baked panel names of the
# deprecated-vs-current diagrams (see the tool README) - the summary falls back to a generic label.
CHANGES = {
    ("4-way", "E", "2022"): "Meeker, redrawn",
    ("4-way", "1", "2022"): "Snowflake -> Molar",
    ("4-way", "13", "2022"): "Offset/Spinner -> Mixed Accordion",
    ("4-way", "20", "2025"): "Piver -> Zipper",
    ("8-way", "K", "2023"): "Crossbow -> Double Meekers",
    ("8-way", "14", "2023"): "Accordion/Opposed Stairstep -> Zippered Opals",
    ("8-way", "15", "2023"): "Opal & Zipper -> Zippers/Double Yuans",
    ("8-way", "21", "2023"): "Stereopod -> Free Bear/Eye",
}

px = lambda f: np.asarray(Image.open(f).convert("RGB"))

def norm(arr):
    """Shape signature for tolerant comparison: grayscale, crop to the ink bounding box, downscale
    to 128x128. Tolerant of the cell-size and margin drift between editions - a real art change moves
    a lot of ink and so a lot of cells."""
    g = np.asarray(Image.fromarray(arr).convert("L")) if arr.ndim == 3 else arr
    mask = g < 200
    if not mask.any():
        return np.zeros((128, 128))
    ys, xs = np.where(mask)
    crop = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return np.asarray(Image.fromarray(crop).resize((128, 128), Image.LANCZOS), float)

def dist(a, b):
    return float(np.abs(norm(a) - norm(b)).mean())

def fs_edition(pdf):
    """{disc: {key: (named, fig)}} for 4-way + 8-way of one edition, by grid position."""
    fx.PDF = pdf
    out = {}
    for disc, (rp, bps) in fx.locate(pdf).items():
        staged = f"/tmp/fai-legacy-out/{os.path.basename(os.path.dirname(pdf))}"
        shutil.rmtree(f"{staged}/{disc}", ignore_errors=True)
        fx.process(disc, rp, bps, keys=RAND + BLOCK, outroot=staged)
        cells = {}
        for f in glob.glob(f"{staged}/{disc}/*.webp"):
            k = os.path.basename(f)[:-5]
            cells[k] = (px(f), px(f"{staged}/{disc}/figures/{k}.webp"))
        out[disc] = cells
    return out

def shipped(disc, key):
    """Current shipped (named, fig) for a key, or (None, None) when absent (a dropped key)."""
    n = f"{SHIPPED}/{disc}/FAI/{key}.webp"; f = f"{SHIPPED}/{disc}/FAI/figures/{key}.webp"
    return (px(n) if os.path.exists(n) else None, px(f) if os.path.exists(f) else None)

def deprecations(disc, key, timeline, cur_fig):
    """timeline: [(year, (named, fig))] chronological for one key. Returns deprecated versions as
    [(last_valid_year, dep_year, kind, named, fig)] -- contiguous editions whose name-erased FIGURE
    matches each other but not the current art are one version - dep_year is the edition that changed/
    dropped it. Figure, not named: it ignores baked name-text edits (the figure is art only)."""
    if not timeline:
        return []
    # segment into runs of matching consecutive figures (art only)
    runs = [[timeline[0]]]
    for entry in timeline[1:]:
        if dist(entry[1][1], runs[-1][-1][1][1]) < CHANGED:
            runs[-1].append(entry)
        else:
            runs.append([entry])
    deps = []
    for i, run in enumerate(runs):
        last_year, (named, fig) = run[-1]
        if cur_fig is not None and dist(fig, cur_fig) < CHANGED:
            continue   # this run is the current art (or re-appeared), not deprecated
        # dep_year: the next run's first year, else (no later run) the current edition that lacks it
        dep_year = runs[i + 1][0][0] if i + 1 < len(runs) else "2026"
        kind = "removed" if (cur_fig is None and i == len(runs) - 1) else "changed"
        deps.append((last_year, dep_year, kind, named, fig))
    return deps

def main():
    years = sorted(d for d in os.listdir(LEGACY) if os.path.isdir(f"{LEGACY}/{d}") and d != "deprecated")
    print(f"legacy editions: {years}\n")

    # extract every edition's FS pools (indoor excluded -- see module docstring)
    fs = {}
    for y in years:
        fpdf = f"{LEGACY}/{y}/fs.pdf"
        if os.path.exists(fpdf): fs[y] = fs_edition(fpdf)
    fs_years = sorted(fs)

    records = []
    if not DRY:
        shutil.rmtree(DEP, ignore_errors=True)

    def emit(disc, key, last_valid, dep_year, kind, named):
        rel = f"{disc}/{key}_dep-{dep_year}.webp"
        change = CHANGES.get((disc, key, dep_year),
                             "removed from pool" if kind == "removed" else "art/formation changed")
        records.append({"discipline": disc, "key": key, "file": rel,
                        "last_valid_edition": last_valid, "deprecated_as_of": dep_year,
                        "kind": kind, "change": change})
        if DRY:
            return
        os.makedirs(f"{DEP}/{disc}", exist_ok=True)
        fx.save(named, f"{DEP}/{rel}")

    # ---- FS 4-way + 8-way (outdoor) ----
    for disc in ("4-way", "8-way"):
        for key in RAND + BLOCK:
            _, cur_fig = shipped(disc, key)
            timeline = [(y, fs[y][disc][key]) for y in fs_years if key in fs[y].get(disc, {})]
            for last_valid, dep_year, kind, named, _fig in deprecations(disc, key, timeline, cur_fig):
                emit(disc, key, last_valid, dep_year, kind, named)

    # ---- regression: current-lineage editions reproduce shipped (the test the README promises) ----
    print("=== cross-edition regression (per key: name-erased figure distance to current shipped) ===")
    for disc in ("4-way", "8-way"):
        cur_fig = {k: shipped(disc, k)[1] for k in RAND + BLOCK}   # decoded once per key, year-independent
        for y in fs_years:
            ds = [dist(fs[y][disc][k][1], cur_fig[k])
                  for k in RAND + BLOCK if k in fs[y].get(disc, {}) and cur_fig[k] is not None]
            changed = sum(1 for d in ds if d >= CHANGED)
            print(f"  {disc} {y}: {len(ds)} keys, {changed} differ from current (max {max(ds) if ds else 0:.1f})")

    print(f"\n{'(dry) ' if DRY else ''}deprecated versions: {len(records)}")
    for m in records:
        print(f"  {m['discipline']}/{m['key']}: last {m['last_valid_edition']} -> dep {m['deprecated_as_of']} ({m['change']})")

if __name__ == "__main__":
    main()
