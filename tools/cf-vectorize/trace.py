"""Trace a CF diagram webp (black line art on white) to a faithful SVG.

Upscale-then-threshold: Lanczos interpolation of the anti-aliased ramps puts the
128-threshold contour at the sub-native-pixel ink boundary, so potrace's curves
land where the original art's edges are, not on a pixel staircase.
"""
from PIL import Image
from scipy import ndimage
import numpy as np
import potrace

TARGET = 2400  # upscaled min-dimension before thresholding
EDGE = 3       # px: border crumbs hug the stripped edge
CRUMB = 6      # px area: far below any glyph or stroke


# The border strip leaves residue hugging the cell edge: 1px line-crumbs, sparse
# dark remnants of the border's anti-alias halo, and a near-full-extent faint line
# in the outermost pixel. Traced, these become floating dots and edge hairlines.
# Real art is safe on both counts: it extends inward past the edge band (so its
# components are never contained in it — block dividers reach the cell edge and
# survive), and its core ink is darker than the 128 threshold.
def descrumb(im):
    g = np.asarray(im).copy()
    ink = g < 128
    H, W = ink.shape
    lbl, n = ndimage.label(ink, structure=np.ones((3, 3)))
    for i in range(1, n + 1):
        ys, xs = np.where(lbl == i)
        near = ys.min() < EDGE or xs.min() < EDGE or ys.max() >= H - EDGE or xs.max() >= W - EDGE
        contained = ys.max() < EDGE or xs.max() < EDGE or ys.min() >= H - EDGE or xs.min() >= W - EDGE
        if contained or (near and len(ys) <= CRUMB):
            g[ys, xs] = 255
    # Whiten the faint halo in the outer 2px ring: Lanczos overshoot at the upscale
    # would otherwise pull it under the threshold and trace it as a hairline.
    band = np.zeros((H, W), bool)
    band[:2] = band[-2:] = band[:, :2] = band[:, -2:] = True
    g[band & (g >= 128)] = 255
    return Image.fromarray(g)


def trace(src, dst):
    im = descrumb(Image.open(src).convert('L'))
    w, h = im.size
    scale = max(2, round(TARGET / min(w, h)))
    big = im.resize((w * scale, h * scale), Image.LANCZOS)
    # potracer thresholds ndarray input itself (True=light, inverted internally)
    path = potrace.Bitmap(np.asarray(big)).trace(
        turdsize=int((scale / 2) ** 2),  # kill specks smaller than ~half a native pixel
        alphamax=1.0, opticurve=1, opttolerance=0.2,
    )

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

    # Intrinsic size: min side 1100 (FS-set scale). CSS max-width/max-height never
    # upscales an img past its intrinsic dims, so small-native attrs would shrink
    # the card; for a vector the attr is free — display fills the box, stays crisp.
    iw, ih = (round(v * 1100 / min(w, h)) for v in (w, h))
    # No background rect — the art floats transparent; the app's CSS keeps the
    # global white img background off the invert-set diagrams.
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{iw}" height="{ih}" '
           f'viewBox="0 0 {w * scale} {h * scale}">'
           f'<path fill="#000" fill-rule="evenodd" d="{"".join(parts)}"/></svg>')
    with open(dst, 'w') as f:
        f.write(svg)
    return scale


if __name__ == '__main__':
    import sys, time
    t0 = time.time()
    s = trace(sys.argv[1], sys.argv[2])
    print(f'{sys.argv[1]} -> {sys.argv[2]}  scale x{s}  {time.time() - t0:.1f}s')
