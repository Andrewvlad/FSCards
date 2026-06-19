#!/usr/bin/env python3
"""Extract the six USPA FS sets from the vector SCM Ch.9 "Formation Skydiving" PDF
(committed at assets/sources/uspa/fs.pdf - originally uspa.org/scm) into a staging dir.
Lossless band-edge crops resized to 1100px wide; figures erased glyph-precisely.
install.py copies the staged files over assets/diagrams/<d>/USPA/. 4-way R/Bundy is
CISM-only (absent from the SCM) and is never extracted, so install.py leaves its
preserved legacy pair untouched."""
import os, glob
from PIL import Image
import ext_rand, ext_block, find_pages

ext_rand.PDF=f"{ext_rand.ROOT}/assets/sources/uspa/fs.pdf"
ext_rand.CACHE="/tmp/fsx_ch9"
DPI=600; TARGET_W=1100; OUT="/tmp/fsx_out/ch9"
REPO=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../../assets/diagrams"))

# discipline repo-dir : (appendix-header style token, way-count, non-random page layout).
# Pages are LOCATED per edition from the running headers (find_pages), never hardcoded - SCM
# front matter shifts the appendix pages every revision. 'block' = 3-panel sequences cut by
# ext_block - 'single' = one-panel numbered formations (10-way) read like randoms by ext_rand.
JOBS={
 "4-way":        ("FS",  4, "block"),
 "8-way":        ("FS",  8, "block"),
 "10-way-speed": ("FS", 10, "single"),
 "16-way":       ("FS", 16, "block"),
 "4-way-vfs":    ("VFS", 4, "block"),
 "2-way-mfs":    ("MFS", 2, "block"),
}

def save(arr, path):
    im=Image.fromarray(arr)
    w=TARGET_W; h=round(im.height*w/im.width)
    im.resize((w,h),Image.LANCZOS).save(path,"WEBP",lossless=True,quality=100,method=6)

def repo_keys(d):
    return set(os.path.basename(f)[:-5] for f in glob.glob(f"{REPO}/{d}/USPA/*.webp"))

if __name__=="__main__":
    for d,(style,width,other) in JOBS.items():
        rpgs,opgs=find_pages.pages_for(ext_rand.PDF,{style},width)
        cells={}
        for rp in rpgs:
            cells.update(ext_rand.extract(rp,DPI))
        for op in opgs:
            cells.update((ext_block if other=="block" else ext_rand).extract(op,DPI))
        od=f"{OUT}/{d}"; os.makedirs(f"{od}/figures",exist_ok=True)
        for k,(named,fig) in cells.items():
            save(named,f"{od}/{k}.webp"); save(fig,f"{od}/figures/{k}.webp")
        got=set(cells.keys()); want=repo_keys(d)
        missing=sorted(want-got, key=lambda k:(len(k),k)); extra=sorted(got-want,key=lambda k:(len(k),k))
        print(f"{d:11s} rnd={rpgs} {other}={opgs}  extracted {len(got):2d}  repo {len(want):2d}  missing={missing}  extra={extra}")
    print("staged ->",OUT)
