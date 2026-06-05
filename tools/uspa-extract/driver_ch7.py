#!/usr/bin/env python3
"""Extract the collegiate 2-way + VFS 2-way USPA sets from the vector SCM Ch.7
"Collegiate" PDF (committed at assets/sources/uspa/scm_ch07.pdf; originally
uspa.org/scm) into a staging dir — native crop size, lossless, glyph-precise figures.
Printed appendix labels are PDF page minus 2: 2-way blocks pp14-15 / randoms p16,
6-way Speed p17, VFS-2 blocks p18 / randoms p19. The 2-way randoms come from
p16fix.py (the 1x4 table is too short for detect_grid) and 6-way from extract6.py."""
import os, glob
from PIL import Image
import ext_rand, ext_block

ext_rand.PDF=f"{ext_rand.ROOT}/assets/sources/uspa/scm_ch07.pdf"
ext_rand.CACHE="/tmp/fsx_ch7"
DPI=600; OUT="/tmp/fsx_out/ch7"
REPO=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../../assets/diagrams"))
JOBS={"2-way": (16, [14, 15]), "2-way-vfs": (19, [18])}

def save(arr, path):
    Image.fromarray(arr).save(path, "WEBP", lossless=True, quality=100, method=6)

if __name__=="__main__":
    for d, (rpg, bpgs) in JOBS.items():
        cells = {}
        cells.update(ext_rand.extract(rpg, DPI))
        for bp in bpgs:
            cells.update(ext_block.extract(bp, DPI))
        od = f"{OUT}/{d}"; os.makedirs(f"{od}/figures", exist_ok=True)
        for k, (named, fig) in cells.items():
            save(named, f"{od}/{k}.webp"); save(fig, f"{od}/figures/{k}.webp")
        want = set(os.path.basename(f)[:-5] for f in glob.glob(f"{REPO}/{d}/USPA/*.webp"))
        got = set(cells.keys())
        print(f"{d:10s} got {len(got):2d} want {len(want):2d} missing={sorted(want-got)} extra={sorted(got-want)}")
