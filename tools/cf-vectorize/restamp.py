"""Re-stamp the CF 4-way USPA canopies with the CF 2-way canopy glyph.

The CF4 cells trace from 174-343px rasters whose ~1-3px strokes wobble badly
once vectorised; the CF2 cells (~430px) trace clean. Every canopy in the CF4
set is therefore replaced by a donor glyph cut from CF2 E: the top canopy's
arc/slider/lines (only its tip is fused with the filled arc below) completed
with the bottom canopy's free tip, translation-grafted along the matching
suspension lines. Formation geometry comes from the batch.py-traced CF4 SVGs:
each canopy's pose is template-fitted there, all canopies share one consensus
scale, apexes are re-anchored on the old art's line-fit tips, and the poses
constraint-solve against the formation's attachment graph (per panel on
blocks): a tip docks at exactly one of three attachment points of its target
(either arc corner or the slider-bump top), joint docks hold both corners,
abutting corners coincide — so canopies touch at the attachment points and
never overlap. The old touch topology is enforced by a weld pass; there is
deliberately NO separation-channel pass — extra old components are trace
damage whose breaks a channel would carve into the clean stamps.

Blocks additionally restore the canopy coloring (clear / full black / half
black / two stripes — the pool marks jumper groupings): each canopy's pattern
classifies from the old art's erosion cores and composes from the authentic
CF2 fill (E's bottom canopy is the donor glyph's filled twin, exactly aligned
by the same line fits; CF4 fills paint solider — only the band window stays
white). Block cards compose preserve-and-replace: the old trace survives
verbatim (INTER arrows, marks, dividers, text), only canopy components are
erased and re-stamped. Randoms rebuild from parts (text + dividers + stamps).

Run AFTER batch.py (it fits against the batch-traced set): regenerating the
CF4 USPA assets from the repo is `python3 batch.py && python3 restamp.py`.
Running batch.py alone REGRESSES the CF4 set to the wobbly native traces.
"""
import io, json, sys
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np
from scipy import ndimage
from scipy.signal import fftconvolve
import cairosvg, potrace

HERE = Path(__file__).resolve().parent
NATIVE = HERE / 'native/4-way-cf'
ASSETS = HERE.parent.parent / 'assets/diagrams/4-way-cf/USPA'
CF2 = HERE.parent.parent / 'assets/diagrams/2-way-cf/USPA/figures/E.svg'

# CF4's source glyph is squatter than CF2's: stack spacing / arc width
# measures 0.85-0.88 in the old traces vs the donor's 0.98
SQUASH = 0.87


def render(path, w, h):
    png = cairosvg.svg2png(url=str(path), output_width=w, output_height=h, background_color='white')
    return np.asarray(Image.open(io.BytesIO(png)).convert('L')).astype(np.uint8)


def runs_of(row):
    xs = np.where(row)[0]
    if len(xs) == 0:
        return []
    runs, start = [], xs[0]
    for p, q in zip(xs, xs[1:]):
        if q != p + 1:
            runs.append((start, p)); start = q
    runs.append((start, xs[-1]))
    return runs


def build_donor():
    """donor master from CF2 E at 16x: top canopy body + bottom canopy's free tip"""
    R = 16
    png = cairosvg.svg2png(url=str(CF2), output_width=430 * R, background_color='white')
    E = np.asarray(Image.open(io.BytesIO(png)).convert('L')).astype(np.uint8).copy()
    ink = E < 128

    def fit_pair(y0, y1):
        Ls, Rs, ys, w = [], [], [], []
        for y in range(y0, y1):
            r = runs_of(ink[y])
            if len(r) != 2 or r[0][1] - r[0][0] > 60 or r[1][1] - r[1][0] > 60:
                continue
            Ls.append((r[0][0] + r[0][1]) / 2); Rs.append((r[1][0] + r[1][1]) / 2)
            w.append(r[0][1] - r[0][0] + 1); ys.append(y)
        aL, bL = np.polyfit(ys, Ls, 1)
        aR, bR = np.polyfit(ys, Rs, 1)
        return aL, bL, aR, bR, float(np.median(w))

    top = fit_pair(2400, 3530)   # top canopy's clean line zone
    bot = fit_pair(3930, 5100)   # bottom canopy's clean line zone
    # translation mapping the bottom lines onto the top lines (same glyph:
    # slopes match to ~1e-4), least squares over both intercepts
    A = np.array([[bot[0], -1], [bot[2], -1]])
    rhs = np.array([top[1] - bot[1], top[3] - bot[3]])
    dy, dx = np.linalg.solve(A, rhs)
    SEAM = 3536                  # first row of the top tip's fusion with the filled arc
    src0 = int(round(SEAM + dy))
    bot_apex = int(np.where(ink[4500:].any(axis=1))[0].max() + 4500)
    n = bot_apex - src0 + 20
    patch = np.roll(E[src0:src0 + n, :], -int(round(dx)), axis=1)
    E[SEAM:SEAM + n, :] = patch
    E[SEAM + n:, :] = 255

    ink = E < 128
    rows = np.where(ink.any(axis=1))[0]
    t = rows.min()
    cols = np.where(ink[t:t + 500].any(axis=0))[0]
    x0, x1 = cols.min(), cols.max()
    donor = E[t - 20:rows.max() + 21, x0 - 20:x1 + 21]

    dk = donor < 128
    apy = int(np.where(dk.any(axis=1))[0].max())
    meta = {'arc_w': int(x1 - x0 + 1), 'arc_cx': float((x1 - x0) / 2 + 20),
            'apex': [float(np.where(dk[apy - 3])[0].mean()), float(apy)],
            'slopeL': top[0], 'slopeR': top[2], 'runw': top[4]}
    return donor, meta


DONOR, META = build_donor()

_cache = {}
def donor_at(s, theta=0.0):
    k = (round(s, 4), round(theta, 1))
    if k not in _cache:
        im = Image.fromarray(DONOR)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s * SQUASH))), Image.LANCZOS)
        if theta:
            im = im.rotate(theta, Image.BICUBIC, expand=True, fillcolor=255)
        g = np.asarray(im).astype(np.uint8)
        if len(_cache) > 40:
            _cache.clear()
        _cache[k] = (g, g < 128)
    return _cache[k]


# attachment geometry: a tip docks onto one of exactly three points of the
# target canopy — either arc corner or the slider-bump top at center
_dk = DONOR < 128
_DH, _DW = DONOR.shape
_tz = _dk[:int(_DH * 0.35)]
_cols = np.where(_tz.any(axis=0))[0]
ARC_X0, ARC_X1 = int(_cols.min()), int(_cols.max())
CORNER_L = (float(ARC_X0 + 2), float(np.where(_tz[:, ARC_X0:ARC_X0 + 8].any(axis=1))[0].mean()))
CORNER_R = (float(ARC_X1 - 2), float(np.where(_tz[:, ARC_X1 - 7:ARC_X1 + 1].any(axis=1))[0].mean()))
_c0, _c1 = int(META['arc_cx'] - 2 * META['runw']), int(META['arc_cx'] + 2 * META['runw'])
CENTER_T = (float(META['arc_cx']), float(np.where(_dk[:, _c0:_c1].any(axis=1))[0].min()))
ATTACH = {'L': CORNER_L, 'C': CENTER_T, 'R': CORNER_R}
PROF = np.full(_DW, np.nan)  # arc top profile: topmost ink row per donor column
for _x in range(_DW):
    _ys = np.where(_dk[:, _x])[0]
    if len(_ys):
        PROF[_x] = _ys[0]


def to_canvas(p, u, v):
    x, y, s, th = p[0], p[1], p[2], p[3]
    cx, cy = _DW / 2, _DH / 2
    dx, dy = (u - cx) * s, (v - cy) * s * SQUASH
    t = np.deg2rad(-th)
    return x + dx * np.cos(t) - dy * np.sin(t), y + dx * np.sin(t) + dy * np.cos(t)


def to_donor(p, X, Y):
    x, y, s, th = p[0], p[1], p[2], p[3]
    cx, cy = _DW / 2, _DH / 2
    t = np.deg2rad(th)
    rx = (X - x) * np.cos(t) - (Y - y) * np.sin(t)
    ry = (X - x) * np.sin(t) + (Y - y) * np.cos(t)
    return rx / s + cx, ry / (s * SQUASH) + cy


# canopy fills (blocks): the block pools colour canopies to mark the
# groupings — clear, full black, half black, or two stripes — all painted
# inside the dome (the arc-band ring and the corner pockets, v<=360; below
# is the V interior)
INTERIOR = ndimage.binary_fill_holes(_dk) & ~_dk
DOME = INTERIOR.copy()
DOME[360:] = False
RING_C = 170  # ring (arc-band cell) centre row in donor px
# ownership zone: the filled glyph silhouette's top — fills overlap the arc
# stroke itself at off-centre columns, so strict interior misses them. The
# top rows open to the full arc span: pose error can map a fill slightly
# above the silhouette (only the bump lives there)
OWN_ZONE = ndimage.binary_fill_holes(_dk)
OWN_ZONE[430:] = False
OWN_ZONE[:60, ARC_X0 + 100:ARC_X1 - 100] = True
D = 4  # fill-sampling grid stride in donor px
DOME_G = DOME[::D, ::D]
_gh, _gw = DOME_G.shape


def disk(r):
    yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    return (yy * yy + xx * xx <= r * r)


def build_fill_auth():
    """authentic full-black fill mask in donor space: CF2 E's bottom canopy is
    the filled twin of the donor glyph — build_donor's line fits give the exact
    top<->bottom translation, so its ink sampled over the donor interior is the
    true fill, wobble-free"""
    R = 16
    png = cairosvg.svg2png(url=str(CF2), output_width=430 * R, background_color='white')
    E = np.asarray(Image.open(io.BytesIO(png)).convert('L'))
    ink = E < 128
    def fit_pair(y0, y1):
        Ls, Rs, ys = [], [], []
        for y in range(y0, y1):
            r = runs_of(ink[y])
            if len(r) != 2 or r[0][1] - r[0][0] > 60 or r[1][1] - r[1][0] > 60:
                continue
            Ls.append((r[0][0] + r[0][1]) / 2); Rs.append((r[1][0] + r[1][1]) / 2)
            ys.append(y)
        aL, bL = np.polyfit(ys, Ls, 1)
        aR, bR = np.polyfit(ys, Rs, 1)
        return aL, bL, aR, bR
    top = fit_pair(2400, 3530)
    bot = fit_pair(3930, 5100)
    A = np.array([[bot[0], -1], [bot[2], -1]])
    rhs = np.array([top[1] - bot[1], top[3] - bot[3]])
    dy, dx = np.linalg.solve(A, rhs)
    rows = np.where(ink.any(axis=1))[0]
    t = rows.min()
    cols = np.where(ink[t:t + 500].any(axis=0))[0]
    x0 = cols.min()
    vv, uu = np.mgrid[0:_DH, 0:_DW]
    Yb = np.rint(vv + (t - 20) + dy).astype(int)
    Xb = np.rint(uu + (x0 - 20) + dx).astype(int)
    ok = (Yb >= 0) & (Yb < ink.shape[0]) & (Xb >= 0) & (Xb < ink.shape[1])
    F = np.zeros((_DH, _DW), bool)
    F[ok] = ink[Yb[ok], Xb[ok]]
    F &= INTERIOR
    F[420:] = False  # nothing fills below the corner pockets
    return F


# CF4's fills are solider than CF2's: the slider-detail whites and the
# under-bump zone all paint black; only the band window stays white. So the
# full fill = the whole dome minus the window, with the window's authentic
# shape taken from the CF2 sample (the big interior cell's unfilled top).
_F_RAW = build_fill_auth()
_lab_int, _n_int = ndimage.label(INTERIOR, np.ones((3, 3)))
_c2 = max(range(1, _n_int + 1), key=lambda c: (_lab_int == c).sum())
WINDOW = (_lab_int == _c2) & ~_F_RAW
WINDOW[420:] = False
FILL_AUTH = INTERIOR & ~WINDOW
FILL_AUTH[420:] = False
# canonical stripe geometry, donor px from the arc centre: the source art's
# stripes vary canopy to canopy (and lean wider on the right), so every
# striped canopy paints this symmetric pair — the medians over all 24
# striped canopies' measured spans (inner |u| 125-153, outer 396-409)
STRIPE_IN, STRIPE_OUT = 138, 402


def fit_card(key, n):
    w, h = Image.open(NATIVE / f'{key}.webp').size
    scale = max(2, round(2400 / min(w, h)))
    W, H = w * scale, h * scale
    old = render(ASSETS / f'{key}.svg', W, H)
    ink = old < 128
    # scale ladder: canopy arc width varies per native class (~40..~76 native px)
    cands = []
    for arcpx in (38, 44, 50, 57, 64, 72, 80):
        s = arcpx * scale / META['arc_w']
        g, m = donor_at(s)
        corr = fftconvolve(ink.astype(np.float32), m[::-1, ::-1].astype(np.float32), mode='same') / m.sum()
        cands.append((corr, s))
    best = np.maximum.reduce([c[0] for c in cands])
    which = np.argmax(np.stack([c[0] for c in cands]), axis=0)
    poses, sup = [], np.zeros_like(best, bool)
    for _ in range(n):
        masked = np.where(sup, -1, best)
        y, x = np.unravel_index(np.argmax(masked), masked.shape)
        s_pk = cands[which[y, x]][1]
        poses.append([float(x), float(y), s_pk, 0.0, 0.0])
        radius = int(META['arc_w'] * s_pk * 0.5)
        yy, xx = np.ogrid[:best.shape[0], :best.shape[1]]
        sup |= (yy - y) ** 2 + (xx - x) ** 2 < radius ** 2
    return poses, ink, scale, (w, h)


def refine(poses, ink, lock_scale=False):
    out = []
    moves = [(1, 0, 0, 0), (-1, 0, 0, 0), (0, 1, 0, 0), (0, -1, 0, 0)]
    if not lock_scale:
        moves += [(0, 0, 0.01, 0), (0, 0, -0.01, 0)]
    moves += [(0, 0, 0, 1.0), (0, 0, 0, -1.0)]  # keep the v1 probe order: s before theta
    for x, y, s, th, _ in poses:
        def iou(px, py, ps, pt):
            g, m = donor_at(ps, pt)
            mh, mw = m.shape
            y0, x0 = int(round(py - mh / 2)), int(round(px - mw / 2))
            if y0 < 0 or x0 < 0 or y0 + mh > ink.shape[0] or x0 + mw > ink.shape[1]:
                return 0
            win = ink[y0:y0 + mh, x0:x0 + mw]
            inter = (win & m).sum()
            return inter / (m.sum() + win.sum() - inter)
        cur = iou(x, y, s, th)
        step = 8
        while step >= 1:
            improved = False
            for mx, my, ds, dt in moves:
                dx, dy = mx * step, my * step
                v = iou(x + dx, y + dy, s + ds, th + dt)
                if v > cur:
                    x, y, s, th, cur = x + dx, y + dy, s + ds, th + dt, v
                    improved = True
            if not improved:
                step //= 2
        out.append([x, y, s, th, cur])
    return out


def apex_of(p):
    x, y, s, th, _ = p
    cx, cy = DONOR.shape[1] / 2, DONOR.shape[0] / 2
    ax, ay = (META['apex'][0] - cx) * s, (META['apex'][1] - cy) * s * SQUASH
    t = np.deg2rad(-th)
    return x + ax * np.cos(t) - ay * np.sin(t), y + ax * np.sin(t) + ay * np.cos(t)


def measure_tips(poses, ink, labo):
    """the OLD canopy's apex per pose: line-fit the old V inside the pose
    window, intersect -> old tip. Docked = the old tip's component continues
    past it (touching canopies merged in the old trace). [(Xt, Yt, docked) |
    None] per pose."""
    apx, apy = META['apex']
    bL = apx - META['slopeL'] * apy
    bR = apx - META['slopeR'] * apy
    tips = []
    for p in poses:
        x, y, s, th, _ = p
        g, _m = donor_at(s, th)
        mh, mw = g.shape
        ox, oy = x - mw / 2, y - mh / 2
        ax, ay = apex_of(p)
        stroke = META['runw'] * s
        pts = {'L': [], 'R': []}
        for Y in range(int(oy + 0.45 * mh), int(ay - 2 * stroke)):
            if not (0 <= Y < ink.shape[0]):
                continue
            v = (Y - oy) / (s * SQUASH)
            for side, sl, b in (('L', META['slopeL'], bL), ('R', META['slopeR'], bR)):
                cx = (sl * v + b) * s + ox
                lo, hi = int(cx - 3 * stroke), int(cx + 3 * stroke + 1)
                xs = np.where(ink[Y, max(0, lo):hi])[0]
                if len(xs):
                    pts[side].append((Y, max(0, lo) + xs.mean()))
        if len(pts['L']) < 12 or len(pts['R']) < 12:
            tips.append(None); continue
        aLo, bLo = np.polyfit(*zip(*pts['L']), 1)
        aRo, bRo = np.polyfit(*zip(*pts['R']), 1)
        if abs(aLo - aRo) < 0.2:
            tips.append(None); continue
        Yt = (bRo - bLo) / (aLo - aRo)
        Xt = aLo * Yt + bLo
        if np.hypot(Xt - ax, Yt - ay) > 7 * stroke:
            tips.append(None); continue
        tip = labo[int(Yt - 1.2 * stroke):int(Yt - 0.1 * stroke), int(Xt - stroke):int(Xt + stroke + 1)]
        tip = tip[tip > 0]
        past = labo[int(Yt + 0.2 * stroke):int(Yt + 1.4 * stroke), int(Xt - stroke):int(Xt + stroke + 1)]
        past = past[past > 0]
        docked = len(tip) > 0 and len(past) > 3 and np.intersect1d(tip, past).size > 0
        tips.append((Xt, Yt, docked))
    return tips


def dock_cons(poses, tips):
    """tip-onto-attachment constraints: (i, Pi_donor, j, Qj_donor, sink_strokes)"""
    cons = []
    for i, t in enumerate(tips):
        if t is None:
            continue
        Xt, Yt, docked = t
        for j, q in enumerate(poses):
            if j == i:
                continue
            u, v = to_donor(q, Xt, Yt)
            if not (ARC_X0 - 35 <= u <= ARC_X1 + 35):  # joint docks sit ~0.5-0.8 stroke past the corner
                continue
            # clamp the profile lookup into the arc so corner docks (u just
            # past the arc end) read the corner height instead of nan
            pr = PROF[int(np.clip(u, ARC_X0 + 2, ARC_X1 - 2))]
            dvert = (v - pr) * SQUASH / META['runw']  # strokes
            if not (-3 < dvert < 4.5):
                continue
            r = (u - ARC_X0) / (ARC_X1 - ARC_X0)
            cls = 'L' if r < 0.25 else ('R' if r > 0.75 else 'C')
            # a joint dock (tip into the point where two canopies meet)
            # legitimately matches both targets: keep every constraint
            cons.append((i, tuple(META['apex']), j, ATTACH[cls], 0.4 if docked else 0.0))
    return cons


def snap_formation(poses, tips, labo):
    """least-squares translations snapping each tip onto its target's nearest
    attachment point and abutting corners onto each other"""
    cons = dock_cons(poses, tips)
    # corner abutments: corners close AND old ink at both corners shares a component
    for i in range(len(poses)):
        for j in range(len(poses)):
            if i == j:
                continue
            si = META['runw'] * poses[i][2]
            Xa, Ya = to_canvas(poses[i], *CORNER_R)
            Xb, Yb = to_canvas(poses[j], *CORNER_L)
            if np.hypot(Xa - Xb, Ya - Yb) > 5 * si:
                continue
            w = int(1.5 * si)
            la = labo[int(Ya) - w:int(Ya) + w + 1, int(Xa) - w:int(Xa) + w + 1]
            lb = labo[int(Yb) - w:int(Yb) + w + 1, int(Xb) - w:int(Xb) + w + 1]
            la, lb = la[la > 0], lb[lb > 0]
            if len(la) and len(lb) and np.intersect1d(la, lb).size > 0:
                cons.append((i, CORNER_R, j, CORNER_L, 0.0))
    if not cons:
        return poses
    n = len(poses)
    LAM = 0.03  # stay-put anchor weight vs constraint weight 1
    rowsx, bx, rowsy, by = [], [], [], []
    for i, P, j, Q, sink in cons:
        Px, Py = to_canvas(poses[i], *P)
        Qx, Qy = to_canvas(poses[j], *Q)
        sinkpx = sink * META['runw'] * poses[j][2]
        rx = np.zeros(n); rx[i], rx[j] = 1, -1
        rowsx.append(rx); bx.append(Qx - Px)
        ry = np.zeros(n); ry[i], ry[j] = 1, -1
        rowsy.append(ry); by.append(Qy + sinkpx - Py)
    for i in range(n):
        r = np.zeros(n); r[i] = LAM
        rowsx.append(r); bx.append(0)
        rowsy.append(r); by.append(0)
    tx = np.linalg.lstsq(np.array(rowsx), np.array(bx), rcond=None)[0]
    ty = np.linalg.lstsq(np.array(rowsy), np.array(by), rcond=None)[0]
    for i, p in enumerate(poses):
        p[0] += tx[i]; p[1] += ty[i]
    return poses


def dock_scale(fitted, raws, s_med):
    """blocks: filled domes drag the IoU fit — and with it the median
    consensus — a rung low (block 5: 7 of 12 poses, leaving every joint
    outside the dock window). Arbitrate among the fitted scale values by
    dock success after pinning; the median wins ties, so cards it already
    served keep their scale."""
    def hits(s):
        n = 0
        for grp, tips in fitted:
            test = [[p[0], p[1], s, p[3], p[4]] for p in grp]
            for p, t in zip(test, tips):
                if t:
                    ax, ay = apex_of(p)
                    p[0] += t[0] - ax
                    p[1] += t[1] - ay
            n += len(dock_cons(test, tips))
        return n
    return max(sorted(set(raws)), key=lambda c: (hits(c), -abs(c - s_med)))


def old_figure_ink(key, scale, dims):
    w, h = dims
    W, H = w * scale, h * scale
    a = render(ASSETS / f'figures/{key}.svg', W, H) < 128
    a[np.where(a.sum(axis=1) > 0.85 * W)[0]] = False  # dividers out
    return a


def _sample(p, img):
    """img at the donor grid points under pose p"""
    x, y, s, th = p[0], p[1], p[2], p[3]
    cx, cy = _DW / 2, _DH / 2
    jj, ii = np.meshgrid(np.arange(_gw), np.arange(_gh))
    u = jj * D
    v = ii * D
    t = np.deg2rad(-th)
    dx, dy = (u - cx) * s, (v - cy) * s * SQUASH
    X = np.rint(x + dx * np.cos(t) - dy * np.sin(t)).astype(int)
    Y = np.rint(y + dx * np.sin(t) + dy * np.cos(t)).astype(int)
    okv = (Y >= 0) & (Y < img.shape[0]) & (X >= 0) & (X < img.shape[1])
    F = np.zeros((_gh, _gw), bool)
    F[okv] = img[Y[okv], X[okv]]
    return F


def assign_blobs(poses, nat, scale):
    """label the native erosion cores (strokes gone, fills survive) and give
    each blob to the pose whose zone holds its centroid most centrally —
    overlapping stairstep domes otherwise borrow their neighbour's fill"""
    er = ndimage.binary_erosion(nat, np.ones((5, 5)))
    lab, n = ndimage.label(er, np.ones((3, 3)))
    owned = {i: [] for i in range(len(poses))}
    for c in range(1, n + 1):
        m = lab == c
        if m.sum() < 20:  # junction residue; real cores (stripes included) are bigger
            continue
        ys, xs = np.where(m)
        Ys, Xs = ys * scale, xs * scale
        best, bestkey = None, (0, 0)
        for i, p in enumerate(poses):
            # the owner's zone contains the whole blob, an overlapping
            # stairstep neighbour's only part of it; ties (both zones hold
            # it fully) break toward the pose seeing it nearer its centre
            hits = 0
            uc = []
            for Y, X in zip(Ys[::2], Xs[::2]):
                u, v = to_donor(p, X, Y)
                iu, iv = int(u), int(v)
                uc.append(u)
                if 0 <= iu < _DW and 0 <= iv < _DH and OWN_ZONE[iv, iu]:
                    hits += 1
            k = (hits, -abs(float(np.mean(uc)) - META['arc_cx']))
            if k > bestkey:
                bestkey, best = k, i
        if best is not None and bestkey[0] > 0.5 * len(Ys[::2]):
            owned[best].append(m)
            continue
        # orphan: a pose fitted a few px off can miss its own ring entirely —
        # assign by predicted ring position instead
        Yc, Xc = ys.mean() * scale, xs.mean() * scale
        best, bestd = None, 250.0
        for i, p in enumerate(poses):
            pred_y = Yc + (_DH / 2 - RING_C) * p[2] * SQUASH
            d = abs(p[1] - pred_y) + 0.5 * abs(p[0] - Xc)
            if d < bestd:
                bestd, best = d, i
        if best is not None:
            owned[best].append(m)
    return owned


def fill_variant(p, blobs, ink, scale):
    """classify this canopy's fill pattern from its owned blobs and compose
    it from the authentic CF2 fill mask. Returns (variant, kind) or (None,
    'clear')."""
    if not blobs:
        return None, 'clear'
    # y-align the measuring pose on the blobs' ring: the fill belongs to the
    # stamp's ring even when the pose fitted a few px off vertically
    dys = []
    for m in blobs:
        ys, _xs = np.where(m)
        dys.append(ys.mean() * scale + (_DH / 2 - RING_C) * p[2] * SQUASH - p[1])
    dy = float(np.clip(np.median(dys), -160, 160))
    pa = [p[0], p[1] + dy, p[2], p[3], p[4]]
    # blob extents in donor u
    W = ARC_X1 - ARC_X0
    margin = 2.5 * scale / pa[2]  # the native 5x5 erosion's bite, donor px
    spans = []
    for m in blobs:
        ys, xs = np.where(m)
        us = [to_donor(pa, X * scale, Y * scale)[0] for Y, X in zip(ys[::4], xs[::4])]
        spans.append((min(us) - margin, max(us) + margin))
    spans.sort()
    widths = [(b - a) / W for a, b in spans]
    if len(spans) == 1 and widths[0] >= 0.7:
        kind = 'full'
        fill = FILL_AUTH
    elif len(spans) == 1 and 0.2 <= widths[0] <= 0.62:
        a, b = spans[0]
        side_right = (a + b) / 2 > META['arc_cx']
        kind = 'half-R' if side_right else 'half-L'
        side = (np.arange(_DW) >= a) if side_right else (np.arange(_DW) <= b)
        fill = FILL_AUTH & side[None, :]
        # the source half-fills run over their side of the band window when
        # the old art draws it dark there
        wmask = WINDOW & side[None, :]
        wg = wmask[::D, ::D]
        if wg.sum() and (_sample(pa, ink) & wg).sum() > 0.4 * wg.sum():
            fill = fill | wmask
    elif len(spans) == 2 and max(widths) <= 0.32:
        # the measured spans only classify; paint the canonical pair
        kind = 'stripes'
        cols = np.zeros(_DW, bool)
        for a, b in ((-STRIPE_OUT, -STRIPE_IN), (STRIPE_IN, STRIPE_OUT)):
            cols[int(META['arc_cx'] + a):int(META['arc_cx'] + b) + 1] = True
        fill = FILL_AUTH & cols[None, :]
    else:
        kind = f'odd({len(spans)}:{",".join(f"{w:.2f}" for w in widths)})'
        # fallback: union span as a full-side cut of the authentic mask
        a = min(s[0] for s in spans); b = max(s[1] for s in spans)
        cols = np.zeros(_DW, bool)
        cols[int(max(0, a)):int(min(_DW, b)) + 1] = True
        fill = FILL_AUTH & cols[None, :]
    var = DONOR.copy()
    var[fill] = 0
    return var, kind


def stamp_of(p, var):
    """donor_at for a per-canopy variant master (no cache)"""
    im = Image.fromarray(var)
    im = im.resize((max(1, round(im.width * p[2])), max(1, round(im.height * p[2] * SQUASH))), Image.LANCZOS)
    if p[3]:
        im = im.rotate(p[3], Image.BICUBIC, expand=True, fillcolor=255)
    return np.asarray(im).astype(np.uint8)


def compose_stamps(key, poses, stamps, scale, dims, figures, old):
    """blocks: preserve-and-replace. The old trace survives verbatim (INTER
    arrows, marks, dividers, text); canopy ink is erased and re-stamped clean.
    Canopy ink = old components mostly inside the stamp silhouettes — a fitted
    pose can sit a few px off its old glyph, so the whole component goes, not
    just the silhouette window."""
    w, h = dims
    W, H = w * scale, h * scale
    base = render(ASSETS / (f'{key}.svg' if not figures else f'figures/{key}.svg'), W, H)
    div_rows = np.where((render(ASSETS / f'figures/{key}.svg', W, H) < 128).sum(axis=1) > 0.85 * W)[0]
    canvas = base.copy()
    sil = np.zeros((H, W), bool)
    for (x, y, s, th, _), g in zip(poses, stamps):
        m = g < 128
        mh, mw = m.shape
        y0, x0 = int(round(y - mh / 2)), int(round(x - mw / 2))
        gg = m[max(0, -y0):mh - max(0, y0 + mh - H), max(0, -x0):mw - max(0, x0 + mw - W)]
        full = ndimage.binary_fill_holes(gg)
        sil[max(0, y0):y0 + mh, max(0, x0):x0 + mw] |= full
    sil = ndimage.binary_dilation(sil, disk(int(round(1.2 * META['runw'] * poses[0][2]))))
    erase = sil.copy()
    labo, no = ndimage.label(old, structure=np.ones((3, 3)))
    inside = ndimage.sum(sil, labo, index=range(1, no + 1))
    total = ndimage.sum(np.ones_like(sil), labo, index=range(1, no + 1))
    for c in range(1, no + 1):
        if inside[c - 1] >= 0.3 * total[c - 1]:
            erase |= labo == c
    canvas[erase] = 255
    for y in div_rows:  # silhouettes near a panel edge must not eat the divider
        canvas[y] = base[y]
    for (x, y, s, th, _), g in zip(poses, stamps):
        mh, mw = g.shape
        y0, x0 = int(round(y - mh / 2)), int(round(x - mw / 2))
        region = canvas[max(0, y0):y0 + mh, max(0, x0):x0 + mw]
        gg = g[max(0, -y0):mh - max(0, y0 + mh - H), max(0, -x0):mw - max(0, x0 + mw - W)]
        np.minimum(region, gg, out=region)
    return canvas


def compose(key, poses, scale, dims, figures):
    w, h = dims
    W, H = w * scale, h * scale
    old_named = render(ASSETS / f'{key}.svg', W, H)
    old_fig = render(ASSETS / f'figures/{key}.svg', W, H)
    canvas = np.full((H, W), 255, np.uint8)
    div_rows = np.where((old_fig < 128).sum(axis=1) > 0.85 * W)[0]
    if not figures:
        # text = exactly what the figures erase removed, kept verbatim
        gm = np.abs(old_named.astype(int) - old_fig.astype(int)) > 40
        gm = np.array(Image.fromarray(gm.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))) > 0
        canvas[gm] = old_named[gm]
    for y in div_rows:
        canvas[y] = np.minimum(canvas[y], old_fig[y])
    for x, y, s, th, _ in poses:
        g, _m = donor_at(s, th)
        mh, mw = g.shape
        y0, x0 = int(round(y - mh / 2)), int(round(x - mw / 2))
        region = canvas[max(0, y0):y0 + mh, max(0, x0):x0 + mw]
        gg = g[max(0, -y0):mh - max(0, y0 + mh - H), max(0, -x0):mw - max(0, x0 + mw - W)]
        np.minimum(region, gg, out=region)
    return canvas


def weld(canvas, old, scale):
    """bridge stamp pairs the old art drew touching: new comps voting for the
    same old comp get a stroke-wide bridge at their nearest-pixel pair"""
    new = canvas < 128
    new[np.where(new.sum(axis=1) > 0.85 * canvas.shape[1])[0]] = False
    so = np.ones((3, 3), bool)
    labo, _no = ndimage.label(old, structure=so)
    labn, nn = ndimage.label(new, structure=so)
    stroke = META['runw'] * 0.30 * scale / 9
    groups = {}
    for c in range(1, nn + 1):
        m = labn == c
        if m.sum() < 60 * (scale / 4) ** 2:
            continue
        votes = labo[m & old] if (m & old).any() else labo[m]
        votes = votes[votes > 0]
        if len(votes):
            groups.setdefault(np.bincount(votes).argmax(), []).append(c)
    for oc, members in groups.items():
        while len(members) > 1:
            bestpair, bestd, bestpts = None, 1e9, None
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    mi = np.argwhere(labn == members[i])[::max(1, (labn == members[i]).sum() // 800)]
                    mj = np.argwhere(labn == members[j])[::max(1, (labn == members[j]).sum() // 800)]
                    d2 = ((mi[:, None, :] - mj[None, :, :]) ** 2).sum(-1)
                    k = np.unravel_index(np.argmin(d2), d2.shape)
                    d = np.sqrt(d2[k])
                    if d < bestd:
                        bestd, bestpair, bestpts = d, (i, j), (mi[k[0]], mj[k[1]])
            if bestd > 14 * stroke:
                break
            p1, p2 = bestpts
            half = max(2, int(round(stroke / 2)))
            for t in np.linspace(0, 1, (int(bestd) + 2) * 2):
                cy = int(round(p1[0] + (p2[0] - p1[0]) * t))
                cx = int(round(p1[1] + (p2[1] - p1[1]) * t))
                canvas[max(0, cy - half):cy + half + 1, max(0, cx - half):cx + half + 1] = 0
            labn[labn == members[bestpair[1]]] = members[bestpair[0]]
            members.pop(bestpair[1])


def emit(canvas, scale, dims, dst):
    w, h = dims
    path = potrace.Bitmap(canvas).trace(
        turdsize=int((scale / 2) ** 2), alphamax=1.0, opticurve=1, opttolerance=0.2)
    fmt = lambda v: f'{v:.1f}'.rstrip('0').rstrip('.')
    parts = []
    for curve in path:
        s = curve.start_point
        parts.append(f'M{fmt(s.x)} {fmt(s.y)}')
        for seg in curve.segments:
            if seg.is_corner:
                c, e = seg.c, seg.end_point
                parts.append(f'L{fmt(c.x)} {fmt(c.y)}L{fmt(e.x)} {fmt(e.y)}')
            else:
                a, b, e = seg.c1, seg.c2, seg.end_point
                parts.append(f'C{fmt(a.x)} {fmt(a.y)} {fmt(b.x)} {fmt(b.y)} {fmt(e.x)} {fmt(e.y)}')
        parts.append('Z')
    iw, ih = (round(v * 1100 / min(w, h)) for v in (w, h))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{iw}" height="{ih}" '
           f'viewBox="0 0 {w * scale} {h * scale}">'
           f'<path fill="#000" fill-rule="evenodd" d="{"".join(parts)}"/></svg>')
    Path(dst).write_text(svg)


def run(key, out=ASSETS):
    blocks = key.isdigit()
    poses, ink, scale, dims = fit_card(key, 12 if blocks else 4)
    poses = refine(poses, ink)
    old = old_figure_ink(key, scale, dims)
    labo, _ = ndimage.label(old, structure=np.ones((3, 3)))
    # all canopies are one size in the source art: a consensus scale beats
    # per-canopy fits, whose IoU basins skew on abutting pairs and filled domes
    raws = [p[2] for p in poses]
    s = float(np.median(raws))
    for p in poses:
        p[2] = s
    if blocks:
        # the dock solve runs per panel; panel bands from the divider rows
        W = dims[0] * scale
        a = render(ASSETS / f'figures/{key}.svg', W, dims[1] * scale) < 128
        div_rows = np.where(a.sum(axis=1) > 0.85 * W)[0]
        grp_div = np.split(div_rows, np.where(np.diff(div_rows) > 5)[0] + 1) if len(div_rows) else []
        bounds = [0] + [int(g.mean()) for g in grp_div] + [dims[1] * scale]
        panels = {}
        for p in poses:
            for b in range(len(bounds) - 1):
                if bounds[b] <= p[1] < bounds[b + 1]:
                    panels.setdefault(b, []).append(p)
                    break
        groups = [panels[pid] for pid in sorted(panels)]
    else:
        groups = [poses]
    def fit_groups(groups):
        out = []
        for grp in groups:
            grp = refine(grp, ink, lock_scale=True)
            grp.sort(key=lambda p: p[1])
            out.append((grp, measure_tips(grp, ink, labo)))
        return out
    fitted = fit_groups(groups)
    if blocks:
        s2 = dock_scale(fitted, raws, s)
        if s2 != s:
            s = s2
            for grp, _ in fitted:
                for p in grp:
                    p[2] = s
            fitted = fit_groups([grp for grp, _ in fitted])
    out_poses = []
    for grp, tips in fitted:
        for p, t in zip(grp, tips):  # pin exactly; dock sink comes from the solve
            if t:
                ax, ay = apex_of(p)
                p[0] += t[0] - ax
                p[1] += t[1] - ay
        out_poses += snap_formation(grp, tips, labo)
    poses = out_poses
    if blocks:
        nat = np.asarray(Image.open(NATIVE / f'{key}.webp').convert('L')) < 128
        owned = assign_blobs(poses, nat, scale)
        stamps = []
        for i, p in enumerate(poses):
            var, _kind = fill_variant(p, owned[i], ink, scale)
            stamps.append(donor_at(p[2], p[3])[0] if var is None else stamp_of(p, var))
    for figures in (False, True):
        if blocks:
            canvas = compose_stamps(key, poses, stamps, scale, dims, figures, old)
        else:
            canvas = compose(key, poses, scale, dims, figures)
        weld(canvas, old, scale)
        sub = 'figures/' if figures else ''
        emit(canvas, scale, dims, Path(out) / f'{sub}{key}.svg')
    print(key, flush=True)


if __name__ == '__main__':
    keys = sys.argv[1:] or list('ABCDEFGHIJKLMN') + [str(n) for n in range(1, 15)]
    for k in keys:
        run(k)
