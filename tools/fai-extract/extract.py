#!/usr/bin/env python3
"""Extract the FAI ISC FS dive-pool diagrams from the CR PDF annexes (4-way +
8-way - the VFS annex is skipped -- its art is USPA's, "Images Copyright United
States Parachute Association", already shipped better in the USPA set). Annex
pages are LOCATED per edition from their running titles (locate(), never
hardcoded -- CR front matter and annex order drift every revision). Each page
embeds the complete art as a single native raster
(verified: a render adds only page furniture), so cells cut 1:1 from the
composited rasters, zero resample, saved as lossless webp at source size.

The pages carry key+name baked into the art (no per-cell text layer), so each cell's
key is READ by matching its baked top-left key glyph against a template library harvested
from the installed FAI set (key_templates / read_key, the same approach axis-extract uses on
its identical no-text-layer PDFs) -- never a hardcoded key list or grid position, so a pool
reorder or addition is picked up from the art itself. Cells are
cropped between the full extents of the detected grid lines, shedding only the
lines' own pixels and anti-alias fringe -- no original white space is removed
(gapped block-row seams keep both lines -- midpoint-merging them bled each row's
border into its neighbour). The figure variant erases the key and per-panel caption by connected
component: glyph components sit fully inside their corner/bottom zone and are
small, art dipping beside a caption belongs to a large component and survives,
and rotation arrows / 360-labels higher in the panel are never touched."""
import re, sys, os, subprocess, glob
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
PDF = f"{ROOT}/assets/sources/fai/fs.pdf"   # current edition (legacy driver overrides per edition)
REPO = f"{ROOT}/assets/diagrams"   # installed sets, harvested for key-glyph templates
INK = 120

# Top-left key location, as (H-frac, W-frac) - shared by erase_key (erases it) and keyglyph
# (reads it). FAI art is solid black like the key, so position + size isolate it, not colour.
KEY_ZONE = (0.22, 0.28)   # corner the key sits in
KEY_CAP = (0.16, 0.12)    # max single key-glyph component size

def native(page):
    """The page's largest embedded raster, composited over white through its
    smask (paired by PDF object number) when one is embedded. The page-raster cache
    is keyed by the source PDF (parent dir + stem) so the legacy driver can extract
    many editions in one process without page-number collisions."""
    sub = f"{os.path.basename(os.path.dirname(PDF))}_{os.path.splitext(os.path.basename(PDF))[0]}"
    stem = f"/tmp/faiext/nat/{sub}/p{page}"
    os.makedirs(os.path.dirname(stem), exist_ok=True)
    if not glob.glob(stem + "-*.png"):
        subprocess.run(["pdfimages", "-png", "-f", str(page), "-l", str(page), PDF, stem],
                       check=True, capture_output=True)
    lst = subprocess.run(["pdfimages", "-list", "-f", str(page), "-l", str(page), PDF],
                         check=True, capture_output=True, text=True).stdout
    rows = [{"num": int(f[1]), "type": f[2], "w": int(f[3]), "h": int(f[4]), "obj": f[10]}
            for f in (ln.split() for ln in lst.splitlines()[2:])]
    main = max((r for r in rows if r["type"] == "image"), key=lambda r: r["w"] * r["h"])
    arr = np.array(Image.open(f"{stem}-{main['num']:03d}.png").convert("RGB"))
    sm = next((r for r in rows if r["type"] == "smask" and r["obj"] == main["obj"]), None)
    if sm:
        a = np.array(Image.open(f"{stem}-{sm['num']:03d}.png").convert("L")).astype(float)[..., None] / 255
        arr = (arr * a + 255 * (1 - a)).round().astype(np.uint8)
    return arr

def runmax0(B):
    """Per-column longest vertical run of True (cumulative-run trick, vectorized)."""
    c = np.zeros(B.shape, np.int32); c[0] = B[0]
    for i in range(1, B.shape[0]): c[i] = (c[i - 1] + 1) * B[i]
    return c.max(0)

def runmax1(B):
    return runmax0(B.T)

def line_spans(dark, axis, frac):
    """Grid lines along an axis as full [lo, hi] extents (axis 0: horizontal lines
    by row, axis 1: vertical lines by column). A line qualifies by its longest
    contiguous run, so partial-width rules (per-column panel dividers) count."""
    H, W = dark.shape
    runs = runmax1(dark) if axis == 0 else runmax0(dark)
    idx = np.where(runs > frac * (W if axis == 0 else H))[0]
    spans = []
    for i in idx:
        if spans and i - spans[-1][1] <= 2: spans[-1][1] = int(i)
        else: spans.append([int(i), int(i)])
    return spans

centre = lambda s: (s[0] + s[1]) / 2

def runlen(b):
    """Longest run of True in a 1-d bool vector."""
    best = cur = 0
    for x in b:
        cur = cur + 1 if x else 0
        if cur > best: best = cur
    return best

def shrink(g, y0, y1, x0, x1):
    """Tighten bounds past full-length line residue: a row/col whose sub-white run
    spans most of the cell is grid-line core or anti-alias fringe; anything else
    (white, art) stops the walk -- so no original white space is ever cropped and
    line-hugging art keeps every pixel up to the line itself."""
    while y0 < y1 and runlen(g[y0, x0:x1] < 245) >= 0.7 * (x1 - x0): y0 += 1
    while y1 > y0 and runlen(g[y1 - 1, x0:x1] < 245) >= 0.7 * (x1 - x0): y1 -= 1
    while x0 < x1 and runlen(g[y0:y1, x0] < 245) >= 0.7 * (y1 - y0): x0 += 1
    while x1 > x0 and runlen(g[y0:y1, x1 - 1] < 245) >= 0.7 * (y1 - y0): x1 -= 1
    return y0, y1, x0, x1

def edge_fringe(g, y0, y1, x0, x1):
    """Consume the line fringe shrink's contiguous-run test misses on the outer
    edges: partial-height fringe (line beside some panels, white beside others --
    8-way 14/21) and full-height fringe broken by stray white px (8-way 6/22)
    both cap the longest run under 0.7, and the faintest fringe (248-253) sits
    above shrink's 245 entirely. A mostly-pale line (< 254 over >= 0.25 of its
    length) is fringe -- art at an edge measures <= 0.11, white 0 -- and so is a
    blank line directly shielding one (a halo detached across a 1px gap, 4-way
    G/O; the blank gate keeps the tunnel off art). The walk runs after shrink,
    so a white margin row still stops it before any caption or art."""
    frac = lambda v: (v < 254).mean()
    eat = lambda v, w: frac(v) >= 0.25 or (frac(v) < 0.02 and w is not None and frac(w) >= 0.25)
    while y0 < y1 and eat(g[y0, x0:x1], g[y0 + 1, x0:x1] if y0 + 1 < y1 else None): y0 += 1
    while y1 > y0 and eat(g[y1 - 1, x0:x1], g[y1 - 2, x0:x1] if y1 - 2 >= y0 else None): y1 -= 1
    while x0 < x1 and eat(g[y0:y1, x0], g[y0:y1, x0 + 1] if x0 + 1 < x1 else None): x0 += 1
    while x1 > x0 and eat(g[y0:y1, x1 - 1], g[y0:y1, x1 - 2] if x1 - 2 >= x0 else None): x1 -= 1
    return y0, y1, x0, x1

def edge_remnants(named):
    """Sides whose outer 2 px still hold a full-length line run or a mostly-pale
    fringe line (border/divider residue the crop should have consumed)."""
    g = named.mean(2)
    out = []
    for side, vecs in (("top", g[:2]), ("bottom", g[-2:]),
                       ("left", g[:, :2].T), ("right", g[:, -2:].T)):
        if any(runlen(v < 245) >= 0.7 * len(v) or (v < 254).mean() >= 0.25
               for v in vecs): out.append(side)
    return out

def despeckle(arr):
    """Remove source-raster dust in place: lone stray specks and 'ghosting' --
    shattered pale remnants of leftover art baked into the CR pages (8-way 21's
    free-bear ghost legs, block 9, the USIS starting-formation variant). Dust is
    a small non-spanning component (a full-width pale row is a divider's
    detached AA halo, not dirt) that either never reaches ink darkness (min
    luminance >= 185) or sits >= 12 px from all other ink (the stray dots on
    8-way C/K; every legitimate detached mark -- i-dot, degree sign, AA-split
    limb tip -- measures within ~4 px of its parent). Pale components are spared
    when they tail a text run (y-overlapping, x-adjacent to a glyph-sized dark
    component): the faintly-rendered degree rings of 8-way 21's inter labels
    never get darker than the ghost crumbs, but only they hug a digit."""
    g = arr.mean(2)
    ink = g < 245
    lab, n = ndimage.label(ink)
    sls = ndimage.find_objects(lab)
    mins = ndimage.minimum(g, lab, range(1, n + 1))
    glyph = [sls[j] for j in range(n)
             if mins[j] < 110
             and 3 <= sls[j][0].stop - sls[j][0].start <= 16
             and sls[j][1].stop - sls[j][1].start <= 30]
    for i, sl in enumerate(sls, 1):
        if sl[1].stop - sl[1].start >= 0.9 * arr.shape[1]: continue
        m = lab[sl] == i
        if m.sum() > 50: continue
        if g[sl][m].min() < 185:
            # mid-dark: dust only when isolated from every other ink component
            y0 = max(0, sl[0].start - 13); y1 = min(arr.shape[0], sl[0].stop + 13)
            x0 = max(0, sl[1].start - 13); x1 = min(arr.shape[1], sl[1].stop + 13)
            win = ink[y0:y1, x0:x1] & (lab[y0:y1, x0:x1] != i)
            if win.any() and ndimage.distance_transform_edt(~win)[lab[y0:y1, x0:x1] == i].min() < 12:
                continue
        elif any(sl[0].start < gs[0].stop and gs[0].start < sl[0].stop
                 and sl[1].start - gs[1].stop < 6 and gs[1].start - sl[1].stop < 6
                 for gs in glyph):
            continue
        # dilated paint, as in erase_glyphs: the speck's own unlabeled fringe
        # whisper goes too, never another component's pixels
        ey = slice(max(0, sl[0].start - 2), min(arr.shape[0], sl[0].stop + 2))
        ex = slice(max(0, sl[1].start - 2), min(arr.shape[1], sl[1].stop + 2))
        sub = lab[ey, ex]
        arr[ey, ex][ndimage.binary_dilation(sub == i, iterations=2)
                    & ((sub == i) | (sub == 0))] = 255
    return arr

def columns(spans):
    """Cell columns from sorted vertical-line spans: a cell is any adjacent line-pair
    whose gap is near the median cell width. Handles both block layouts -- paired-border
    strips (2026: own L+R per strip, narrow gutter between, 8 lines -> 4 cells - the gutter
    stays under the width threshold) and contiguous shared-border grids (2018/22: one line
    per boundary, equal gaps, 5 lines -> 4 cells). The earlier skip-ahead-by-two paired
    (0,1)(2,3) and dropped every other column on the contiguous grid."""
    xs = [centre(s) for s in spans]
    diffs = [b - a for a, b in zip(xs, xs[1:])]
    interior = np.median([d for d in diffs if d > 0.10 * (xs[-1] - xs[0])]) if diffs else 0
    return [(spans[i], spans[i + 1]) for i in range(len(spans) - 1)
            if 0.7 * interior < xs[i + 1] - xs[i] < 1.35 * interior]

# ---- glyph erase (operates in-place on an RGB panel crop) ----
def erase_glyphs(panel, zone, hcap, wcap, baseline=None):
    """White out the connected components lying FULLY inside zone (y0, y1, x0, x1)
    and under the size caps -- text glyphs are small and zone-bound, while art
    reaching into the zone belongs to a large component and survives. Components
    form on the fringe-inclusive mask (< 200, not < INK) WITHOUT dilation: an
    AA-thinned art joint (a foot tip on the caption row) stays connected to its
    parent and is spared, while dilating here would bridge a glyph to art above it
    and spare the glyph. Painting then dilates the erased component instead, so
    the glyph's outermost anti-alias fringe goes with it (no ghost outline) -- but
    spills only onto unlabeled fringe, never onto another component's pixels (a
    caption descender two px off a frame border must not nibble the border).

    With `baseline` set, candidates erase only if they belong to the caption's
    own text cluster -- y-overlapping, x-adjacent components (i-dots and hyphens
    included) of which at least one reaches within baseline*H of the panel bottom
    (caption bottoms measure <= 4.7% of panel height across every FAI/USIS panel)
    and which number >= 3. DETACHED art in the band is small and zone-bound too,
    and without this test the erase swallowed it whole, invisibly to the partial-
    component audit: art floating higher (a leg piece split off by an AA gap, a
    rotation arrow, a 360-degree label) fails the baseline reach, and art at
    caption height (8-way 20's mid-panel foot, 76px left of 'Inter') is x-distant
    and under-sized as a cluster of its own."""
    H, W = panel.shape[:2]
    lab, n = ndimage.label(panel.mean(2) < 200)
    y0, y1, x0, x1 = zone
    cand = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None: continue
        sy, sx = sl
        if (sy.start >= y0 and sy.stop <= y1 and sx.start >= x0 and sx.stop <= x1
                and sy.stop - sy.start <= hcap and sx.stop - sx.start <= wcap):
            cand.append((i, sy, sx))
    if baseline is not None:
        # Candidates cluster by y-overlap plus x-adjacency (0.14*W spans word gaps,
        # measured <= 24px; on-row art sits >= 76px off the text), and a cluster
        # erases only if some member's bottom reaches within baseline*H of the
        # panel bottom AND it has >= 3 members (every caption measures >= 3
        # components) -- a lone seeded foot tip ON the caption row stays. Tiny
        # components (<= 6px sides) also join across a small y-GAP: an i-dot
        # hovers overlap-free above an all-lowercase word body (Bunyip, Marquis,
        # Iroquois), while the kept 360/540 labels (digits 12-13px tall, >= 12px
        # above their row -- one touches it at gap 0) match neither test.
        gap = 0.14 * W
        tiny = lambda c: c[1].stop - c[1].start <= 6 and c[2].stop - c[2].start <= 6
        adj = lambda a, b: (a[2].start - b[2].stop < gap and b[2].start - a[2].stop < gap
                            and ((a[1].start < b[1].stop and b[1].start < a[1].stop)
                                 or ((tiny(a) or tiny(b))
                                     and a[1].start - b[1].stop <= 8
                                     and b[1].start - a[1].stop <= 8)))
        clusters = []
        for c in cand:
            mine = [cl for cl in clusters if any(adj(c, m) for m in cl)]
            clusters = [cl for cl in clusters if cl not in mine] + [[c] + sum(mine, [])]
        cand = [c for cl in clusters
                if len(cl) >= 3 and any(H - m[1].stop <= baseline * H for m in cl)
                for c in cl]
    for i, sy, sx in cand:
        ey = slice(max(0, sy.start - 2), min(H, sy.stop + 2))
        ex = slice(max(0, sx.start - 2), min(W, sx.stop + 2))
        sub = lab[ey, ex]
        panel[ey, ex][ndimage.binary_dilation(sub == i, iterations=2)
                      & ((sub == i) | (sub == 0))] = 255

def erase_key(panel):
    """Key glyph: digits/letter in the top-left corner of the (first) panel. Zone + size caps
    (KEY_ZONE / KEY_CAP) are shared with keyglyph, which reads the same glyph for naming."""
    H, W = panel.shape[:2]
    erase_glyphs(panel, (0, int(KEY_ZONE[0] * H), 0, int(KEY_ZONE[1] * W)),
                 int(KEY_CAP[0] * H), int(KEY_CAP[1] * W))

def erase_caption(panel):
    """Caption (name / 'Inter') in the bottom band of a panel -- full width, since a
    long name ('Compressed Stairstep Diamonds') can run nearly edge to edge. The
    baseline test (0.07: between the 4.7% glyph max and 9.8% art min) confines the
    erase to the caption's own text row."""
    H, W = panel.shape[:2]
    erase_glyphs(panel, (H - int(0.20 * H), H, 0, W), int(0.12 * H), int(0.30 * W),
                 baseline=0.07)

def sliced_components(named, fig):
    """Partial-component invariant: the erase takes an ink component whole (a glyph)
    or leaves it whole (art) -- a count here means a zone misfired into art. Cell-
    spanning components (a panel divider, a USIS frame border) are exempt: a caption
    descender can fuse into a divider (8-way 15 "Zippers"), and erasing that glyph
    legitimately takes part of the merged component."""
    ni = named.mean(2) < 200
    removed = ni & (fig.mean(2) >= 200)
    lab, n = ndimage.label(ni)
    r = ndimage.sum_labels(removed, lab, range(1, n + 1))
    t = ndimage.sum_labels(ni, lab, range(1, n + 1))
    spans = np.array([sl is not None and sl[1].stop - sl[1].start >= 0.9 * named.shape[1]
                      for sl in ndimage.find_objects(lab)])
    return int(((r > 8) & (r < t) & ~spans).sum())

def save(arr, path):
    Image.fromarray(arr).save(path, "WEBP", lossless=True, quality=100, method=6)

# ---- key reading (match the baked key glyph vs templates from the installed set) ----
GLYPH_OK = 0.10   # key-match mismatch fraction ceiling before a CHECK flag

def keyglyph(panel):
    """Binary crop of the baked top-left key (a letter A-Q, or a 1-2 digit block number),
    or None when the corner holds no glyph. Isolated by the same top-left zone + size caps
    erase_key uses: FAI art is solid black like the key, so position and size separate them,
    not colour (the trick axis-extract leans on with its grey art). Two-digit keys land as two
    components inside the zone - their union is cropped to one mask so '10'..'22' read whole."""
    H, W = panel.shape[:2]
    lab, _ = ndimage.label(panel.mean(2) < INK)
    y1z, x1z = int(KEY_ZONE[0] * H), int(KEY_ZONE[1] * W)
    hcap, wcap = int(KEY_CAP[0] * H), int(KEY_CAP[1] * W)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None: continue
        sy, sx = sl
        if (sy.stop <= y1z and sx.stop <= x1z
                and sy.stop - sy.start <= hcap and sx.stop - sx.start <= wcap):
            boxes.append((sy.start, sy.stop, sx.start, sx.stop, i))
    if not boxes:
        return None
    y0, y1 = min(b[0] for b in boxes), max(b[1] for b in boxes)
    x0, x1 = min(b[2] for b in boxes), max(b[3] for b in boxes)
    return np.isin(lab[y0:y1, x0:x1], [b[4] for b in boxes])

def glyph_dist(a, b):
    """Mismatch fraction of two key crops, centre-padded to a common box. Every cell of one
    edition bakes its key at one pixel size, so no rescale -- a size gate rejects a different
    key-string length (a 1-digit vs a 2-digit block) outright."""
    if abs(a.shape[0] - b.shape[0]) > 5 or abs(a.shape[1] - b.shape[1]) > 7:
        return 1.0
    H, W = max(a.shape[0], b.shape[0]), max(a.shape[1], b.shape[1])
    pads = []
    for g in (a, b):
        p = np.zeros((H, W), bool)
        y, x = (H - g.shape[0]) // 2, (W - g.shape[1]) // 2
        p[y:y + g.shape[0], x:x + g.shape[1]] = g
        pads.append(p)
    return float((pads[0] ^ pads[1]).mean())

def key_templates():
    """Key string -> key-glyph crops, harvested from the installed (verified-correct) FAI
    cards of both disciplines. The filename IS the key and the baked art IS the glyph, so the
    key->glyph map is read from shipped ground truth -- no hardcoded list. (13_indoor bakes a
    plain '13' - the keyless starting-formation cards are skipped.)"""
    lib = {}
    for d in ("4-way", "8-way"):
        for rf in sorted(glob.glob(f"{REPO}/{d}/FAI/*.webp")):
            base = os.path.basename(rf)[:-5].split("_")[0]
            if base == "starting-formation":
                continue
            arr = np.array(Image.open(rf).convert("RGB"))
            H, W = arr.shape[:2]
            if H > 1.5 * W: arr = arr[:H // 3]   # block strip: the key sits in panel 1 only
            g = keyglyph(arr)
            if g is not None:
                lib.setdefault(base, []).append(g)
    return lib

def read_key(panel, lib):
    """Best-matching template key for a cell crop - returns (key, dist, runner-up dist)."""
    g = keyglyph(panel)
    if g is None:
        return None, 1.0, 1.0
    scores = sorted((min(glyph_dist(g, t) for t in temps), key)
                    for key, temps in lib.items())
    return scores[0][1], scores[0][0], (scores[1][0] if len(scores) > 1 else 1.0)

# ---- page location (running titles, never hardcoded -- annex pagination drifts per edition) ----
# Key on the stable core 'CURRENT [INDOOR ][VERTICAL ]FORMATION SKYDIVING <N>-WAY <BLOCK|RANDOM>
# POOL' shared by every edition - the prefix drifts ('Addendum <L> -' 2018, none 2022-24,
# 'ANNEX <L> -' 2025-26) so it is not matched. The optional 'INDOOR' word marks the Indoor CR's
# 8-way pool (usis.py), distinct from the outdoor 8-way. 'current' anchors the title, never in body.
ANNEX = re.compile(
    r'current\s+(indoor\s+)?(vertical\s+)?formation\s+skydiving'
    r'\s+(\d+)\s*-?\s*way\s+(block|random)\s+pool', re.I)

def page_annex(text):
    """The single annex a page is the title page OF, as (style, width, section, indoor), else None.
    Only an annex's title (first) page carries the running title - continuation pages do not, so
    the block-span logic in locate() stays correct. A TOC dot-leader line and the contents page
    (which lists every annex) are rejected by keeping only a page that names exactly one annex."""
    found = set()
    for line in text.splitlines():
        if '..' in line: continue
        m = ANNEX.search(line)
        if m:
            found.add(("VFS" if m.group(2) else "FS", int(m.group(3)), m.group(4).lower(), bool(m.group(1))))
    return next(iter(found)) if len(found) == 1 else None

def locate(pdf, style="FS", widths=(4, 8), indoor=False):
    """Map each requested discipline to (randoms_page, [block_pages]) by reading the annex
    running titles. A block annex spans from its title page to the next annex's - a random annex
    is one page. Every annex (incl. VFS / indoor) is read to bound the spans, then ones off the
    requested style / width / indoor flag dropped (usis.py asks for indoor 8-way)."""
    pages = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                           capture_output=True, text=True, check=True).stdout.split("\f")
    hits = {}
    for n, pg in enumerate(pages, 1):
        a = page_annex(pg)
        if a: hits[n] = a
    starts = sorted(hits)
    jobs = {}
    for i, p in enumerate(starts):
        st, width, section, ind = hits[p]
        end = starts[i + 1] - 1 if i + 1 < len(starts) else len(pages)
        if st != style or width not in widths or ind != indoor: continue
        j = jobs.setdefault(f"{width}-way", {"rand": None, "blocks": []})
        if section == "random": j["rand"] = p
        else: j["blocks"] = list(range(p, end + 1))
    return {d: (j["rand"], j["blocks"]) for d, j in jobs.items()}

# ---- page geometry ----
def extract_randoms(page):
    """4x4 contiguous grid (16 randoms A-Q, shared borders). Row edges anchor on the
    detected H-lines at the rows' OWN pitch (their median spacing), not the column width:
    cells are square on recent editions but ~3% shorter than wide on 2018, and assuming
    square overshot the raster. Column width is only a fallback pitch when under two H-lines
    are found. Some pages (p20) render the top border at < half width, missing detection, so
    the grid is reconstructed by pitch and each predicted edge refines to a detected span -
    an anchor whose grid would fall off the raster is rejected, the per-edge fallback clamped."""
    arr = native(page); H = arr.shape[0]; dark = arr.mean(2) < INK
    vs = line_spans(dark, 1, 0.45)
    hs = line_spans(dark, 0, 0.40)
    w = float(np.median([centre(b) - centre(a) for a, b in zip(vs, vs[1:])]))
    ph = float(np.median([centre(b) - centre(a) for a, b in zip(hs, hs[1:])])) if len(hs) > 1 else w
    # prefer the highest score, then the TOPMOST grid (weak top borders on some pages tie a correct
    # top-anchored grid with a wrong one built into blank space). Track the best grid that FITS the
    # raster and the best overall - the fit guard can reject every anchor (over-estimated pitch), so
    # fall back to the best overall, then to a raster-top anchor when there are no H-lines at all.
    best = fitted = None
    for ln in hs:
        for k in range(4):
            y0 = centre(ln) - k * ph
            edges = [y0 + j * ph for j in range(5)]
            score = sum(1 for e in edges if any(abs(e - centre(l)) < 0.10 * ph for l in hs))
            if best is None or score > best[0] or (score == best[0] and y0 < best[1]):
                best = (score, y0)
            if -0.02 * ph <= edges[0] and edges[-1] <= H + 0.02 * ph and (   # grid fits the raster
                    fitted is None or score > fitted[0] or (score == fitted[0] and y0 < fitted[1])):
                fitted = (score, y0)
    best = fitted or best or (0, 0.0)
    rows = []
    for j in range(5):
        e = best[1] + j * ph
        snap = next((l for l in hs if abs(centre(l) - e) < 0.10 * ph), None)
        rows.append(snap if snap else [min(max(round(e), 0), H - 1)] * 2)
    return arr, vs, rows

def extract_blocks(page):
    """4 cols x 2 block-rows; each block = a 3-panel strip bounded by 4 H-line spans.
    Adjacent block-rows either share their seam line or sit gapped (two close lines);
    only near-duplicate lines (< 0.1 pitch) merge, then strips walk line-to-line,
    skipping a gap seam to the next row's own top line."""
    arr = native(page); H, W = arr.shape[:2]
    dark = arr.mean(2) < INK
    cols = columns(line_spans(dark, 1, 0.28))
    hs = line_spans(dark, 0, 0.10)
    cents = [centre(s) for s in hs]
    pitch = float(np.median([d for d in (b - a for a, b in zip(cents, cents[1:])) if d > 0.05 * H]))
    merged = [hs[0]]
    for s in hs[1:]:
        if centre(s) - centre(merged[-1]) < 0.1 * pitch: merged[-1] = [merged[-1][0], s[1]]
        else: merged.append(s)
    boxes, i = [], 0
    while i + 3 < len(merged):
        boxes.append(tuple(merged[i:i + 4]))
        i += 3
        # gapped seam: the next row's top border is its own line just below this bottom
        if i + 1 < len(merged) and centre(merged[i + 1]) - centre(merged[i]) < 0.5 * pitch:
            i += 1
    return arr, cols, boxes

# ---- crop + write + QA ----
def cut(arr, top, bot, left, right):
    """Cell interior between line spans, shrunk past the lines' anti-alias fringe
    only -- no original white space (or line-hugging art) is cropped away. Also
    returns the cell's source-row origin (block panel slices need it)."""
    g = arr.mean(2)
    y0, y1, x0, x1 = edge_fringe(g, *shrink(g, top[1] + 1, bot[0], left[1] + 1, right[0]))
    return arr[y0:y1, x0:x1].copy(), y0

def audit(key, named, fig):
    """Self-check: no line residue on a crop's outer 2px (under-shrunk border), no
    ink component partially erased (art sliced), and no glyph-sized components
    left in any caption zone of the figure (missed erase)."""
    warns = []
    sliced = sliced_components(named, fig)
    if sliced: warns.append(f"{sliced} art component(s) sliced")
    warns += [f"{side} line remnant" for side in edge_remnants(named)]
    H, W = fig.shape[:2]
    bands = 3 if H > 1.5 * W else 1
    for b in range(bands):
        y1 = round((b + 1) * H / bands)
        panel = fig[round(b * H / bands):y1].copy()
        before = (panel.mean(2) < INK).sum()
        erase_caption(panel)
        if before - (panel.mean(2) < INK).sum() > 40: warns.append(f"panel{b + 1} caption remnant")
    for w in warns: print(f"  !! {key}: {w}")
    return len(warns)

def montage(items, path, cell_w=260):
    """items: list of (label, np.array). Tiled grid montage for visual QA."""
    ims = []
    for lab, a in items:
        im = Image.fromarray(a); h = round(im.height * cell_w / im.width)
        ims.append(im.resize((cell_w, h), Image.LANCZOS))
    maxh = max(i.height for i in ims); cols = 8
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * (maxh + 4)), (235, 235, 235))
    for n, im in enumerate(ims):
        sheet.paste(im, ((n % cols) * cell_w, (n // cols) * (maxh + 4)))
    sheet.save(path)

def process(disc, rand_page, block_pages, lib=None, keys=None, outroot="/tmp/faiext/out"):
    """keys=None glyph-reads each cell (live path). A list assigns the canonical pool order by
    grid position, skipping empty slots -- the legacy corpus uses this since older editions'
    key letterforms defeat the glyph match (validate_ordering enforces the same fixed order)."""
    d = f"{outroot}/{disc}"; os.makedirs(f"{d}/figures", exist_ok=True)
    named_qa, fig_qa, warns, seen = [], [], 0, set()
    kit = iter(keys) if keys is not None else None
    def assign(cell, region=None):
        if kit is not None:
            if (cell.mean(2) < INK).mean() < 0.003: return None, 0.0, 0.0   # empty slot, no key consumed
            return next(kit, None), 0.0, 0.0
        return read_key(region if region is not None else cell, lib)

    def stage(key, dist, dist2, named, fig):
        nonlocal warns
        if key in seen:
            print(f"  !! {disc}/{key}: read twice, second cell dropped"); warns += 1
            return
        seen.add(key)
        # figure despeckled after its erase: a spared caption-hugging crumb loses its
        # anchor glyphs with the caption and goes too
        despeckle(named); despeckle(fig)
        warns += audit(f"{disc}/{key}", named, fig)
        save(named, f"{d}/{key}.webp"); save(fig, f"{d}/figures/{key}.webp")
        named_qa.append((key, named)); fig_qa.append((key, fig))
        if kit is None:   # glyph mode only: flag a low-confidence key match (no match in position mode)
            flag = "" if dist < GLYPH_OK and dist2 > 2 * dist else f"  CHECK key dist={dist:.3f} next={dist2:.3f}"
            if flag: print(f"  {disc}/{key}:{flag}")

    # randoms (key read from each cell's baked glyph, not its grid position)
    arr, vs, rows = extract_randoms(rand_page)
    for r in range(len(rows) - 1):
        for c in range(len(vs) - 1):
            named, _ = cut(arr, rows[r], rows[r + 1], vs[c], vs[c + 1])
            key, dist, dist2 = assign(named)
            if key is None: continue
            fig = named.copy(); erase_key(fig); erase_caption(fig)
            stage(key, dist, dist2, named, fig)
    # blocks (each = 3-panel strip with its dividers kept - key baked top-left of panel 1)
    for pg in block_pages:
        arr, cols, boxes = extract_blocks(pg)
        for (top, d1, d2, bot) in boxes:
            for (left, right) in cols:
                named, org = cut(arr, top, bot, left, right)
                # panel content bounds in crop coords -- divider cores excluded by
                # the span slices, then shrunk past the lines' AA fringe: those
                # rows otherwise form a full-width sub-white component INSIDE the
                # slice that a caption descender fuses with, hiding its glyph from
                # the erase (8-way 15 "Zippers" kept both p's)
                g = named.mean(2)
                raw = [0, d1[0] - org, d1[1] + 1 - org, d2[0] - org, d2[1] + 1 - org, named.shape[0]]
                p = [v for s in range(3)
                     for v in shrink(g, raw[2 * s], raw[2 * s + 1], 0, named.shape[1])[:2]]
                key, dist, dist2 = assign(named, named[p[0]:p[1]])
                if key is None: continue
                fig = named.copy()
                erase_key(fig[p[0]:p[1]])
                for s in range(3):
                    erase_caption(fig[p[2 * s]:p[2 * s + 1]])
                stage(key, dist, dist2, named, fig)
    montage(named_qa, f"/tmp/faiext/qa_{disc}_named.png")
    montage(fig_qa, f"/tmp/faiext/qa_{disc}_fig.png")
    print(f"{disc}: {len(seen)} cards warnings={warns} -> {d}")

if __name__ == "__main__":
    os.makedirs("/tmp/faiext/nat", exist_ok=True)   # extraction + QA staging
    lib = key_templates()
    assert lib, "no FAI key templates harvested -- is the FAI set installed under assets/diagrams?"
    JOBS = locate(PDF)
    for disc, (rp, bps) in JOBS.items():
        process(disc, rp, bps, lib)
