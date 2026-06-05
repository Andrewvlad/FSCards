"""Derive 4-way R/Bundy — absent from the FAI pool (CISM-only), so every set's R
is hand-derived: FAI block 12's first cell IS the Bundy formation."""
import extract as faiext
from PIL import Image
arr, cols, boxes, ins = faiext.extract_blocks(18)   # page 18 = blocks 9-16; row0 col3 = block 12
(top, d1, d2, bot) = boxes[0]; (c0, c1) = cols[3]
# cell1 (top formation = Bundy), exclude the divider below it
cell = arr[top + ins:d1 - ins, c0 + ins:c1 - ins].copy()
named = cell.copy(); faiext.erase_key(named, 6)                 # remove the '12' number, keep 'Bundy'
fig = cell.copy();   faiext.erase_key(fig, 6); faiext.erase_name(fig, 6)
faiext.save(named, "/tmp/faiext/out/4-way/R.webp")
faiext.save(fig,   "/tmp/faiext/out/4-way/figures/R.webp")
print("R named", Image.open("/tmp/faiext/out/4-way/R.webp").size,
      " fig", Image.open("/tmp/faiext/out/4-way/figures/R.webp").size)
