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

Cards carry no PDF text layer, so embeds are mapped to pool keys by visual
matching against the currently-installed (verified-correct) repo set, and the
figures/ erasure is geometric: connected components of solid-black ink, killing
only the top-left key and each panel's bottom centred name line, keeping the
(c) AXIS tag, panel dividers, rotation arrows/labels and all art.

Sources (committed under assets/sources/axis/; originally downloaded via
axisflightschool.com -> Draw Generator -> Dive Pools): fs4, fs8, fs8_indoor (13/17/20 _indoor +
starting-formation), fs10, fs16, vfs2, vfs4 (FAI-ISC version — the USPA variant
bakes a YouTube badge into block 12's inter), mfs2, fs2 (collegiate), cf2
(each card embedded twice; either copy matches), cf4. 4-way R/Bundy is not in
any AXIS pool (the AXIS CISM pool's R is Caterpillar, in a different art
style), so it is re-derived from block 12's entry panel — see derive_R.
"""
import os, glob, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
SRC = f"{ROOT}/assets/sources/axis"
CACHE = "/tmp/axis_embeds"
OUT = "/tmp/axis_out"
REPO = f"{ROOT}/assets/diagrams"

CARD_SIZES = {(300, 300), (300, 900)}  # anything else (header banners, legend pages) is not a card
INK_BLACK = 110   # max(rgb) below this = solid black ink; grey art is ~179, colours have one high channel
HALO = 2          # px ring of anti-alias residue whited around an erased glyph

# discipline -> [(pdf, restricted-key-set or None)]; None = source for every key
# not claimed by a restricted entry.
FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

JOBS = {
    "4-way":        [("fs4.pdf", None)],
    "8-way":        [("fs8.pdf", None),
                     ("fs8_indoor.pdf", {"13_indoor", "17_indoor", "20_indoor", "starting-formation"})],
    "10-way-speed": [("fs10.pdf", None)],
    "16-way":       [("fs16.pdf", None)],
    "4-way-vfs":    [("vfs4.pdf", None)],
    "2-way-mfs":    [("mfs2.pdf", None)],
    "2-way":        [("fs2.pdf", None)],
    "2-way-vfs":    [("vfs2.pdf", None)],
    "2-way-cf":     [("cf2.pdf", None)],
    "4-way-cf":     [("cf4.pdf", None)],
}


def embeds(pdf):
    """All embedded card images of a PDF, extracted losslessly (cached)."""
    tag = os.path.join(CACHE, pdf[:-4])
    if not glob.glob(tag + "-*.png"):
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(["pdfimages", "-png", os.path.join(SRC, pdf), tag], check=True)
    out = []
    for f in sorted(glob.glob(tag + "-*.png")):
        im = Image.open(f)
        if im.size in CARD_SIZES:
            out.append((f, np.array(im.convert("RGB"))))
    return out


def interior(path):
    """Installed repo card minus its baked border: walk each edge's dark band inward."""
    a = np.array(Image.open(path).convert("L"))
    H, W = a.shape
    def inner(i, step, axis):
        line = lambda j: a[j, 20:-20] if axis == 0 else a[20:-20, j]
        while (line(i) < 245).mean() > 0.8: i += step
        return i
    return a[inner(0, 1, 0):inner(H - 1, -1, 0) + 1, inner(0, 1, 1):inner(W - 1, -1, 1) + 1]


def match(repo_file, cands):
    """Best-matching embed for an installed card; returns (index, mse, runner-up mse)."""
    ref = interior(repo_file)
    aspect = ref.shape[0] / ref.shape[1]
    scores = []
    for i, (_, arr) in enumerate(cands):
        h, w = arr.shape[:2]
        if abs(h / w - aspect) > 0.15: continue
        r = np.asarray(Image.fromarray(ref).resize((w, h), Image.LANCZOS), float)
        g = arr[..., :3].mean(2)
        scores.append((((r - g) ** 2).mean(), i))
    scores.sort()
    return scores[0][1], scores[0][0], (scores[1][0] if len(scores) > 1 else float("inf"))


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


def derive_R(arr12):
    """4-way R/Bundy: block 12's entry panel cropped above the first divider, its
    '12' key swapped for a drawn 'R' (Liberation Sans Bold — the stand-in the old
    856px derivation used; the baked AXIS key font is not redistributable)."""
    black = arr12[..., :3].max(2) < INK_BLACK
    sep = int(np.where(black.mean(1) > 0.97)[0].min())
    while (arr12[sep - 1, :, :3].mean(1) < 245).mean() > 0.8: sep -= 1
    panel = arr12[:sep].copy()
    # R is a random: shed the block iconage — blocks suit a reference pair in
    # red (239,0,0) / blue (0,176,240) to track across panels, while randoms
    # are all greyscale. Un-mix the tint per pixel keeping the black-ink alpha:
    # the flat fill maps to the white suit, black-line AA to the grey ramp,
    # white-edge AA back to white.
    f = panel[..., :3].astype(float)
    sat = f.max(2) - f.min(2) > 8
    for mask, dom, off, fill in ((sat & (f[..., 0] >= f[..., 2]), 0, 1, 239),
                                 (sat & (f[..., 2] > f[..., 0]), 2, 0, 240)):
        v = np.clip((f[..., dom] - f[..., off]) * 255 / fill + f[..., off], 0, 255)
        panel[..., :3][mask] = v[mask, None].round()
    # measure the '12' key bbox before erasing, to size and place the 'R'
    lab, _ = ndimage.label(panel[..., :3].max(2) < INK_BLACK, structure=np.ones((3, 3)))
    H, W = panel.shape[:2]
    boxes = [(sl[0].start, sl[0].stop, sl[1].start, sl[1].stop)
             for sl in ndimage.find_objects(lab)
             if sl[0].stop <= 0.22 * H and sl[1].stop <= 0.32 * W]
    ky0, kx0 = min(b[0] for b in boxes), min(b[2] for b in boxes)
    kh = max(b[1] for b in boxes) - ky0
    named = erase(panel, names=False)
    im = Image.fromarray(named)
    draw = ImageDraw.Draw(im)
    for size in range(80, 8, -1):   # largest size whose cap height fits the '12' bbox
        font = ImageFont.truetype(FONT, size)
        bx = draw.textbbox((0, 0), "R", font=font)
        if bx[3] - bx[1] <= kh: break
    draw.text((kx0 - bx[0], ky0 - bx[1]), "R", font=font, fill=(0, 0, 0))
    return np.array(im), erase(panel)


def save(arr, path):
    Image.fromarray(arr).save(path, "WEBP", lossless=True, quality=100, method=6)


if __name__ == "__main__":
    for d, sources in JOBS.items():
        restricted = set().union(*(s or set() for _, s in sources))
        pools = {pdf: embeds(pdf) for pdf, _ in sources}
        od = os.path.join(OUT, d)
        os.makedirs(os.path.join(od, "figures"), exist_ok=True)
        used, arrs = {}, {}
        for rf in sorted(glob.glob(f"{REPO}/{d}/Axis/*.webp")):
            key = os.path.basename(rf)[:-5]
            if d == "4-way" and key == "R": continue   # no AXIS source card; derived below
            srcs = [pdf for pdf, spec in sources
                    if (key in spec if spec else key not in restricted)]
            cands = [c for pdf in srcs for c in pools[pdf]]
            i, mse, mse2 = match(rf, cands)
            f, arr = cands[i]
            if f in used:
                print(f"  !! {d}/{key}: embed already claimed by {used[f]}")
            used[f] = key
            arr, nbadges = remove_badges(arr)
            if nbadges: print(f"  {d}/{key}: removed {nbadges} badge(s)")
            arrs[key] = arr
            save(arr, f"{od}/{key}.webp")
            save(erase(arr), f"{od}/figures/{key}.webp")
            flag = "" if mse < 600 and mse2 > 3 * mse else f"  CHECK mse={mse:.0f} next={mse2:.0f}"
            print(f"  {d}/{key}: {arr.shape[1]}x{arr.shape[0]} mse={mse:.0f}{flag}")
        if d == "4-way":
            named, fig = derive_R(arrs["12"])
            save(named, f"{od}/R.webp")
            save(fig, f"{od}/figures/R.webp")
            print(f"  {d}/R: {named.shape[1]}x{named.shape[0]} derived from block 12")
        print(f"{d}: {len(used) + (d == '4-way')} cards")
    print("staged ->", OUT)
