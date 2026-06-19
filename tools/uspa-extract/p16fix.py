#!/usr/bin/env python3
"""2-way randoms (SCM Ch.7): single 1x4 bordered row - too short for ext_rand's
page-relative grid thresholds. Find the table band from its full-width horizontal rules,
verticals within the band, then reuse ext_rand's key/crop/erase verbatim."""
import os, sys
import numpy as np
from PIL import Image
import ext_rand, find_pages
from ext_rand import render, words, find_key, erase_names, max_run, clusters, INK

ext_rand.PDF = f"{ext_rand.ROOT}/assets/sources/uspa/collegiate.pdf"
ext_rand.CACHE = "/tmp/fsx_ch7"
DPI = 600
OUT = "/tmp/fsx_out/ch7/2-way"
# Locate the FS 2-way randoms page from the headers. The 2026 edition prints no appendix
# subtitle on it, so fall back to the page right after the 2-way block run.
_rnd, _blk = find_pages.pages_for(ext_rand.PDF, {None, "FS"}, 2)
PAGE = _rnd[0] if _rnd else (max(_blk) + 1 if _blk else None)
if PAGE is None:
    print("2-way randoms: no page found, skipping"); sys.exit(0)

arr = render(PAGE, DPI); ws = words(PAGE, DPI)
H, W, _ = arr.shape
dark = arr[..., :3].mean(2) < INK

# table band: horizontal rules spanning >60% page width, nearest above keys / below names
rowrun = np.array([max_run(dark[r, :]) for r in range(H)])
hl = [int(np.mean(c)) for c in clusters(list(np.where(rowrun > 0.6 * W)[0]), int(0.012 * H))]
keys = [w for w in ws if w[4].strip() in {"A", "B", "C", "D"}]
if not keys:
    print("2-way randoms: no A-D keys on the located page, skipping"); sys.exit(0)
ky0 = min(k[1] for k in keys)
names = [w for w in ws if w[4].strip() not in {"A", "B", "C", "D"} and ky0 < w[1] < ky0 + 0.25 * H]
ny1 = max(n[3] for n in names)
top = max(y for y in hl if y < ky0); bot = min(y for y in hl if y > ny1)

# vertical edges: runs ~ full band height inside [top, bot]
band = dark[top:bot, :]
colrun = np.array([max_run(band[:, c]) for c in range(W)])
xs = [int(np.mean(c)) for c in clusters(list(np.where(colrun > 0.85 * (bot - top))[0]), int(0.012 * W))]
print("band", top, bot, "xs", xs)
assert len(xs) == 5, "expected 4 cells"

out = {}
for c in range(4):
    X0, X1, Y0, Y1 = xs[c], xs[c + 1], top, bot
    inside = [w for w in ws if w[0] >= X0 - 2 and w[2] <= X1 + 2 and w[1] >= Y0 - 2 and w[3] <= Y1 + 2]
    key = find_key(inside, X0, Y0, W)
    cx0, cy0, cx1, cy1 = ext_rand.cell_inner(arr, X0, Y0, X1, Y1)
    out[key] = (arr[cy0:cy1, cx0:cx1].copy(), erase_names(arr, ws, cx0, cy0, cx1, cy1, [(cy0, cy1)]))
    print(key, out[key][0].shape)

os.makedirs(f"{OUT}/figures", exist_ok=True)
for k, (named, fig) in out.items():
    Image.fromarray(named).save(f"{OUT}/{k}.webp", "WEBP", lossless=True, quality=100, method=6)
    Image.fromarray(fig).save(f"{OUT}/figures/{k}.webp", "WEBP", lossless=True, quality=100, method=6)
print("saved", sorted(out))
