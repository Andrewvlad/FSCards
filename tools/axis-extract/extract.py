#!/usr/bin/env python3
"""Re-cut the Axis image sets from the AXIS Flight School dive-pool PDFs.

The PDFs (mPDF output from the AXIS Draw Generator) embed each card as a single
flate-compressed raster — 300x300 for randoms/formations, 300x900 for blocks
(3 panels with the divider lines baked in). Key, name, INTER, rotation labels
and the (c) AXIS tag are all baked into that raster; only the thin black cell
border around it is PDF-drawn. So the embedded image IS the full native-quality
card content "just inside the border": extract it losslessly, never resample.
(Rendering pages instead — the old approach — only bilinear-upscales these same
rasters ~2.85x at 600 DPI and re-includes the border.)

Cards carry no PDF text layer, but every card bakes its pool key top-left in
one consistent generator font. Embeds are keyed by matching that glyph crop
against a template library harvested from the installed (verified-correct)
sets, so the pipeline is embed-driven: a pool revision's new keys stage
themselves, art revisions land under their stable key, and keys missing from
the staging are pool drops for install.py to delete. The figures/ erasure is
geometric: connected components of solid-black ink, killing only the top-left
key and each panel's bottom centred name line, keeping the (c) AXIS tag, panel
dividers, rotation arrows/labels and all art.

Sources (committed under assets/sources/axis/; originally downloaded via
axisflightschool.com -> Draw Generator -> Dive Pools): fs4, fs4_cism (claims
only R/Bundy, the rest of the CISM pool duplicates fs4), fs8, fs8_indoor
(13/17/20 _indoor + starting-formation), fs10, fs16, vfs2, vfs4 (FAI-ISC
version — the USPA variant bakes a YouTube badge into block 12's inter),
mfs2, fs2 (collegiate), cf2 (each card embedded twice; either copy matches),
cf4.
"""
import hashlib, os, glob, shutil, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from slugs import JOBS, pdf_slug

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
SRC = f"{ROOT}/assets/sources/axis"
CACHE = "/tmp/axis_embeds"
OUT = "/tmp/axis_out"
REPO = f"{ROOT}/assets/diagrams"

CARD_SIZES = {(300, 300), (300, 900)}  # anything else (header banners, legend pages) is not a card
INK_BLACK = 110   # max(rgb) below this = solid black ink; grey art is ~179, colours have one high channel
HALO = 2          # px ring of anti-alias residue whited around an erased glyph
MIN_STAGED_RATIO = 0.5   # staged/installed floor - a resolution bump stages 0 cards, must fail loud not open an empty PR


def embeds(pdf):
    """All embedded card images of a PDF, extracted losslessly (cached).

    The cache tag carries the PDF's content hash: a filename-only tag would
    silently serve the previous PDF's embeds on a re-run after an upstream
    revision lands."""
    with open(os.path.join(SRC, pdf), "rb") as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:8]
    tag = os.path.join(CACHE, f"{pdf[:-4]}-{digest}")
    if not glob.glob(tag + "-*.png"):
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(["pdfimages", "-png", os.path.join(SRC, pdf), tag], check=True)
    out = []
    for f in sorted(glob.glob(tag + "-*.png")):
        im = Image.open(f)
        if im.size in CARD_SIZES:
            out.append((f, np.array(im.convert("RGB"))))
    return out


def keyglyph(arr):
    """Binary crop of the baked top-left key, or None when the card has none.

    Solid-black comps confined to the first panel's top-left corner, tall
    enough to be key glyphs: art specks and vfs2's camera-dart centre dot are
    shorter, the (c) AXIS tag sits right of 0.32W, annotations float lower."""
    H, W = arr.shape[:2]
    black = arr[..., :3].max(2) < INK_BLACK
    seprows = np.where(black.mean(1) > 0.97)[0]
    ph = int(seprows.min()) if len(seprows) else H   # first panel only on blocks
    lab, _ = ndimage.label(black, structure=np.ones((3, 3)))
    boxes = [(sl[0].start, sl[0].stop, sl[1].start, sl[1].stop, i)
             for i, sl in enumerate(ndimage.find_objects(lab), 1)
             if sl[0].stop <= 0.22 * ph and sl[1].stop <= 0.32 * W
             and sl[0].stop - sl[0].start >= 0.08 * ph]
    if not boxes:
        return None
    y0, y1 = min(b[0] for b in boxes), max(b[1] for b in boxes)
    x0, x1 = min(b[2] for b in boxes), max(b[3] for b in boxes)
    # mask to the key comps alone so art sharing the bbox can't pollute the crop
    return np.isin(lab[y0:y1, x0:x1], [b[4] for b in boxes])


def glyph_dist(a, b):
    """Mismatch fraction of two key crops, centre-padded to a common box.

    All AXIS cards bake keys at the same pixel size, so no rescaling: a size
    gate rejects different-length key strings outright."""
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
    """Key string -> key-glyph crops, harvested from every installed Axis card."""
    lib = {}
    for d in JOBS:
        for rf in sorted(glob.glob(f"{REPO}/{d}/Axis/*.webp")):
            key = os.path.basename(rf)[:-5]
            base = key.split("_")[0]   # 13_indoor bakes a plain '13'
            if base == "starting-formation":
                continue   # no baked key
            g = keyglyph(np.array(Image.open(rf).convert("RGB")))
            if g is not None:
                lib.setdefault(base, []).append(g)
    return lib


def read_key(arr, lib):
    """Best template key for an embed; returns (key, dist, runner-up dist)."""
    g = keyglyph(arr)
    if g is None:
        return None, 1.0, 1.0
    scores = sorted((min(glyph_dist(g, t) for t in temps), key)
                    for key, temps in lib.items())
    return scores[0][1], scores[0][0], (scores[1][0] if len(scores) > 1 else 1.0)


def erase(arr, names=True):
    """Figure variant: white out the key + each panel's bottom name line, glyph-precisely.

    Solid-black connected components only — grey/red/yellow/blue art never qualifies.
    The name line = the bottom-most centred row of text-sized components of a panel,
    plus the wrapped first line directly above it when one exists ('Compressed /
    Stairstep Diamond') — recognised by text-tight leading and matching glyph height,
    which annotations (MFS's 'foot grip'), rotation labels and art specks never show.
    Erased glyphs take their <=HALO px anti-alias ring along, but never pixels of
    surviving ink."""
    a = arr.copy()
    H, W = a.shape[:2]
    black = a[..., :3].max(2) < INK_BLACK
    # panel dividers by row scan, not by component — art touching a divider merges
    # with it into one tall component, which must not break the panel split
    seprows = np.where(black.mean(1) > 0.97)[0]
    seps = []
    for r in seprows:
        if seps and r - seps[-1][-1] <= 5: seps[-1].append(int(r))
        else: seps.append([int(r)])
    bounds = [0] + [int(np.mean(g)) for g in seps] + [H]
    panels = list(zip(bounds, bounds[1:]))
    # mask the divider rows out of the glyph pass: a descender touching a divider
    # ('Jelly Roll', 'Opposed Stairstep') must stay a glyph-sized comp, not merge
    # into a full-width structural one and evade the erase. Its pixels inside the
    # solid black line are left behind, invisibly. The union pass masks a dilated
    # band, or the divider's grey anti-alias fringe would bridge art into glyphs.
    glyph = black.copy()
    nofringe = np.ones(H, bool)
    for grp in seps:
        glyph[grp[0]:grp[-1] + 1] = False
        nofringe[max(0, grp[0] - HALO):grp[-1] + 1 + HALO] = False
    lab, n = ndimage.label(glyph, structure=np.ones((3, 3)))
    # a black comp embedded in a large grey structure (badge box edges, art strokes) is
    # anti-alias of that art, not a glyph: glyphs sit on white, so their grey halo is at
    # most perimeter-sized, while art-attached specks join a mostly-grey region
    g3 = a[..., :3]
    greyish = (g3.max(2) >= INK_BLACK) & (g3.max(2) <= 210) & (g3.max(2) - g3.min(2) < 60)
    ulab, un = ndimage.label((black | greyish) & nofringe[:, None], structure=np.ones((3, 3)))
    ublack = np.bincount(ulab[black].ravel(), minlength=un + 1)
    ugrey = np.bincount(ulab[greyish].ravel(), minlength=un + 1)
    comps, greyskip = [], []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        if x1 - x0 >= 0.97 * W:   # full-width = a divider (or divider+art): structural, never erased
            continue
        m = lab[sl] == i
        u = ulab[sl][m][0]
        if ugrey[u] > 2.0 * ublack[u]:
            greyskip.append((i, y0, y1, x0, x1))
            continue
        comps.append((i, y0, y1, x0, x1))

    kill = np.zeros_like(black)
    py0, py1 = panels[0]
    for i, y0, y1, x0, x1 in comps:   # key: top-left of the first panel ((c) tag is right of 0.32W)
        if y0 >= py0 and y1 <= py0 + 0.22 * (py1 - py0) and x1 <= 0.32 * W:
            kill |= lab == i

    for py0, py1 in (panels if names else []):
        ph = py1 - py0
        cands = [c for c in comps
                 if c[1] >= py0 + 0.55 * ph and c[2] <= py1
                 and c[2] - c[1] <= 0.13 * ph and c[4] - c[3] < 0.9 * W]
        prev = None   # bbox of the erased name line, while checking for a wrapped first line
        while cands:
            anchor = max(cands, key=lambda c: c[2])
            ay0, ay1 = anchor[1], anchor[2]
            line = [c for c in cands
                    if min(c[2], ay1) - max(c[1], ay0) > 0.5 * min(c[2] - c[1], ay1 - ay0)]
            ly0, ly1 = min(c[1] for c in line), max(c[2] for c in line)
            # absorb detached fragments sitting in the line's band (i-dots, which a
            # deep descender anchor does not itself y-overlap), or they leak into —
            # and derail — the next iteration's cluster
            line += [c for c in cands if c not in line
                     and min(c[2], ly1) - max(c[1], ly0) > 0.6 * (c[2] - c[1])]
            cands = [c for c in cands if c not in line]
            ly0, ly1 = min(c[1] for c in line), max(c[2] for c in line)
            if prev and (prev[0] - ly1 > 0.3 * prev[1] or ly1 - ly0 < 0.7 * prev[1]):
                break                     # above the name at more than text leading, or in smaller
                                          # glyphs: an annotation ('foot grip') or art, not a wrap
            # the name is the centred x-run(s) of the line; art sharing its rows (loop
            # arcs, badge slivers) sits far off to a side and must not drag the
            # extent off-centre and reject — or get killed with — the name
            line.sort(key=lambda c: c[3])
            runs, cur = [], [line[0]]
            for c in line[1:]:
                if c[3] - cur[-1][4] <= 1.5 * (ay1 - ay0): cur.append(c)
                else: runs.append(cur); cur = [c]
            runs.append(cur)
            runs = [r for r in runs if 0.25 * W < (r[0][3] + r[-1][4]) / 2 < 0.75 * W]
            if not runs:
                continue                  # nothing centred on these rows — skip, keep looking
            killed = [c for r in runs for c in r]
            lx0, lx1 = min(c[3] for c in killed), max(c[4] for c in killed)
            for c in killed: kill |= lab == c[0]
            # a name glyph touching grey art ('Ritz', whose z meets the leg above it)
            # was grey-skipped; reclaim it if it is glyph-like and sits on this line —
            # bottom-aligned, near the line's median glyph height (art specks beside a
            # name are much shorter), within a glyph's reach of the line's extent
            lh = ay1 - ay0
            mh = float(np.median([c[2] - c[1] for c in killed]))
            for c in greyskip:
                if (c[2] - c[1] <= 0.13 * ph and abs(c[2] - ay1) <= 0.25 * lh
                        and c[2] - c[1] >= 0.6 * mh and c[3] > lx0 - 2 * lh and c[4] < lx1 + 2 * lh):
                    kill |= lab == c[0]
            stray = [c for c in cands if min(c[2], ay1) - max(c[1], ay0) > 0 and c[3] < lx1 and c[4] > lx0]
            if stray:
                print(f"    !! unerased glyph-sized comp(s) inside the name line: {stray}")
            if prev: break                # a name wraps to at most two lines
            prev = (ly0, ly1 - ly0)

    ring = ndimage.binary_dilation(kill, np.ones((2 * HALO + 1,) * 2)) & ~kill
    g = a[..., :3]
    faint = (g.max(2) >= INK_BLACK) & (g.max(2) < 252) & (g.max(2) - g.min(2) < 60)
    # never let the ring nick surviving art a killed glyph touched: spare ring pixels
    # hugging thick surviving ink (a glyph's own anti-alias is a thin film on white).
    # The divider band is exempt — anti-alias of an erased glyph that reached the
    # divider must still be whited, or it lingers as a ghost along the line
    core = ndimage.binary_erosion((black | greyish) & ~kill, np.ones((3, 3)))
    spare = ndimage.binary_dilation(core, np.ones((2 * HALO + 1,) * 2)) & nofringe[:, None]
    a[kill | (ring & faint & ~spare)] = 255
    return a


def remove_badges(arr):
    """White out the baked 'video courtesy of …' YouTube badges (8-way, 16-way and all
    VFS blocks but the revised 12 carry one; newer-template PDFs are badge-free).

    A badge = a solid bright-red play button (the suits' red is darker) inside a grey
    rounded-rect box with team-credit text. The box bounds come from flooding the
    near-white box INTERIOR from just above the button — the closed stroke seals the
    flood, so art outside the box can never be reached — then the whole box (+stroke)
    is whited and the panel divider it was pasted over is repainted across the gap
    from its surviving outside profile. Art the box was baked OVER is gone in the
    source itself; fragments poking out survive (as in the previously-shipped set)."""
    a = arr.copy()
    H, W = a.shape[:2]
    red = (a[..., 0] >= 200) & (a[..., 1] <= 40) & (a[..., 2] <= 40)
    rlab, _ = ndimage.label(red, np.ones((3, 3)))
    buttons = []
    for i, sl in enumerate(ndimage.find_objects(rlab), 1):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        h, w = y1 - y0, x1 - x0
        if h < 20 or w < 34 or not 1.1 <= w / h <= 2.0: continue
        m = rlab[sl] == i
        sub = a[y0:y1, x0:x1]
        hole = ((sub[..., :3].min(2) > 200) & ~m).mean()   # the white play triangle
        if m.mean() >= 0.78 and hole >= 0.04:
            buttons.append((y0, y1, x0, x1))
    removed = 0
    for y0, y1, x0, x1 in buttons:
        white = a[..., :3].min(2) >= 230
        cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
        # box layouts differ per discipline (the button may hug the box top), so try
        # seeds on each side of the button and take the first box-sized flood
        ys = xs = None
        for sy, sx in ((cy, x0 - 10), (cy, x1 + 10), (y1 + 4, cx), (y0 - 6, cx)):
            if not (0 <= sy < H and 0 <= sx < W and white[sy, sx]): continue
            seed = np.zeros_like(white)
            seed[sy, sx] = True
            t = ndimage.binary_propagation(seed, mask=white)
            tys, txs = np.where(t)
            if tys.max() - tys.min() <= 140 and txs.max() - txs.min() <= 140:
                ys, xs = tys, txs
                break
        if ys is None:
            print("    badge interior flood failed — skipped"); continue
        pad = 5   # box stroke + its anti-alias
        by0, by1 = max(0, ys.min() - pad), min(H, ys.max() + 1 + pad)
        bx0, bx1 = max(0, xs.min() - pad), min(W, xs.max() + 1 + pad)
        out = np.r_[0:bx0, bx1:W]
        ink_frac = (a[by0:by1][:, out, :3].min(2) < 230).mean(1)
        a[by0:by1, bx0:bx1] = 255
        for i, y in enumerate(range(by0, by1)):   # divider rows the box was pasted over
            if ink_frac[i] > 0.5:
                a[y, bx0:bx1] = np.median(a[y, out], 0).astype(a.dtype)
        print(f"    badge box {bx1 - bx0}x{by1 - by0} at y{by0} x{bx0}")
        removed += 1
    return a, removed


def save(arr, path):
    Image.fromarray(arr).save(path, "WEBP", lossless=True, quality=100, method=6)


GLYPH_OK = 0.10   # key-match mismatch fraction ceiling before a CHECK flag

if __name__ == "__main__":
    # argv = changed source-PDF basenames: only their disciplines re-cut (no args = all).
    # Staging is cleared so install.py sees exactly this run's disciplines
    only = set(sys.argv[1:])
    run = {d: s for d, s in JOBS.items() if not only or any(p in only for p, _ in s)}
    shutil.rmtree(OUT, ignore_errors=True)
    lib = key_templates()
    for d, sources in run.items():
        od = os.path.join(OUT, d)
        os.makedirs(os.path.join(od, "figures"), exist_ok=True)
        staged = {}
        for pdf, spec in sources:
            for f, arr in embeds(pdf):
                base, dist, dist2 = read_key(arr, lib)
                if spec:
                    # restricted source claims only its declared keys (fs8_indoor's
                    # outdoor-duplicate randoms fall through), an unkeyed embed is
                    # its starting-formation reference card
                    key = ("starting-formation" if base is None and "starting-formation" in spec
                           else next((k for k in spec if k.split("_")[0] == base), None))
                    # a garbage read with one unstaged spec key left is that key in a
                    # font no installed card bakes yet (fs4_cism's R until its first
                    # accepted install), claimed under the CHECK flag for review
                    if key is None and base is not None and dist >= GLYPH_OK:
                        left = [k for k in spec if k != "starting-formation" and k not in staged]
                        if len(left) == 1:
                            key = left[0]
                else:
                    if base is None:
                        print(f"  ?? {d}: unkeyed {arr.shape[1]}x{arr.shape[0]} embed skipped ({os.path.basename(f)})")
                    key = base
                if key is None:
                    continue
                if key in staged:
                    if np.array_equal(arr, staged[key][0]):
                        continue   # cf2 embeds every card twice
                    print(f"  !! {d}/{key}: differing duplicate embed kept out ({os.path.basename(f)})")
                    continue
                flag = "" if base is None or (dist < GLYPH_OK and dist2 > 2 * dist) \
                    else f"  CHECK key dist={dist:.3f} next={dist2:.3f}"
                staged[key] = (arr, flag)
        expected = len(glob.glob(f"{REPO}/{d}/Axis/*.webp"))   # installed cards = this run's floor (figures/ excluded)
        if len(staged) < MIN_STAGED_RATIO * expected:
            sys.exit(f"{d}: staged {len(staged)} cards, under half the {expected} installed - "
                     f"likely a source resolution change, check CARD_SIZES {CARD_SIZES}")
        for key in sorted(staged):
            arr, flag = staged[key]
            arr, nbadges = remove_badges(arr)
            save(arr, f"{od}/{key}.webp")
            save(erase(arr), f"{od}/figures/{key}.webp")
            note = f" badges={nbadges}" if nbadges else ""
            print(f"  {d}/{key}: {arr.shape[1]}x{arr.shape[0]}{note}{flag}")
        print(f"{d}: {len(staged)} cards")
    print("staged ->", OUT)
    slugs = sorted({s for p in only if (s := pdf_slug(p))}) if only else sorted(run)
    print("recut-slug:", " ".join(slugs))   # extract-axis-images.yml reads this for the PR branch suffix
