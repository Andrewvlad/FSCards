#!/usr/bin/env python3
"""Reposition the 'R' key on the preserved 4-way R/Bundy card to the sibling
randoms' key geometry. R is CISM-only and never extracted (see the README), and
its prior-pair key sat up-left of every SCM-cut sibling (top y33/x-center 48.5
vs the siblings' y53-55/x-center ~73.5 at the same ~66-70px cap height). Pure
translation of the existing glyph -- the weight and cap already match -- so the
art stays byte-untouched. Self-noops when the key is already in place; the
figure variant carries no key. Operates on the installed file in place."""
import numpy as np
from PIL import Image
from scipy import ndimage

PATH = "../../assets/diagrams/4-way/USPA/R.webp"
TY, TCX = 53, 73.5   # target glyph top / x-centre, the sibling randoms' cluster
PAD = 4              # margin around the glyph bbox taking its AA fringe along

arr = np.array(Image.open(PATH).convert("RGB"))
zone = arr.mean(2)[:200, :200] < 130
ys, xs = np.where(zone)
y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
dy, dx = TY - y0, round(TCX - (x0 + x1) / 2)
if abs(dy) <= 1 and abs(dx) <= 1:
    print(f"key already at y{y0} x-centre {(x0 + x1) / 2}; nothing to do")
    raise SystemExit
src = (slice(y0 - PAD, y1 + PAD), slice(x0 - PAD, x1 + PAD))
dst = (slice(y0 - PAD + dy, y1 + PAD + dy), slice(x0 - PAD + dx, x1 + PAD + dx))
glyph = arr[src].copy()
arr[src] = 255
# the shift is smaller than the glyph, so src is erased before the check
assert (arr[dst].mean(2) > 245).all(), "destination not empty white; re-measure"
arr[dst] = glyph
Image.fromarray(arr).save(PATH, "WEBP", lossless=True, quality=100, method=6)
print(f"key moved by dy {dy} dx {dx} -> top y{y0 + dy}, x-centre {(x0 + x1) / 2 + dx}")
