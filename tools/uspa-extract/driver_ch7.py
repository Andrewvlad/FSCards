#!/usr/bin/env python3
"""Extract the collegiate 2-way + VFS 2-way USPA sets from the vector SCM Ch.7
"Collegiate" PDF (committed at assets/sources/uspa/collegiate.pdf - originally
uspa.org/scm) into a staging dir — native crop size, lossless, glyph-precise figures.
Pages are located per edition from the appendix headers (find_pages), never hardcoded.
This driver cuts 2-way blocks and both halves of VFS-2 - the 2-way randoms come from
p16fix.py (the 1x4 table is too short for detect_grid) and 6-way-speed from extract6.py."""
import os, glob
from PIL import Image
import ext_rand, ext_block, find_pages

ext_rand.PDF=f"{ext_rand.ROOT}/assets/sources/uspa/collegiate.pdf"
ext_rand.CACHE="/tmp/fsx_ch7"
DPI=600; OUT="/tmp/fsx_out/ch7"
REPO=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../../assets/diagrams"))
# discipline : (header style tokens, way-count, non-random layout, cut randoms here?). VFS-2
# randoms are a normal grid (cut here) - FS 2-way randoms are the 1x4 table left to p16fix.
JOBS={
 "2-way":     ({None,"FS"}, 2, "block", False),
 "2-way-vfs": ({"VFS"},     2, "block", True),
}

def save(arr, path):
    Image.fromarray(arr).save(path, "WEBP", lossless=True, quality=100, method=6)

if __name__=="__main__":
    for d, (styles, width, other, do_rand) in JOBS.items():
        rpgs, opgs = find_pages.pages_for(ext_rand.PDF, styles, width)
        cells = {}
        if do_rand:
            for rp in rpgs:
                cells.update(ext_rand.extract(rp, DPI))
        for op in opgs:
            cells.update((ext_block if other == "block" else ext_rand).extract(op, DPI))
        od = f"{OUT}/{d}"; os.makedirs(f"{od}/figures", exist_ok=True)
        for k, (named, fig) in cells.items():
            save(named, f"{od}/{k}.webp"); save(fig, f"{od}/figures/{k}.webp")
        want = set(os.path.basename(f)[:-5] for f in glob.glob(f"{REPO}/{d}/USPA/*.webp"))
        got = set(cells.keys())
        print(f"{d:10s} rnd={rpgs if do_rand else '(p16fix)'} {other}={opgs}  got {len(got):2d} want {len(want):2d} missing={sorted(want-got)} extra={sorted(got-want)}")
