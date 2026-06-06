"""Derive 4-way R/Bundy — absent from the FAI pool (CISM-only), so every set's R
is hand-derived: FAI block 12's first panel IS the Bundy formation, with the '12'
key swapped for a drawn 'R' matching the randoms' key convention (the PDF's text
face is ArialMT; Liberation Sans is the metric-compatible local stand-in, as in
the Axis derivation) and the end panel's unmarked torso grafted over jumper 2's
back-X (randoms carry no marking)."""
import numpy as np
import extract as fx
from PIL import Image, ImageFont, ImageDraw
arr, cols, boxes = fx.extract_blocks(18)   # page 18 = blocks 9-16; row0 col3 = block 12
(top, d1, d2, bot) = boxes[0]; (left, right) = cols[3]
# panel 1 (top formation = Bundy), its divider excluded by the span cut
cell, _ = fx.cut(arr, top, d1, left, right)

# R is a random: jumper 2's back is X-marked in the entry panel (blocks mark a
# reference jumper to track across panels; randoms carry none — USPA's R
# equally sheds its back-dot), and the marked torso is a different drawing, not
# an overlay (narrower outline), so erasing the X strokes leaves a wrong-shaped
# back. Block 12 ends in a second Bundy: graft the end panel's clean torso
# window 1-1 — the two stamps register within a pixel (dy −1, measured on the
# 2026 CR raster like the key box below). The seam check trips on a revision.
cell3, _ = fx.cut(arr, d2, bot, left, right)
ref = cell.copy()
y0, y1, x0, x1 = 100, 148, 136, 192
cell[y0:y1, x0:x1] = cell3[y0 - 1:y1 - 1, x0:x1]
seam = np.abs(cell.mean(2) - ref.mean(2)) > 60
seam[y0 + 2:y1 - 2, x0 + 2:x1 - 2] = False
assert seam.sum() < 60, "panel stamps shifted; re-measure the graft window"
fx.despeckle(cell)
named = cell.copy(); fx.erase_key(named)                    # remove the '12' key, keep 'Bundy'
fig = cell.copy();   fx.erase_key(fig); fx.erase_caption(fig)

# key position + cap height measured from a sibling random's card (same 220ppi page
# scale), so the drawn R sits and sizes exactly like the lettered keys around it
ref = np.array(Image.open("/tmp/faiext/out/4-way/B.webp").convert("RGB"))
H, W = ref.shape[:2]
ys, xs = np.where(ref[0:int(.22 * H), 0:int(.28 * W)].mean(2) < 200)
x0, y0, cap = xs.min(), ys.min(), ys.max() - ys.min() + 1
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
size = next(s for s in range(cap, 3 * cap) if ImageFont.truetype(FONT, s).getbbox("R")[3]
            - ImageFont.truetype(FONT, s).getbbox("R")[1] >= cap)
font = ImageFont.truetype(FONT, size)
bb = font.getbbox("R")
im = Image.fromarray(named)
ImageDraw.Draw(im).text((x0 - bb[0], y0 - bb[1]), "R", font=font, fill=(0, 0, 0))
named = np.array(im)

fx.save(named, "/tmp/faiext/out/4-way/R.webp")
fx.save(fig,   "/tmp/faiext/out/4-way/figures/R.webp")
print("R named", Image.open("/tmp/faiext/out/4-way/R.webp").size,
      " fig", Image.open("/tmp/faiext/out/4-way/figures/R.webp").size)
