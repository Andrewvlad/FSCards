#!/usr/bin/env python3
"""Extract the six USPA FS sets from the vector SCM Ch.9 "Formation Skydiving" PDF
(committed at assets/sources/uspa/scm_fs.pdf; originally uspa.org/scm) into a staging dir.
Lossless band-edge crops resized to 1100px wide; figures erased glyph-precisely.
Install = copy the staged files over assets/diagrams/<d>/USPA/. 4-way R/Bundy is
CISM-only (absent from the SCM) and is never extracted, so a plain copy never
clobbers its preserved legacy pair."""
import os, glob
from PIL import Image
import ext_rand, ext_block

ext_rand.PDF=f"{ext_rand.ROOT}/assets/sources/uspa/scm_fs.pdf"
ext_rand.CACHE="/tmp/fsx_ch9"
DPI=600; TARGET_W=1100; OUT="/tmp/fsx_out/ch9"
REPO=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../../assets/diagrams"))

# discipline repo-dir : (randoms_page, [block_pages])
JOBS={
 "4-way":        (17,[14,15,16]),
 "8-way":        (21,[18,19,20]),
 "10-way-speed": (22,[]),
 "16-way":       (25,[23,24]),
 "4-way-vfs":    (29,[26,27,28]),
 "2-way-mfs":    (34,[31,32,33]),
}

def save(arr, path):
    im=Image.fromarray(arr)
    w=TARGET_W; h=round(im.height*w/im.width)
    im.resize((w,h),Image.LANCZOS).save(path,"WEBP",lossless=True,quality=100,method=6)

def repo_keys(d):
    return set(os.path.basename(f)[:-5] for f in glob.glob(f"{REPO}/{d}/USPA/*.webp"))

if __name__=="__main__":
    for d,(rpg,bpgs) in JOBS.items():
        cells={}
        cells.update(ext_rand.extract(rpg,DPI))
        for bp in bpgs:
            cells.update(ext_block.extract(bp,DPI))
        od=f"{OUT}/{d}"; os.makedirs(f"{od}/figures",exist_ok=True)
        for k,(named,fig) in cells.items():
            save(named,f"{od}/{k}.webp"); save(fig,f"{od}/figures/{k}.webp")
        got=set(cells.keys()); want=repo_keys(d)
        missing=sorted(want-got, key=lambda k:(len(k),k)); extra=sorted(got-want,key=lambda k:(len(k),k))
        print(f"{d:11s} extracted {len(got):2d}  repo {len(want):2d}  missing={missing}  extra={extra}")
    print("staged ->",OUT)
