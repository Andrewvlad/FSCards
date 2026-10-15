#!/usr/bin/env python3
"""Pad every card of a cut set with white up to one shared canvas, so a set's randoms, and its
blocks or formations, all ship at one size.

Height pads at the top of a random or formation, where the SCM template's short first table row
loses its rows, and at the top of each block panel, so names keep their distance from the rule
below and both dividers sit on the same rows in every block (aligned on each divider's first core
row). Width, which a column's sub-pixel phase can move a pixel on Ch.7's native crops, pads evenly
on both sides. The canvas is each table row's most common size, the largest row winning, and
never drops below what the set already ships at, so it only grows when a whole row does. A card
past that grows it too and gets flagged. `[canvas]` lines name every canvas that moved.
`extract.py --reset-canvas` drops the shipped floor, for an edition that tightens its tables.

CLI: canvas.py <repo image paths> pads each of those cards up to its set's largest card and
prints the ones it changed, which is how the reject workflow fits the cards it restores."""
import glob, os, sys
from collections import Counter, defaultdict
import numpy as np
from PIL import Image

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))
sys.path.insert(0, f"{ROOT}/tools/panel-cuts")
from measure import FULL, INK, TARGETS, divider_bands

BLOCK_SETS = {discipline for discipline, imageset, *_ in TARGETS if imageset == "USPA"}
RESET = "--reset-canvas" in sys.argv

largest = lambda *sizes: [max(column) for column in zip(*sizes)]
describe = lambda size: f"{size[0]}x{'+'.join(map(str, size[1:]))}"


def mode(values):
    counts = Counter(values)
    return max(value for value, count in counts.items() if count == max(counts.values()))


def layout(image, block):
    """[width, then each panel's height between divider core rows], and the rows each panel's
    padding goes in at: the card top, then midway down the white gap under each divider, clear
    of the line's resize ringing and the art's anti-aliasing."""
    height, width = image.shape[:2]
    if not block:
        return [width, height], [0]
    gray = image.astype(float).mean(2)
    bands = divider_bands(gray)[0]
    cores = [next(r for r in range(top, bottom + 1) if (gray[r] < INK).mean() > FULL) for top, bottom in bands]
    inked = (gray < 245).mean(1) > 0.002
    gaps = [bottom + 1 + int(np.argmax(inked[bottom + 1:])) // 2 for _, bottom in bands]
    return [width, cores[0], cores[1] - cores[0], height - cores[1]], [0] + gaps


def pad(image, canvas, block):
    size, starts = layout(image, block)
    white = lambda rows, columns: np.full((rows, columns, *image.shape[2:]), 255, image.dtype)
    parts = []
    for start, end, height, target in zip(starts, starts[1:] + [len(image)], size[1:], canvas[1:]):
        parts += [white(target - height, size[0]), image[start:end]]
    tall = np.concatenate(parts)
    left = (canvas[0] - size[0]) // 2
    return np.concatenate([white(len(tall), left), tall, white(len(tall), canvas[0] - size[0] - left)], axis=1)


def shipped(discipline, numbered, block):
    """Largest size per dimension among the set's committed cards."""
    sizes = [layout(np.asarray(Image.open(path).convert("RGB")), block)[0]
             for path in glob.glob(f"{ROOT}/assets/diagrams/{discipline}/USPA/*.webp")
             if os.path.basename(path)[:-5].isdigit() == numbered]
    return largest(*sizes) if sizes else None


def fit(discipline, cards):
    """{key: (named, figure, table row)} for one cut discipline -> {key: (named, figure)},
    randoms and numbered cards each padded to their own canvas."""
    fitted = {}
    for numbered in (False, True):
        group = {key: card for key, card in cards.items() if key.isdigit() == numbered}
        if not group:
            continue
        block = numbered and discipline in BLOCK_SETS
        kind = "blocks" if block else "formations" if numbered else "randoms"
        sizes = {key: layout(named, block)[0] for key, (named, _, _) in group.items()}
        rows = defaultdict(list)
        for key, (_, _, row) in group.items():
            rows[row].append(sizes[key])
        floor = largest(*([mode(column) for column in zip(*members)] for members in rows.values()))
        before = shipped(discipline, numbered, block)
        if before and not RESET:
            floor = largest(floor, before)
        canvas = largest(floor, *sizes.values())
        for key, size in sizes.items():
            if largest(size, floor) != floor:
                print(f"[canvas] {discipline} {kind}: {key} ({describe(size)}) outgrew its table row, growing the canvas")
        if before and canvas != before:
            print(f"[canvas] {discipline} {kind}: {describe(before)} -> {describe(canvas)}")
        for key, (named, figure, _) in group.items():
            fitted[key] = (pad(named, canvas, block), pad(figure, canvas, block))
    return fitted


def fit_files(paths):
    """Pad each repo card below its set's largest card (an unstaged R, a restored reject) up to
    it, returning the paths changed."""
    changed = []
    for path in paths:
        parts = os.path.relpath(os.path.abspath(path), ROOT).split(os.sep)
        discipline, key = parts[2], os.path.splitext(parts[-1])[0]
        block = key.isdigit() and discipline in BLOCK_SETS
        image = np.asarray(Image.open(path).convert("RGB"))
        canvas = shipped(discipline, key.isdigit(), block)
        if layout(image, block)[0] != canvas:
            Image.fromarray(pad(image, canvas, block)).save(path, "WEBP", lossless=True, quality=100, method=6)
            changed.append(path)
    return changed


if __name__ == "__main__":
    print("\n".join(fit_files(sys.argv[1:])))
