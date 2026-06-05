#!/usr/bin/env python3
"""Extract FAI ISC FS/VFS dive-pool diagrams from the 2026 CR PDF annexes.
Annex pages carry key+name baked into the art (no per-cell text layer), so cells
are cropped geometrically and the figure variant erases key+name bands (keeping
line art, dividers, rotation arrows / 360 labels) by darkness profile.

Two source modes, per page (verified with pdfimages -list + visual diff):
- pp17-25 embed the complete art as a single native raster -> extract it 1:1
  (composited over white through its smask when one is embedded), zero resample.
- pp26-28 embed only an empty grid raster; the art itself (the 4-colour VFS
  jumpers) is vector -> render at RENDER_DPI, the only resolution-bound step.
Output is lossless webp at source size."""
import re, sys, os, subprocess, glob
import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
PDF = f"{ROOT}/assets/sources/fai/fai_fs_2026.pdf"
INK = 120
RASTER_PAGES = set(range(17, 26))   # art embedded as complete native rasters
RENDER_DPI = 700                    # vector pages: ~1.57in cells -> ~1100px, the USPA vector-set standard

RAND_KEYS = list("ABCDEFGHJKLMNOPQ")          # 16, I skipped
BLOCK_KEYS = [str(i) for i in range(1, 23)]   # 1..22

def render(page):
    out = f"/tmp/faiext/_p{page}"
    if not glob.glob(out + "*.png"):
        subprocess.run(["pdftoppm", "-png", "-r", str(RENDER_DPI), "-f", str(page), "-l", str(page), PDF, out],
                       check=True, capture_output=True)
    return np.array(Image.open(glob.glob(out + "*.png")[0]).convert("RGB"))

def native(page):
    """The page's largest embedded raster, composited over white through its
    smask (paired by PDF object number) when one is embedded."""
    stem = f"/tmp/faiext/nat/p{page}"
    if not glob.glob(stem + "-*.png"):
        subprocess.run(["pdfimages", "-png", "-f", str(page), "-l", str(page), PDF, stem],
                       check=True, capture_output=True)
    lst = subprocess.run(["pdfimages", "-list", "-f", str(page), "-l", str(page), PDF],
                         check=True, capture_output=True, text=True).stdout
    rows = [{"num": int(f[1]), "type": f[2], "w": int(f[3]), "h": int(f[4]), "obj": f[10], "ppi": int(f[12])}
            for f in (ln.split() for ln in lst.splitlines()[2:])]
    main = max((r for r in rows if r["type"] == "image"), key=lambda r: r["w"] * r["h"])
    arr = np.array(Image.open(f"{stem}-{main['num']:03d}.png").convert("RGB"))
    sm = next((r for r in rows if r["type"] == "smask" and r["obj"] == main["obj"]), None)
    if sm:
        a = np.array(Image.open(f"{stem}-{sm['num']:03d}.png").convert("L")).astype(float)[..., None] / 255
        arr = (arr * a + 255 * (1 - a)).round().astype(np.uint8)
    return arr, main["ppi"]

def page_arr(page):
    """Page pixels + the border inset for that scale (clears the printed border line)."""
    arr, ppi = native(page) if page in RASTER_PAGES else (render(page), RENDER_DPI)
    return arr, round(ppi / 72 * 1.6)

def runmax0(B):
    """Per-column longest vertical run of True (cumulative-run trick, vectorized)."""
    c = np.zeros(B.shape, np.int32); c[0] = B[0]
    for i in range(1, B.shape[0]): c[i] = (c[i - 1] + 1) * B[i]
    return c.max(0)

def runmax1(B):
    return runmax0(B.T)

def clusters(idx, gap):
    out = []
    for i in idx:
        if out and i - out[-1][1] <= gap: out[-1][1] = i
        else: out.append([i, i])
    return [int((a + b) / 2) for a, b in out]

def vlines(dark, frac):
    H, W = dark.shape
    return clusters(np.where(runmax0(dark) > frac * H)[0], int(0.012 * W))

def hlines(dark, frac):
    H, W = dark.shape
    return clusters(np.where(runmax1(dark) > frac * W)[0], int(0.010 * H))

def columns(xs):
    """Pair sorted vertical-line centres into [L,R] column spans via interior-width walk.
    Box interior ~5x the inter-box gap, so a diff near the median interior is a column;
    a small gap or a far stray is skipped."""
    xs = sorted(xs)
    diffs = [b - a for a, b in zip(xs, xs[1:])]
    interior = np.median([d for d in diffs if d > 0.10 * (xs[-1] - xs[0])]) if diffs else 0
    cols, i = [], 0
    while i < len(xs) - 1:
        w = xs[i + 1] - xs[i]
        if 0.7 * interior < w < 1.35 * interior:
            cols.append((xs[i], xs[i + 1])); i += 2
        else:
            i += 1
    return cols

# ---- geometric text erase (operates in-place on an RGB cell crop) ----
def erase_name(cell, pad):
    """White out the bottom-most CENTRED text band (the name / 'Inter' label) when a
    clear white gap separates it from the figure above. Thin full-width rules (the box
    border / cell dividers) are erased and skipped past, so the name below/above a rule
    is still found. Skips ambiguous cases (figure reaches the bottom) to spare line art."""
    H, W = cell.shape[:2]
    dark = cell.mean(2) < INK
    rd = dark.sum(1); dk = 0.012 * W
    r = H - 1
    while r > 0:
        while r > 0 and rd[r] < dk: r -= 1        # skip white
        nb_bot = r
        while r > 0 and rd[r] >= dk: r -= 1       # ascend through the dark band
        nb_top = r
        if nb_bot <= 0: return
        band_h = nb_bot - nb_top
        if band_h <= 0.02 * H:                    # thin rule / speck -> wipe & keep scanning up
            cell[max(0, nb_top - 1):nb_bot + 2, :] = 255
            continue
        spread = dark[nb_top:nb_bot + 1, :].any(0).mean()
        # the name/label is a thin text band (figures are ~0.5H tall); height is the
        # discriminator, not spread (short labels like 'Inter'/'Box' have low spread)
        if band_h <= 0.14 * H and spread >= 0.06:
            cell[max(0, nb_top - pad):H, :] = 255
        return                                    # name erased, or a tall figure band -> leave
    return

def erase_key(cell, pad):
    """White out the isolated key glyph in the top-left corner (bbox of dark content
    in a tight corner window that the centred figure does not reach)."""
    H, W = cell.shape[:2]
    rk, ck = int(0.17 * H), int(0.20 * W)
    sub = (cell[0:rk, 0:ck].mean(2) < INK)
    ys, xs = np.where(sub)
    if len(xs):
        y1, x1 = ys.max(), xs.max()
        cell[0:min(rk, y1 + pad), 0:min(ck, x1 + pad)] = 255

def save(arr, path):
    Image.fromarray(arr).save(path, "WEBP", lossless=True, quality=100, method=6)

def extract_randoms(page):
    """4x4 square grid (16 randoms A-Q). Columns are reliable; rows are snapped to a
    square pitch (= column width) anchored on the detected H-lines, because some pages
    (p20) render the top row borders at < half width and the raw detector misses them."""
    arr, ins = page_arr(page); dark = arr.mean(2) < INK
    xs = vlines(dark, 0.45)
    cols = columns(xs) if len(xs) > 5 else [(xs[i], xs[i + 1]) for i in range(len(xs) - 1)]
    w = float(np.median([r - l for l, r in cols]))          # square cell pitch
    lines = sorted(hlines(dark, 0.40))
    best = None
    for ln in lines:
        for k in range(4):
            y0 = ln - k * w
            if y0 < -0.02 * w: continue
            edges = [y0 + j * w for j in range(5)]
            score = sum(1 for e in edges if any(abs(e - l) < 0.10 * w for l in lines))
            # prefer the highest score, then the TOPMOST grid (weak top borders on some
            # pages tie a correct top-anchored grid with a wrong one built into blank space)
            if best is None or score > best[0] or (score == best[0] and y0 < best[1]):
                best = (score, y0)
    e = [round(best[1] + j * w) for j in range(5)]
    rows = [(e[j], e[j + 1]) for j in range(4)]
    return arr, cols, rows, ins

def extract_blocks(page):
    """Up to 4 cols x 2 block-rows; each block = a 3-cell strip (4 H-edges). Adjacent
    block-rows are sometimes gapped (8 lines, two close at the seam) and sometimes
    contiguous (7 lines sharing the seam) -> collapse near-duplicate lines, then walk
    in strides of 3 so consecutive blocks share their seam edge."""
    arr, ins = page_arr(page); H, W = arr.shape[:2]
    dark = arr.mean(2) < INK
    xs = vlines(dark, 0.28); cols = columns(xs)
    ys = sorted(hlines(dark, 0.10))
    diffs = [b - a for a, b in zip(ys, ys[1:])]
    pitch = float(np.median([d for d in diffs if d > 0.05 * H]))
    merged = [ys[0]]
    for y in ys[1:]:
        if y - merged[-1] < 0.5 * pitch: merged[-1] = int((merged[-1] + y) / 2)
        else: merged.append(y)
    boxes, i = [], 0
    while i + 3 < len(merged):
        boxes.append((merged[i], merged[i + 1], merged[i + 2], merged[i + 3])); i += 3
    return arr, cols, boxes, ins

# ---- crop + write + QA ----
def montage(items, path, cell_w=190):
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

def process(disc, rand_page, block_pages):
    d = f"/tmp/faiext/out/{disc}"; os.makedirs(f"{d}/figures", exist_ok=True)
    named_qa, fig_qa = [], []
    # randoms (row-major A..Q)
    arr, cols, rows, ins = extract_randoms(rand_page)
    ki = 0
    for (r0, r1) in rows:
        for (c0, c1) in cols:
            if ki >= len(RAND_KEYS): break
            key = RAND_KEYS[ki]; ki += 1
            named = arr[r0 + ins:r1 - ins, c0 + ins:c1 - ins].copy()
            fig = named.copy(); erase_key(fig, 6); erase_name(fig, 6)
            save(named, f"{d}/{key}.webp"); save(fig, f"{d}/figures/{key}.webp")
            named_qa.append((key, named)); fig_qa.append((key, fig))
    # blocks (page-major, then row-major; each = 3-cell strip)
    bi = 0
    for pg in block_pages:
        arr, cols, boxes, ins = extract_blocks(pg)
        for (top, d1, d2, bot) in boxes:
            for (c0, c1) in cols:
                if bi >= len(BLOCK_KEYS): break
                key = BLOCK_KEYS[bi]; bi += 1
                named = arr[top + ins:bot - ins, c0 + ins:c1 - ins].copy()
                fig = named.copy()
                erase_key(fig, 6)
                # erase the name band of each of the 3 cells (cell2 'Inter' too; keeps 360/arrows).
                # offsets in CROP coords (origin = top+ins); robust erase_name skips the
                # divider/border rule at each segment bottom and erases the name.
                origin = top + ins; ymax = (bot - ins) - origin
                b = [0, d1 - origin, d2 - origin, ymax]
                for s in range(3):
                    erase_name(fig[max(0, b[s]):b[s + 1], :], 6)
                save(named, f"{d}/{key}.webp"); save(fig, f"{d}/figures/{key}.webp")
                named_qa.append((key, named)); fig_qa.append((key, fig))
    montage(named_qa, f"/tmp/faiext/qa_{disc}_named.png")
    montage(fig_qa, f"/tmp/faiext/qa_{disc}_fig.png")
    print(f"{disc}: randoms={ki} blocks={bi} -> {d}")

if __name__ == "__main__":
    os.makedirs("/tmp/faiext/nat", exist_ok=True)   # extraction + QA staging
    JOBS = {"4-way": (20, [17, 18, 19]), "8-way": (24, [21, 22, 23]),
            "4-way-vfs": (28, [25, 26, 27])}
    for disc, (rp, bps) in JOBS.items():
        process(disc, rp, bps)
