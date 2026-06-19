#!/usr/bin/env python3
"""Extract the USPA 6-Way Speed formation cells from SCM Ch.7 (page located via find_pages).
The cells form a left-justified grid (the pool has run 3 formations in one row up to 5 across
two), found by scanning the WHOLE page for its border lines - never hardcoded page positions or
a fixed cell count. Each cell: number top-left, vector formation diagram, name centred at bottom,
black border. Output mirrors the 10-way-speed USPA style: named = number+diagram+name on white
(border removed); figure = diagram only (number+name erased glyph-precisely via ext_rand's
erase_names from the PDF text layer)."""
import os, sys
import numpy as np
from PIL import Image
import ext_rand, find_pages

ext_rand.PDF = f"{ext_rand.ROOT}/assets/sources/uspa/collegiate.pdf"
ext_rand.CACHE = "/tmp/fsx_ch7"
DPI = 600
OUTDIR = "/tmp/fsx_out/ch7/6-way-speed"
INK = 140
# Locate the 6-Way Speed Formations page from the headers (single page, no random/block split)
_rnd, _other = find_pages.pages_for(ext_rand.PDF, {None, "FS"}, 6)
PAGE = _other[0] if _other else None

def longest_run(b):
    if not b.any():
        return 0
    idx = np.flatnonzero(~b)
    if idx.size == 0:
        return b.size
    bounds = np.diff(np.concatenate(([-1], idx, [b.size]))) - 1
    return int(bounds.max())

def group(hits, gap):
    groups = []
    for h in hits:
        if groups and h - groups[-1][-1] <= gap:
            groups[-1].append(h)
        else:
            groups.append([h])
    return [int(np.mean(g)) for g in groups]

def vlines(ink, y0, y1, min_len, gap=20):
    """x-centres of vertical border lines within the y-band [y0,y1]."""
    sub = ink[y0:y1, :]
    hits = [x for x in range(sub.shape[1]) if longest_run(sub[:, x]) >= min_len]
    return group(hits, gap)

def hlines(ink, x0, x1, min_len, gap=20):
    """y-centres of horizontal border lines within the x-band [x0,x1]."""
    sub = ink[:, x0:x1]
    hits = [y for y in range(sub.shape[0]) if longest_run(sub[y, :]) >= min_len]
    return group(hits, gap)

def save_webp(arr, path):
    Image.fromarray(arr).save(path, "WEBP", lossless=True, method=6)

def vrun_span(col):
    """[start, end) of the longest contiguous run in a boolean column - a border's true vertical
    extent. A horizontal rule (title underline, footer) crossing the column is only ~2px, so it
    never wins, keeping the grid's span clear of those strays."""
    best = (0, 0, 0); s = None
    for i, v in enumerate(col):
        if v:
            if s is None: s = i
        elif s is not None:
            if i - s > best[0]: best = (i - s, s, i)
            s = None
    if s is not None and len(col) - s > best[0]: best = (len(col) - s, s, len(col))
    return best[1], best[2]

def detect(g):
    """Find the formation grid by scanning the WHOLE page for its border lines - no hardcoded
    page-fraction bands (the grid's position shifts between editions). The grid's vertical span
    comes from each detected vertical's longest run, then horizontals are read inside that span
    across column 1 (present in every row), so the title and footer rules drop out."""
    ink = g < INK
    H, W = g.shape
    vx = vlines(ink, 0, H, min_len=int(0.10 * H), gap=40)        # one cell tall - col-1 dividers span more
    if len(vx) < 2:
        return vx, [], ink, (H, W)                              # no grid: caller skips gracefully
    spans = [vrun_span(ink[:, x]) for x in vx]
    gtop = min(s for s, _ in spans); gbot = max(e for _, e in spans)
    hy = [y for y in hlines(ink, vx[0], vx[1], min_len=int(0.6 * (vx[1] - vx[0])), gap=40)
          if gtop - 25 <= y <= gbot + 25]
    return vx, hy, ink, (H, W)

def vpresent(ink, x, y0, y1, frac=0.6):
    """A vertical divider spans row band [y0,y1] near column x - i.e. this cell exists in this
    row. Lets a later row carry fewer cells than the widest (top) row."""
    band = y1 - y0
    W = ink.shape[1]
    return max(longest_run(ink[y0 + 5:y1 - 5, xx]) for xx in range(max(0, x - 12), min(W, x + 12))) >= frac * band

def boxes_from(vx, hy, ink):
    """Number the cells row-major over however many rows/cells are drawn. Each row is
    left-justified, so its cells are the prefix of vx whose dividers actually span that row's
    band - no fixed 4-across/1-below assumption."""
    boxes = []; k = 0
    for r in range(len(hy) - 1):
        y0, y1 = hy[r], hy[r + 1]
        present = [x for x in vx if vpresent(ink, x, y0, y1)]
        for c in range(len(present) - 1):
            k += 1
            boxes.append((k, present[c], present[c + 1], y0, y1))
    return boxes

def band_inner(g, coord, p0, p1, axis, step, thr=245, frac=0.80):
    """Inner edge of a border line (grayscale twin of ext_rand.band_inner): walk inward from
    the detected line centre past every band row/col, so the crop excludes ONLY border pixels
    (line + anti-alias halo) and keeps every interior white pixel — a fixed inset over-cropped
    because border thickness varies."""
    line = lambda i: g[i, p0:p1] if axis == 0 else g[p0:p1, i]
    is_band = lambda i: (line(i) < thr).mean() > frac
    i = coord
    if not is_band(i):
        near = next((coord + d * s for d in range(1, 31) for s in (step, -step) if is_band(coord + d * s)), None)
        if near is None: return coord
        i = near
    while is_band(i + step): i += step
    return i + step

def interior_bounds(g, x0, x1, y0, y1):
    cx0 = band_inner(g, x0, y0 + 25, y1 - 25, 1, +1)
    cx1 = band_inner(g, x1, y0 + 25, y1 - 25, 1, -1) + 1
    cy0 = band_inner(g, y0, x0 + 25, x1 - 25, 0, +1)
    cy1 = band_inner(g, y1, x0 + 25, x1 - 25, 0, -1) + 1
    return cx0, cy0, cx1, cy1

if __name__ == "__main__":
    if PAGE is None:
        print("6-way-speed: page not found, skipping"); sys.exit(0)
    g = np.array(Image.fromarray(ext_rand.render(PAGE, DPI)).convert("L"))
    vx, hy, ink, (H, W) = detect(g)
    if len(vx) < 2 or len(hy) < 2:
        print("6-way-speed: grid not detected, skipping"); sys.exit(0)
    print("H,W =", H, W)
    print("vx (vertical borders):", vx)
    print("hy (horizontal borders):", hy)
    boxes = boxes_from(vx, hy, ink)
    print("boxes:", [(k, x0, x1, y0, y1) for k, x0, x1, y0, y1 in boxes])

    do_extract = "--extract" in sys.argv
    if not do_extract:
        rgb = ext_rand.render(PAGE, DPI).copy()
        for k, x0, x1, y0, y1 in boxes:
            rgb[y0:y0+8, x0:x1] = [255, 0, 0]; rgb[y1-8:y1, x0:x1] = [255, 0, 0]
            rgb[y0:y1, x0:x0+8] = [255, 0, 0]; rgb[y0:y1, x1-8:x1] = [255, 0, 0]
        ov = Image.fromarray(rgb); ov.thumbnail((1000, 1300))
        ov.save("/tmp/fsx_6way_ov.png")
        print("wrote /tmp/fsx_6way_ov.png")
    else:
        os.makedirs(f"{OUTDIR}/figures", exist_ok=True)
        ws = ext_rand.words(PAGE, DPI)
        rgb = np.repeat(g[..., None], 3, 2)   # ext_rand erasure expects RGB; channels identical
        for k, x0, x1, y0, y1 in boxes:
            cx0, cy0, cx1, cy1 = interior_bounds(g, x0, x1, y0, y1)
            named = g[cy0:cy1, cx0:cx1].copy()
            save_webp(named, f"{OUTDIR}/{k}.webp")
            fig = ext_rand.erase_names(rgb, ws, cx0, cy0, cx1, cy1, [(cy0, cy1)])[..., 0]
            save_webp(fig, f"{OUTDIR}/figures/{k}.webp")
            print(f"key {k}: {named.shape[1]}x{named.shape[0]}")
        print("extracted", len(boxes), "->", OUTDIR)
