#!/usr/bin/env python3
"""Redo the CF outline (USPA) sets BORDER-ONLY: take each native PDF cell and remove
ONLY the border line (no margin into the card, no resample, no crisp-up). Output is at
native resolution. Figures additionally erase the baked labels (letter/number/names)
BEFORE the border strip. Sets: 4-way-cf (randoms A-N from fai18-*, blocks 1-14 from
fblk*) and 2-way-cf (randoms A-F from cf2-*); the page extracts regenerate into SRC
from the committed CR PDFs under assets/sources/cf/ when absent."""
import os, subprocess
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
SRC = "/tmp/cf4"
OUT = "/tmp/cf4/cfborder_ll"
# pdfimages page extracts: FAI CF CR 2025 pp16-18 (CF4 blocks + randoms), APF CF CR
# 01-2025 p17 (CF2 Annex C — the highest-res raster of the outline art)
PDFS = [(f"{ROOT}/assets/sources/cf/fai_cf_2025.pdf", 16, "fblk"),
        (f"{ROOT}/assets/sources/cf/fai_cf_2025.pdf", 17, "fblk17"),
        (f"{ROOT}/assets/sources/cf/fai_cf_2025.pdf", 18, "fai18"),
        (f"{ROOT}/assets/sources/cf/apf_cf_2025.pdf", 17, "cf2")]
ROWS = [("fai18-000.png", "ABCD"), ("fai18-002.png", "EFGH"),
        ("fai18-003.png", "IJKL"), ("fai18-005.png", "MN")]
GRIDS = [("fblk-000.png", [1, 2, 3, 4]), ("fblk-002.png", [5, 6, 7]),
         ("fblk-004.png", [8]), ("fblk17-001.png", [9, 10]),
         ("fblk17-002.png", [11]), ("fblk17-003.png", [12]),
         ("fblk17-000.png", [13, 14])]
CF2 = [("cf2-000.png", "B"), ("cf2-001.png", "C"), ("cf2-002.png", "E"),
       ("cf2-003.png", "F"), ("cf2-004.png", "A"), ("cf2-005.png", "D")]
for d in ("4-way-cf", "2-way-cf"):
    os.makedirs(f"{OUT}/{d}/figures", exist_ok=True)
for pdf, page, stem in PDFS:
    if not os.path.exists(f"{SRC}/{stem}-000.png"):
        subprocess.run(["pdfimages", "-png", "-f", str(page), "-l", str(page), pdf, f"{SRC}/{stem}"], check=True)


# ---- border strip (removes only the border line; keeps all card-interior white) ----
def strip_box(gray, edge_limit=10, max_band=30):  # block 5's left border hides behind a 7px outer margin
    H, W = gray.shape; ink = gray < 128
    rc = ink.mean(1); cc = ink.mean(0)

    def find(vec, n):
        s = 0
        while s < n and not vec[s] > 0.6:      # skip thin outer margin (white)
            if s >= edge_limit:
                return 0                        # no border near this edge -> keep it
            s += 1
        if s >= n:
            return 0
        e = s
        while e < n and vec[e] > 0.3:           # advance through the border band
            e += 1
        if e - s > max_band:
            return 0                            # too thick to be a frame line
        return e                                # drop [0, e): outer margin + border line
    t = find(rc, H); l = find(cc, W)
    b = find(rc[::-1], H); r = find(cc[::-1], W)
    return (l, t, W - r, H - b)


# ---- native cell extraction ----
def spans(mask, minlen):
    o = []; i = 0; n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]: j += 1
            if j - i >= minlen: o.append((i, j))
            i = j
        else:
            i += 1
    return o


def rand_cells(path, minw=60):
    a = np.array(Image.open(path).convert("L")); ink = a < 128
    out = []
    for x0, x1 in spans(ink.any(0), minw):
        ys = spans(ink[:, x0:x1].any(1), minw)
        out.append((a[min(s[0] for s in ys):max(s[1] for s in ys), x0:x1]))
    return out


def block_cols(path):
    a = np.array(Image.open(path).convert("L")); ink = a < 128
    out = []
    for x0, x1 in spans(ink.any(0), 120):
        col = a[:, x0:x1]; ys = spans((col < 128).any(1), 120)
        out.append(col[min(s[0] for s in ys):max(s[1] for s in ys)])
    return out


# ---- label erasure (figures only); frame kept (stripped afterwards) ----
def erase_rand(gray):                                   # CF4 random: letter + bottom name
    H, W = gray.shape; ink = gray < 128
    lbl, n = ndimage.label(ink, structure=np.ones((3, 3)))
    drop = np.zeros_like(ink)
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        h = (ys.max() - ys.min()) / H; w = (xs.max() - xs.min()) / W
        cy = ys.mean() / H; cx = xs.mean() / W
        if w > 0.85 and h > 0.85: continue
        if cy < 0.30 and cx < 0.34 and h < 0.25 and w < 0.34: drop |= (lbl == i)
        elif cy > 0.72 and h < 0.22 and w < 0.85: drop |= (lbl == i)
    out = gray.copy(); out[ndimage.binary_dilation(drop, iterations=2)] = 255
    return out


def erase_letter(gray):                                 # CF2 random: corner letter only
    H, W = gray.shape; ink = gray < 128
    lbl, n = ndimage.label(ink, structure=np.ones((3, 3)))
    drop = np.zeros_like(ink)
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        h = (ys.max() - ys.min()) / H; w = (xs.max() - xs.min()) / W
        cy = ys.mean() / H; cx = xs.mean() / W
        if w > 0.85 and h > 0.85: continue
        if cy < 0.30 and cx < 0.34 and h < 0.25 and w < 0.34: drop |= (lbl == i)
    out = gray.copy(); out[ndimage.binary_dilation(drop, iterations=2)] = 255
    return out


def hlines(ink):
    W = ink.shape[1]; cov = ink.sum(1)
    rows = [y for y in range(len(cov)) if cov[y] > 0.55 * W]
    out = []; i = 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and rows[j + 1] - rows[j] <= 3: j += 1
        out.append((rows[i] + rows[j]) // 2); i = j + 1
    return out


def erase_block(gray):                                  # CF4 block: number + 3 panel names
    H, W = gray.shape; ink = gray < 128
    lines = hlines(ink)
    if len(lines) >= 4: top, d1, d2, bot = lines[0], lines[1], lines[2], lines[-1]
    else: top, bot, d1, d2 = 0, H, H // 3, 2 * H // 3
    panels = [(top, d1), (d1, d2), (d2, bot)]
    allowed = np.zeros_like(ink)
    allowed[top:top + int(0.14 * H), 0:int(0.36 * W)] = True
    for (pt, pb) in panels:
        allowed[int(pb - 0.32 * (pb - pt)):pb, :] = True
    lbl, n = ndimage.label(ink, structure=np.ones((3, 3)))
    seed = np.zeros_like(ink)
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        h = (ys.max() - ys.min()) / H; w = (xs.max() - xs.min()) / W
        cy = int(ys.mean()); cx = int(xs.mean())
        if w > 0.85 and h > 0.55: continue
        if h < 0.09 and w < 0.72 and allowed[cy, cx]: seed |= (lbl == i)
    soft = (gray < 236) & allowed
    grow = ndimage.binary_propagation(seed & allowed, mask=soft)
    drop = ndimage.binary_dilation(grow, iterations=1) & allowed
    out = gray.copy(); out[drop] = 255
    near = ndimage.binary_dilation(out < 110, iterations=3)
    out[allowed & (out > 140) & (out < 255) & ~near] = 255
    return out


def save(cell, fig, path):
    box = strip_box(cell)                               # same box for named + figure
    Image.fromarray(cell).convert("RGB").crop(box).save(f"{OUT}/{path}", lossless=True, quality=100, method=6)
    d, f = path.split("/")
    Image.fromarray(fig).convert("RGB").crop(box).save(f"{OUT}/{d}/figures/{f}", lossless=True, quality=100, method=6)
    return box


os.chdir(SRC)
for path, keys in ROWS:
    for cell, k in zip(rand_cells(path), keys):
        box = save(cell, erase_rand(cell), f"4-way-cf/{k}.webp")
        print(f"CF4 {k}: {cell.shape[1]}x{cell.shape[0]} -> {box[2]-box[0]}x{box[3]-box[1]}")
for path, nums in GRIDS:
    for col, num in zip(block_cols(path), nums):
        box = save(col, erase_block(col), f"4-way-cf/{num}.webp")
        print(f"CF4 blk{num}: {col.shape[1]}x{col.shape[0]} -> {box[2]-box[0]}x{box[3]-box[1]}")
for path, k in CF2:
    cell = np.array(Image.open(path).convert("L"))
    box = save(cell, erase_letter(cell), f"2-way-cf/{k}.webp")
    print(f"CF2 {k}: {cell.shape[1]}x{cell.shape[0]} -> {box[2]-box[0]}x{box[3]-box[1]}")
print("done")
