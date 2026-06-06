#!/usr/bin/env python3
"""Extract the USIS set (FAI indoor 8-way pool) from the 2026 Indoor FS CR PDF,
committed at assets/sources/fai/fai_indoor_2026.pdf (originally fai.org).
Dive-pool pages: p26 blocks 1-8, p27 blocks 9-16, p28 blocks 17-22, p29 randoms
A-Q, p30 the two starting-formation reference cards.

Unlike the FS/VFS annexes (extract.py), every page's art is a complete native
raster (verified: a page render adds only title/footer text), so cells cut 1:1
from the composited rasters with zero resample, saved as lossless webp. Cells
shed their printed frame borders (line + anti-alias fringe only -- interior white
survives whole, matching the borderless USPA/Axis cells; block strips keep their
internal dividers); the figure key/name erase is the connected-component one
shared with extract.py -- run before the strip, while the borders and dividers
still span the whole cell and so are never glyph candidates (the old rectangle
wipes flat-cut any art reaching into the key window or a name band).
Staging lands in /tmp/usisext/; the set ships merged into the FAI set: only the
indoor-variant blocks install, renamed assets/diagrams/8-way/FAI/<13|17|20>_indoor.webp
(+ figures/ siblings), plus the two starting-formation cards. Every other staged
cell is byte-identical to extract.py's outdoor FAI cell (same embedded art in
both CRs, same pipeline) except block 21, which differs only by ~45 px of
anti-alias jitter -- the staged set doubles as a cross-PDF consistency check."""
import os, subprocess, glob
import numpy as np
from PIL import Image
from extract import (ROOT, runmax0, runmax1, line_spans, shrink, edge_fringe,
                     edge_remnants, despeckle, erase_glyphs, erase_key,
                     erase_caption, sliced_components, save, montage)

def clusters(idx, gap):
    """Cluster near-adjacent indices (a grid line's rows/cols) to their centres."""
    out = []
    for i in idx:
        if out and i - out[-1][1] <= gap: out[-1][1] = int(i)
        else: out.append([int(i), int(i)])
    return [int((a + b) / 2) for a, b in out]

PDF = f"{ROOT}/assets/sources/fai/fai_indoor_2026.pdf"
OUT = "/tmp/usisext"
INK = 110

def rasters(page):
    """All content rasters of a page (in placement order), each composited over
    white through its smask (paired by PDF object number) when one is embedded."""
    stem = f"{OUT}/nat/p{page}"
    if not glob.glob(stem + "-*.png"):
        subprocess.run(["pdfimages", "-png", "-f", str(page), "-l", str(page), PDF, stem],
                       check=True, capture_output=True)
    lst = subprocess.run(["pdfimages", "-list", "-f", str(page), "-l", str(page), PDF],
                         check=True, capture_output=True, text=True).stdout
    rows = [{"num": int(f[1]), "type": f[2], "obj": f[10]}
            for f in (ln.split() for ln in lst.splitlines()[2:])]
    out = []
    for r in (r for r in rows if r["type"] == "image"):
        arr = np.array(Image.open(f"{stem}-{r['num']:03d}.png").convert("RGB"))
        sm = next((s for s in rows if s["type"] == "smask" and s["obj"] == r["obj"]), None)
        if sm:
            a = np.array(Image.open(f"{stem}-{sm['num']:03d}.png").convert("L")).astype(float)[..., None] / 255
            arr = (arr * a + 255 * (1 - a)).round().astype(np.uint8)
        out.append(arr)
    return out

# ---- cell cropping (grid borders located by longest-run profiles) ----
def line_runs(b, minlen):
    out = []; s = None
    for i, v in enumerate(b):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s >= minlen: out.append((s, i - 1))
            s = None
    if s is not None and len(b) - s >= minlen: out.append((s, len(b) - 1))
    return out

def crop_blocks(arr, keys_by_band):
    """4 cols x 2 block-bands per page; cells cut between paired border verticals,
    band extents read off the first border column. The last page's second band has
    only blocks 21-22, so near-empty cells are skipped by ink fill."""
    B = np.array(Image.fromarray(arr).convert("L")) < INK
    xs = clusters(np.where(runmax0(B) >= 500)[0], 6)
    pairs = [(xs[2 * m], xs[2 * m + 1]) for m in range(len(xs) // 2)]
    bands = line_runs(B[:, max(0, xs[0] - 1):xs[0] + 2].any(1), 400)
    cells = {}
    for bi, (y0, y1) in enumerate(bands):
        for ci, (x0, x1) in enumerate(pairs):
            if ci >= len(keys_by_band[bi]): continue
            if B[y0:y1 + 1, x0:x1 + 1].mean() < 0.01: continue
            cells[keys_by_band[bi][ci]] = arr[y0:y1 + 1, x0:x1 + 1]
    return cells

def crop_randoms(arr):
    """Contiguous 4x4 grid: adjacent cells share their border lines."""
    B = np.array(Image.fromarray(arr).convert("L")) < INK
    xs = clusters(np.where(runmax0(B) >= 800)[0], 6)
    ys = clusters(np.where(runmax1(B) >= 800)[0], 6)
    rmap = [list("ABCD"), list("EFGH"), list("JKLM"), list("NOPQ")]
    return {rmap[r][c]: arr[ys[r]:ys[r + 1] + 1, xs[c]:xs[c + 1] + 1]
            for r in range(len(ys) - 1) for c in range(len(xs) - 1)}

# ---- figure variant: erase the corner key + per-panel name by connected
# component (extract.py's erasers). Art reaching into a zone belongs to a large
# component and survives -- the old rectangle wipes flat-cut it -- and the frame
# borders/dividers span the whole cell, so they are never glyph candidates. ----
def panels(arr):
    """Panel row-slices between the full-width line spans (frame top, dividers,
    frame bottom): three for a block strip, one for a random / starting card.
    Each slice is shrunk past the bounding lines' AA fringe (extract.shrink) --
    the line cores alone are excluded by the spans, and the fringe rows otherwise
    form a full-width sub-white component INSIDE the slice that a caption
    descender fuses with, hiding its glyph from the erase (8-way 15 "Zippers")."""
    g = arr.mean(2)
    dark = np.array(Image.fromarray(arr).convert("L")) < INK
    spans = line_spans(dark, 0, 0.55)
    return [shrink(g, a[1] + 1, b[0], 0, arr.shape[1])[:2]
            for a, b in zip(spans, spans[1:])]

def erase_figure(arr):
    ps = panels(arr)
    erase_key(arr[ps[0][0]:ps[0][1]])
    for a, b in ps:
        erase_caption(arr[a:b])
    return arr

def erase_start_label(arr):
    """Starting-formation cards: the 'Starting Formation' label is larger type than
    the pool captions ('Formation' alone spans ~0.36 W), so wider caps apply --
    with the same baseline-row confinement as erase_caption."""
    (a, b), = panels(arr)
    s = arr[a:b]; H, W = s.shape[:2]
    erase_glyphs(s, (H - int(0.25 * H), H, 0, W), int(0.10 * H), int(0.45 * W),
                 baseline=0.07)
    return arr

def strip_border(arr):
    """Row/col slices removing the printed frame border -- its line core and pale
    anti-alias fringe (extract.shrink, then edge_fringe for the partial/broken/
    faint fringe the run test misses) and nothing else, so every interior white
    pixel survives. Applied to named and figure alike after the erase."""
    g = arr.mean(2)
    y0, y1, x0, x1 = edge_fringe(g, *shrink(g, 0, arr.shape[0], 0, arr.shape[1]))
    return slice(y0, y1), slice(x0, x1)

def audit(key, named, fig, eraser):
    """Self-check: the partial-component invariant (sliced_components), plus an
    erase re-run on the figure expecting nothing further (missed glyph)."""
    warns = []
    sliced = sliced_components(named, fig)
    if sliced: warns.append(f"{sliced} art component(s) sliced")
    drop = (fig.mean(2) < INK).sum() - (eraser(fig.copy()).mean(2) < INK).sum()
    if drop > 40: warns.append(f"glyph remnant ({drop} px on re-run)")
    for w in warns: print(f"  !! {key}: {w}")
    return len(warns)

if __name__ == "__main__":
    d = f"{OUT}/8-way/USIS"
    os.makedirs(f"{d}/figures", exist_ok=True)
    os.makedirs(f"{OUT}/nat", exist_ok=True)

    cells = {}
    for page, bands in ((26, [["1", "2", "3", "4"], ["5", "6", "7", "8"]]),
                        (27, [["9", "10", "11", "12"], ["13", "14", "15", "16"]]),
                        (28, [["17", "18", "19", "20"], ["21", "22"]])):
        cells |= crop_blocks(rasters(page)[0], bands)
    cells |= crop_randoms(rasters(29)[0])

    named_qa, fig_qa, warns = [], [], 0
    for k in [str(n) for n in range(1, 23)] + list("ABCDEFGHJKLMNOPQ"):
        named = cells[k]
        fig = erase_figure(named.copy())
        warns += audit(k, named, fig, erase_figure)
        ys, xs = strip_border(named)
        # despeckle only after the strip: a speck just inside the printed frame
        # border fuses into the border component through its AA fringe and would
        # ride the spanning exemption (8-way E/F/G/J/O). The degree-ring spare
        # anchors on the kept rotation labels, so named and figure agree.
        named, fig = despeckle(named[ys, xs].copy()), despeckle(fig[ys, xs].copy())
        for side in edge_remnants(named):
            print(f"  !! {k}: {side} line remnant"); warns += 1
        save(named, f"{d}/{k}.webp"); save(fig, f"{d}/figures/{k}.webp")
        named_qa.append((k, named)); fig_qa.append((k, fig))

    # starting formations (p30, placement order: left card, then its variant)
    for arr, name in zip(rasters(30), ("starting-formation", "starting-formation_alt")):
        fig = erase_start_label(arr.copy())
        warns += audit(name, arr, fig, erase_start_label)
        ys, xs = strip_border(arr)
        arr, fig = despeckle(arr[ys, xs]), despeckle(fig[ys, xs])
        for side in edge_remnants(arr):
            print(f"  !! {name}: {side} line remnant"); warns += 1
        save(arr, f"{d}/{name}.webp"); save(fig, f"{d}/figures/{name}.webp")
        named_qa.append((name[-3:], arr)); fig_qa.append((name[-3:], fig))

    montage(named_qa, f"{OUT}/qa_usis_named.png")
    montage(fig_qa, f"{OUT}/qa_usis_fig.png")
    print(f"{len(named_qa)} cards -> {d}  (warnings: {warns})")
