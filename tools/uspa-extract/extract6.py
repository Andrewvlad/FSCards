#!/usr/bin/env python3
"""Extract the 5 USPA 6-Way Speed formation cells from SCM Ch.7 Appendix D (p17).
Layout: row1 = cells 1-4 across, row2 = cell 5 (col 1). Each cell: number top-left, vector
formation diagram, name centred at bottom, black border. Output mirrors the 10-way USPA style:
named = number+diagram+name on white (border removed); figure = diagram only (number+name
erased glyph-precisely via ext_rand's erase_names from the PDF text layer)."""
import os, sys
import numpy as np
from PIL import Image
import ext_rand

ext_rand.PDF = f"{ext_rand.ROOT}/assets/sources/uspa/scm_ch07.pdf"
ext_rand.CACHE = "/tmp/fsx_ch7"
PAGE, DPI = 17, 600
OUTDIR = "/tmp/fsx_out/ch7/6-way"
INK = 140

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

def detect(g):
    ink = g < INK
    H, W = g.shape
    # cells live in the top region; ignore the footer band entirely
    top = int(0.45 * H)
    # vertical borders across the row1 band
    vy0, vy1 = int(0.12 * H), int(0.40 * H)
    vx = vlines(ink, vy0, vy1, min_len=int(0.10 * H), gap=40)
    # horizontal borders within the left column (covers both rows)
    hx0, hx1 = vx[0], vx[1] if len(vx) > 1 else W
    hy = [y for y in hlines(ink, hx0 + 10, hx1 - 10, min_len=int(0.6 * (hx1 - hx0)), gap=40) if y < top]
    return vx, hy, (H, W)

def boxes_from(vx, hy):
    """Build the 5 cell boxes from detected borders.
    Columns: consecutive vx pairs (cell left/right). Rows: hy = [r1top, r1bot/r2top, r2bot]."""
    cols = [(vx[i], vx[i + 1]) for i in range(len(vx) - 1)]
    boxes = []
    r1t, r1b = hy[0], hy[1]
    for c, (x0, x1) in enumerate(cols[:4]):
        boxes.append((c + 1, x0, x1, r1t, r1b))
    # row 2: cell 5 under column 1
    r2t, r2b = hy[1], hy[2]
    boxes.append((5, cols[0][0], cols[0][1], r2t, r2b))
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
    g = np.array(Image.fromarray(ext_rand.render(PAGE, DPI)).convert("L"))
    vx, hy, (H, W) = detect(g)
    print("H,W =", H, W)
    print("vx (vertical borders):", vx)
    print("hy (horizontal borders):", hy)
    boxes = boxes_from(vx, hy)
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
