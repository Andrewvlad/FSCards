#!/usr/bin/env python3
"""Extract BLOCK sequences from a USPA SCM block appendix page (Ch.9 FS / Ch.7 Collegiate).
Each block = a 3-panel cell (formation / inter / formation) enclosed by black border
lines. The crop is bounded by those enclosing borders (cropped just inside them, keeping
the two internal panel-divider rules), matching the repo's tall block image exactly.

Edges are snapped to the black border lines, NOT to the block number:
  cell_top    = the detected horizontal line immediately ABOVE the number
  cell_bottom = the detected line nearest cell_top + 3*panel_pitch (a block is 3 panels)
Anchoring on the number instead (old approach) bled a sliver of the cell above into the
crop and, when the panel-pitch was mis-estimated, captured only the first panel.
Lines are detected PER COLUMN so a partially-empty bottom row (blocks 21/22) still works.
figure = same crop with all text erased via overlap (divider rules + inter arrows kept)."""
import re, numpy as np
import ext_rand
from PIL import Image

INK=110

def detect_cols(arr):
    H,W=arr.shape[:2]; dark=arr[...,:3].mean(2)<INK
    colrun=np.array([ext_rand.max_run(dark[:,c]) for c in range(W)])
    return [int(np.mean(c)) for c in ext_rand.clusters(np.where(colrun>0.30*H)[0],int(0.012*W))]

def col_hlines(arr, X0, X1):
    """Full-width horizontal lines within a single column's x-range (border lines and
    internal panel dividers both qualify). Per-column so partial rows don't drop lines."""
    sub=arr[:, X0:X1, :3].mean(2)<INK; W=X1-X0
    rowrun=np.array([ext_rand.max_run(sub[r,:]) for r in range(sub.shape[0])])
    idx=np.where(rowrun>0.60*W)[0]
    return [int(np.mean(c)) for c in ext_rand.clusters(idx,4)]   # cluster thick (2-3px) lines

def panel_pitch(lines):
    """Robust panel height from a column's line list. The raw median of consecutive line
    diffs is polluted by spurious full-width lines (wide grips / name text detected inside
    a panel) and by empty-cell gaps; one refinement round — keep diffs within +-30% of the
    initial median, re-take the median — recovers the true ~equal panel spacing."""
    if len(lines)<2: return None
    d=np.diff(lines); m=float(np.median(d))
    keep=d[(d>0.7*m)&(d<1.3*m)]
    return float(np.median(keep)) if len(keep) else m

def extract(page,dpi):
    arr=ext_rand.render(page,dpi); ws=ext_rand.words(page,dpi)
    cols=detect_cols(arr)
    # left-aligned block-number words, tagged with their column
    blocks=[]
    for w in ws:
        if not re.fullmatch(r'\d{1,2}',w[4].strip()): continue
        wx0,wy0=w[0],w[1]; key=w[4].strip()
        c=next((i for i in range(len(cols)-1) if cols[i]-3<=wx0<cols[i+1]),None)
        if c is None: continue
        X0,X1=cols[c],cols[c+1]
        # block numbers are left-aligned; centered numerics are name words (e.g. the
        # "69" in "Double 69"), not keys — reject those
        if (wx0-X0) > 0.15*(X1-X0): continue
        blocks.append((c,X0,X1,wy0,key))
    # per-column line list + panel pitch (median spacing; robust to a missed divider)
    lc={}
    for c,X0,X1,_,_ in blocks:
        if c not in lc: lc[c]=col_hlines(arr,X0,X1)
    out={}
    for c,X0,X1,wy0,key in blocks:
        lines=lc[c]
        above=[y for y in lines if y < wy0-2]
        if not above: continue
        cell_top=above[-1]                                   # border just above the number
        pitch=panel_pitch(lines) or (X1-X0)*436.0/553        # robust panel height
        target=cell_top+3*pitch                              # bottom border, 3 panels down
        cell_bot=min(lines,key=lambda y:abs(y-target))
        # snap to a real border only if one sits near the 3-panel mark; else trust 3*pitch
        # (handles a faint/undetected bottom border instead of grabbing the 2-panel divider)
        if abs(cell_bot-target) > 0.35*pitch: cell_bot=int(round(target))
        cx0,cy0,cx1,cy1=ext_rand.cell_inner(arr,X0,cell_top,X1,cell_bot)
        named=arr[cy0:cy1,cx0:cx1].copy()
        # 3 equal panels (start / inter / end); erase only each panel's bottom name + key,
        # keeping the mid-panel rotation labels so figure erasure never clips a limb
        Peff=(cell_bot-cell_top)/3.0
        panels=[(cell_top+i*Peff, cell_top+(i+1)*Peff) for i in range(3)]
        out[key]=(named, ext_rand.erase_names(arr,ws,cx0,cy0,cx1,cy1,panels))
    return out

if __name__=="__main__":
    import sys
    for pg in [int(x) for x in sys.argv[1:]]:
        res=extract(pg,150)
        print(f"p{pg}:",sorted(res.keys(),key=int))
        for k in sorted(res,key=int):
            n=res[k][0]; print(f"   {k}: {n.shape[1]}x{n.shape[0]}  AR={n.shape[1]/n.shape[0]:.2f}")
