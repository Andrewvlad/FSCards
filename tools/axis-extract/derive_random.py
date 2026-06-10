#!/usr/bin/env python3
"""Derive a random-style card from a block's entry panel, for a random no AXIS
pool ships natively. Historic use: 4-way R, before the AXIS CISM pool carried
it as a native card (extract.py now claims it from fs4_cism.pdf). Kept as a
manual pathway, unwired from the workflows, should that pool drop or change R
again.

Usage: derive_random.py <block> <key> [discipline]   (e.g. derive_random.py 12 R)

Crops the installed named block card above its first divider, sheds the block
reference-pair tint, swaps the baked block key for the target key drawn in
Liberation Sans Bold (the stand-in the old 856px derivation used; the baked
AXIS key font is not redistributable), and installs the named card plus its
figures/ sibling into the discipline's Axis set. The entry panel's baked
bottom name line carries over as the derived card's name.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import REPO, INK_BLACK, erase, save

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def derive_random(arr, key):
    black = arr[..., :3].max(2) < INK_BLACK
    sep = int(np.where(black.mean(1) > 0.97)[0].min())
    while (arr[sep - 1, :, :3].mean(1) < 245).mean() > 0.8: sep -= 1
    panel = arr[:sep].copy()
    # the derived card is a random: shed the block iconage — blocks suit a
    # reference pair in red (239,0,0) / blue (0,176,240) to track across panels,
    # while randoms are all greyscale. Un-mix the tint per pixel keeping the
    # black-ink alpha: the flat fill maps to the white suit, black-line AA to
    # the grey ramp, white-edge AA back to white.
    f = panel[..., :3].astype(float)
    sat = f.max(2) - f.min(2) > 8
    for mask, dom, off, fill in ((sat & (f[..., 0] >= f[..., 2]), 0, 1, 239),
                                 (sat & (f[..., 2] > f[..., 0]), 2, 0, 240)):
        v = np.clip((f[..., dom] - f[..., off]) * 255 / fill + f[..., off], 0, 255)
        panel[..., :3][mask] = v[mask, None].round()
    # measure the block-key bbox before erasing, to size and place the new key
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
    for size in range(80, 8, -1):   # largest size whose cap height fits the block-key bbox
        font = ImageFont.truetype(FONT, size)
        bx = draw.textbbox((0, 0), key, font=font)
        if bx[3] - bx[1] <= kh: break
    draw.text((kx0 - bx[0], ky0 - bx[1]), key, font=font, fill=(0, 0, 0))
    return np.array(im), erase(panel)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: derive_random.py <block> <key> [discipline]")
    block, key = sys.argv[1], sys.argv[2]
    d = sys.argv[3] if len(sys.argv) > 3 else "4-way"
    set_dir = f"{REPO}/{d}/Axis"
    arr = np.array(Image.open(f"{set_dir}/{block}.webp").convert("RGB"))
    named, fig = derive_random(arr, key)
    save(named, f"{set_dir}/{key}.webp")
    save(fig, f"{set_dir}/figures/{key}.webp")
    print(f"{d}/{key}: {named.shape[1]}x{named.shape[0]} derived from block {block} into {set_dir}")
