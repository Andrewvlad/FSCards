#!/usr/bin/env python3
"""Extract RANDOM-formation cells from a USPA SCM appendix page (Ch.9 FS / Ch.7 Collegiate).
Crops each bordered box's interior (border pixels only — every interior white pixel kept),
reads its key+name from the text layer, and emits a named crop + a figure crop with the
key and bottom name line erased glyph-precisely.
Drivers point PDF at the right SCM chapter and give CACHE a per-chapter prefix (same page
numbers exist in both chapters — a shared cache would silently serve the wrong render)."""
import re, sys, os, subprocess, glob
from collections import deque
import numpy as np
from PIL import Image
ROOT=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"../.."))
PDF=f"{ROOT}/assets/sources/uspa/scm_fs.pdf"
CACHE="/tmp/fsx"
INK=110

def render(page,dpi):
    out=f"{CACHE}_r{page}_{dpi}"
    subprocess.run(["pdftoppm","-png","-r",str(dpi),"-f",str(page),"-l",str(page),PDF,out],check=True,capture_output=True)
    return np.array(Image.open(glob.glob(out+"*.png")[0]).convert("RGB"))

def words(page,dpi):
    h=f"{CACHE}_w{page}.html"
    subprocess.run(["pdftotext","-bbox","-f",str(page),"-l",str(page),PDF,h],check=True,capture_output=True)
    t=open(h,encoding='utf-8',errors='ignore').read(); s=dpi/72.0; ws=[]
    for m in re.finditer(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>',t):
        x0,y0,x1,y1=[float(v)*s for v in m.groups()[:4]]; ws.append([x0,y0,x1,y1,m.group(5)])
    return ws

def max_run(col):
    best=cur=0
    for v in col:
        cur=cur+1 if v else 0
        if cur>best:best=cur
    return best

def clusters(idx,gap):
    out=[]
    for i in idx:
        if out and i-out[-1][1]<=gap: out[-1][1]=i
        else: out.append([i,i])
    return out

def regular_edges(edges, n_expected=None):
    """Keep the longest run of ~equally spaced edges (drops header/footer strays)."""
    if len(edges)<3: return edges
    diffs=np.diff(edges); med=np.median(diffs)
    keep=[edges[0]]
    for i in range(1,len(edges)):
        if abs(edges[i]-keep[-1]-med) < 0.4*med or len(keep)==1 and abs(edges[i]-keep[-1])<1.6*med:
            keep.append(edges[i])
        elif edges[i]-keep[-1] > 1.6*med:
            # gap too big: stop extending (stray below grid)
            break
    return keep

def detect_grid(arr):
    H,W=arr.shape[:2]; dark=arr[...,:3].mean(2)<INK
    colrun=np.array([max_run(dark[:,c]) for c in range(W)])
    rowrun=np.array([max_run(dark[r,:]) for r in range(H)])
    vcols=np.where(colrun>0.20*H)[0]; hrows=np.where(rowrun>0.20*W)[0]
    xs=[int(np.mean(c)) for c in clusters(vcols,int(0.012*W))]
    ys=[int(np.mean(c)) for c in clusters(hrows,int(0.012*H))]
    ys=regular_edges(ys)
    return xs,ys

def find_key(inside,x0,y0,W):
    # topmost-leftmost short alnum token = the cell key
    cand=[w for w in inside if re.fullmatch(r'[A-HJ-Qa-q]|\d{1,2}',w[4].strip())]
    if not cand: return None
    cand.sort(key=lambda w:(w[1]-y0)*2+(w[0]-x0))
    return cand[0][4].strip().upper()

def band_inner(arr, coord, p0, p1, axis, step, thr=245, frac=0.80):
    """Inner edge of a border line. From the detected line cluster at `coord`, walk inward
    (`step`=+1 for a top/left edge, -1 for bottom/right) past every band row/col — a row/col
    is border band when >frac of its pixels across the cell's interior extent [p0,p1] are
    non-white (<thr, which also catches the anti-alias halo). Returns the first interior
    row/col, so the crop excludes ONLY border pixels — every interior white pixel is kept.
    (A fixed inset can't do this: SCM border thickness varies ~2px horizontal / ~17px
    vertical at 600 DPI, so the old dpi-scaled inset ate up to ~11px of interior white and
    let art that sits close to a thin border touch the crop edge — 8-way P/Venus.) The
    cluster mean can sit a few px off a thin line, so seek the band within +-30px first."""
    line=lambda i: arr[i,p0:p1,:3].mean(1) if axis==0 else arr[p0:p1,i,:3].mean(1)
    is_band=lambda i: (line(i)<thr).mean()>frac
    i=coord
    if not is_band(i):
        near=next((coord+d*s for d in range(1,31) for s in (step,-step) if is_band(coord+d*s)),None)
        if near is None: return coord       # no line at this edge (partial border): keep everything
        i=near
    while is_band(i+step): i+=step
    return i+step

def cell_inner(arr, X0, Y0, X1, Y1):
    """Border-free crop bounds for a cell whose border-line clusters sit at X0/Y0/X1/Y1.
    The perpendicular extent is inset 25px so corner intersections with the crossing
    border don't count toward the band fraction."""
    cx0=band_inner(arr,X0,Y0+25,Y1-25,1,+1)
    cx1=band_inner(arr,X1,Y0+25,Y1-25,1,-1)+1
    cy0=band_inner(arr,Y0,X0+25,X1-25,0,+1)
    cy1=band_inner(arr,Y1,X0+25,X1-25,0,-1)+1
    return cx0,cy0,cx1,cy1

def extract(page,dpi):
    arr=render(page,dpi); ws=words(page,dpi); H,W=arr.shape[:2]
    xs,ys=detect_grid(arr)
    out={}
    for r in range(len(ys)-1):
        for c in range(len(xs)-1):
            X0,Y0,X1,Y1=xs[c],ys[r],xs[c+1],ys[r+1]
            inside=[w for w in ws if w[0]>=X0-2 and w[2]<=X1+2 and w[1]>=Y0-2 and w[3]<=Y1+2]
            if not inside: continue
            key=find_key(inside,X0,Y0,W)
            if not key: continue
            cx0,cy0,cx1,cy1=cell_inner(arr,X0,Y0,X1,Y1)
            named=arr[cy0:cy1,cx0:cx1].copy()
            # single full-cell band: erase the key + the bottom name line only, so a
            # mid-cell description (MFS A 'Two-handed grip' / B 'Same Arm') is kept
            out[key]=(named, erase_names(arr,ws,cx0,cy0,cx1,cy1,[(cy0,cy1)]))
    return out

def wipe_word(crop, w, cx0, cy0, pad=10):
    """Glyph-precise erase of one text word in crop coords: hand the word's tight bbox to
    _wipe_text_preserve, padded so the figure-ink flood has an outside margin to seed from.
    Erasure never reaches above the glyph's own top (plus its <=2px halo) — the pad is
    flood seeding area, not erased area."""
    H,W=crop.shape[:2]
    wx0,wy0,wx1,wy1,_=w
    rx0=max(0,int(wx0-cx0)-pad); ry0=max(0,int(wy0-cy0)-pad)
    rx1=min(W,int(wx1-cx0)+pad); ry1=min(H,int(wy1-cy0)+pad)
    if rx1>rx0 and ry1>ry0:
        tbox=(int(wx0-cx0)-rx0, int(wy0-cy0)-ry0, int(wx1-cx0)-rx0, int(wy1-cy0)-ry0)
        _wipe_text_preserve(crop[ry0:ry1, rx0:rx1], tbox)

def _dilate(mask, it):
    for _ in range(it):
        e=mask.copy()
        e[1:,:]|=mask[:-1,:]; e[:-1,:]|=mask[1:,:]
        e[:,1:]|=mask[:,:-1]; e[:,:-1]|=mask[:,1:]
        mask=e
    return mask

def _wipe_text_preserve(region, tbox, ink=INK):
    """White out a name glyph inside `region` (an HxWx3 view) while PRESERVING figure ink (a
    foot/shoe or loop arc) that overlaps the glyph's bounding box. `tbox`=(tx0,ty0,tx1,ty1) is
    the glyph's tight bbox within the region; the region is padded a little beyond it. A glyph
    is ENCLOSED by its bbox; figure ink crosses the bbox boundary, so it stays connected to
    dark ink in the pad margin OUTSIDE the bbox. So flood dark pixels from that outside margin
    (8-way): whatever the flood reaches is figure ink (kept); the enclosed remainder is the
    glyph (erased, plus a 2px dilation to take its grey anti-aliased halo, so no ghost is left).
    Keying off the BBOX — not the region/crop border — is what lets a long name's end letters
    that touch the crop edge still be erased (e.g. the 'C'/'s' of 8-way 22's 'Compressed …
    Diamonds'); a border-seeded flood wrongly kept them. Limbs/loops are still preserved (e.g.
    MFS 3/14's 'Inter' arc and 'MindWarp' foot)."""
    h,w=region.shape[:2]
    dark=region[...,:3].mean(2)<ink
    if not dark.any(): return
    tx0,ty0,tx1,ty1=tbox
    textmask=np.zeros((h,w),bool)
    textmask[max(0,ty0):min(h,ty1), max(0,tx0):min(w,tx1)]=True
    # seed only from ink >2px outside the bbox: pdftotext boxes can run ~1px tight (the
    # MFS 'K' leg), and a 1px glyph overhang would otherwise seed the flood and preserve
    # the whole glyph. True figure ink crossing a label has plenty of ink past the guard.
    ext=dark & ~_dilate(textmask,2)            # dark ink clear of the glyph bbox = figure ink (seed)
    dq=deque(zip(*np.where(ext)))
    while dq:
        y,x=dq.popleft()
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                ny,nx=y+dy,x+dx
                if (dy or dx) and 0<=ny<h and 0<=nx<w and dark[ny,nx] and not ext[ny,nx]:
                    ext[ny,nx]=True; dq.append((ny,nx))
    glyph=dark & ~ext                          # dark enclosed in the bbox = the glyph
    region[_dilate(glyph,2) & ~ext]=255        # erase glyph + its halo; never touch figure ink

def erase_names(arr, words, cx0, cy0, cx1, cy1, panels):
    """Crop arr[cy0:cy1, cx0:cx1] and white out ONLY each panel's name plus the corner key
    — never the mid-panel rotation labels ('All 540°', 'Forward Flip', …). On USPA diagrams
    the panel name is the BOTTOM-most text line of the panel and the middle block panel's
    name is 'Inter'; rotation labels sit higher, among the jumper figures, so rectangling
    them out (the old erase-every-word approach) clipped limbs. `panels` is a list of
    (top, bottom) y-bands in full-image coords (one per block panel; a single band for a
    random cell). The key is the top-most-leftmost short alnum token in the crop."""
    crop=arr[cy0:cy1,cx0:cx1].copy()
    incrop=[w for w in words if w[2]>cx0 and w[0]<cx1 and w[3]>cy0 and w[1]<cy1 and w[4].strip()]
    # the key token (top-most-leftmost short alnum) — erased so the figure front hides it
    keyc=[w for w in incrop if re.fullmatch(r'[A-HJ-Qa-q]|\d{1,2}', w[4].strip())]
    if keyc: wipe_word(crop,min(keyc, key=lambda w:(w[1]-cy0)*2+(w[0]-cx0)),cx0,cy0)
    # each panel's name = its bottom-most text line (anchor = lowest word; include words on
    # the same line by y-centre, so the line above — a rotation label — is left untouched)
    for (ptop,pbot) in panels:
        inp=[w for w in incrop if w[1]>=ptop-3 and w[3]<=pbot+3]
        if not inp: continue
        anchor=max(inp,key=lambda w:w[1]); ac=(anchor[1]+anchor[3])/2; ah=anchor[3]-anchor[1]
        for w in inp:
            if abs((w[1]+w[3])/2-ac)<=0.6*ah: wipe_word(crop,w,cx0,cy0)
    return crop

if __name__=="__main__":
    page=int(sys.argv[1]); dpi=int(sys.argv[2])
    res=extract(page,dpi)
    print("keys:",sorted(res.keys(),key=lambda k:(len(k),k)))
    for k,(n,f) in res.items():
        print(f"  {k}: {n.shape[1]}x{n.shape[0]}")
