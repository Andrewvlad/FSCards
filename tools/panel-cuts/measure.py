#!/usr/bin/env python3
"""Measure per-block panel-divider positions in shipped block strips.

Walks assets/diagrams/<discipline>/<set>/<key>.webp for block (numeric) keys and
locates the two internal divider bands by full-width row scan (the axis-extract
approach: scan rows, not components, so art touching a divider can't break the
split). Emits cut fractions as divider band OUTER edges — the client crops each
panel between bands, so the baked divider is excluded entirely and the CSS
border draws the only rule — plus an audit contact sheet (bands shaded red,
exact-thirds ticks in blue) for eyeball QA.

Each entry is [width/height, d1_top, d1_bot, d2_top, d2_bot] — the aspect ratio lets the
client size the panel row without waiting for the image to load; dividers are fractions
of image height, panels are [0, d1_top], [d1_bot, d2_top], [d2_bot, 1].

Writes assets/diagrams/panel-cuts.js (the PANEL_CUTS global consumed by diagramFace).

Pass discipline names as args (e.g. `measure.py 2-way 8-way`) to re-measure only those
and splice them into the committed file, leaving other disciplines byte-identical. No
args rebuilds the whole file. The extract workflow passes the disciplines install.py touched.
Audit contact sheets render only for sets whose cuts actually moved (none if nothing changed).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]

# Every set with 3-panel block strips. Not listed: Rhythm (blocks are single continuous
# drawings — poolImages reroutes them to USPA, or FAI for indoor variants, under split).
# A third element redirects the scan: 4-way-cf USPA ships SVGs, measured via their
# committed same-extent trace cells
TARGETS = [
    ('2-way', 'USPA'), ('2-way', 'Axis'),
    ('4-way', 'USPA'), ('4-way', 'Axis'), ('4-way', 'FAI'),
    ('8-way', 'USPA'), ('8-way', 'Axis'), ('8-way', 'FAI'),
    ('16-way', 'USPA'), ('16-way', 'Axis'),
    ('2-way-vfs', 'USPA'), ('2-way-vfs', 'Axis'),
    ('4-way-vfs', 'USPA'), ('4-way-vfs', 'Axis'),
    ('2-way-mfs', 'USPA'), ('2-way-mfs', 'Axis'),
    ('4-way-cf', 'USPA', 'tools/cf-vectorize/native/4-way-cf'), ('4-way-cf', 'Axis'),
]

INK = 110          # ink-core luminance ceiling (matches uspa-extract's INK)
FULL = 0.90        # row fraction below a threshold that counts as a full-width divider row
FRINGE = 254       # anti-alias luminance ceiling for the band-edge extension
GAP = 3            # px between core rows still clustered as one band


def divider_bands(g):
    """Two (top, bottom) divider bands, inclusive, fringe included. A divider is a
    near-complete full-width ruled line - when more than two rows clear the full-width test
    (a dense art row can), the two STRONGEST lines win, never the two nearest a position.
    So a block whose panels are unequal heights (a source-side mistake) still resolves to its
    real dividers, and the measured fractions report whatever heights those panels actually are."""
    H, W = g.shape
    core = np.where((g < INK).mean(1) > FULL)[0]
    bands = []
    for r in core:
        if bands and r - bands[-1][-1] <= GAP: bands[-1].append(int(r))
        else: bands.append([int(r)])
    if len(bands) < 2: return None
    # rank by how complete a ruled line each band is (peak then mean coverage), not where it
    # sits: a real divider saturates the row (~1.0), incidental full-width art averages lower
    cover = lambda b: (max((g[r] < INK).mean() for r in b),
                       float(np.mean([(g[r] < INK).mean() for r in b])))
    picked = sorted(sorted(bands, key=cover, reverse=True)[:2], key=lambda b: b[0])
    out = []
    for b in picked:
        top, bot = b[0], b[-1]
        # a fringe row is full-width pale, like the core is full-width dark — a row-mean
        # test instead bleeds the band through adjacent art on the grey-realistic sets
        while top > 0 and (g[top - 1] < FRINGE).mean() > FULL: top -= 1
        while bot < H - 1 and (g[bot + 1] < FRINGE).mean() > FULL: bot += 1
        out.append((top, bot))
    return out, len(bands) - 2


def clearance(g, bands, ink=245):
    """Smallest white run between a divider band edge and the nearest ink row (walking
    outward, so the band's own rows don't count), as a height fraction — the floor under
    the client's SEAM_MARGIN window inset."""
    H = g.shape[0]
    inked = (g < ink).mean(1) > 0.002
    runs = []
    for top, bot in bands:
        for r, step in ((top - 1, -1), (bot + 1, 1)):
            n = 0
            while 0 <= r < H and not inked[r]: n += 1; r += step
            runs.append(n)
    return min(runs) / H


def measure_set(discipline, imageset, srcdir=None):
    setdir = ROOT / srcdir if srcdir else ROOT / 'assets' / 'diagrams' / discipline / imageset
    ink = 128 if srcdir else 245  # Trace input: residue paler than trace.py's threshold never reaches the SVG
    results, extras = {}, {}
    # '13_indoor' style stems sort with their base block
    for f in sorted(setdir.glob('[0-9]*.webp'), key=lambda p: (int(p.stem.split('_')[0]), p.stem)):
        im = Image.open(f).convert('RGB')
        fig = setdir / 'figures' / f.name
        if Image.open(fig).size != im.size:   # a :diagram-only reject can desync the pair: skip, don't abort
            print(f'  !! {fig} extents differ from named, skipping'); continue
        g = np.asarray(im).astype(float).mean(2)
        det = divider_bands(g)
        if det is None:
            print(f'  !! {f}: <2 divider bands found')
            continue
        bands, extra = det
        if extra: extras[f.stem] = extra
        H = g.shape[0]
        (t1, b1), (t2, b2) = bands
        results[f.stem] = ((im.width / im.height, t1 / H, (b1 + 1) / H, t2 / H, (b2 + 1) / H), im, bands, clearance(g, bands, ink))
    return results, extras


def audit_sheet(discipline, imageset, results, path):
    """Blocks tiled at uniform height, divider bands shaded red, thirds ticked blue."""
    TILE_H, PAD, LABEL = 420, 8, 14
    tiles = []
    for key, (cuts, im, bands, clr) in results.items():
        w = round(im.width * TILE_H / im.height)
        tile = im.resize((w, TILE_H), Image.LANCZOS).convert('RGB')
        d = ImageDraw.Draw(tile, 'RGBA')
        s = TILE_H / im.height
        for top, bot in bands:
            d.rectangle([0, top * s - 1, w, (bot + 1) * s + 1], fill=(255, 0, 0, 110))
        for frac in (1 / 3, 2 / 3):
            d.line([0, frac * TILE_H, w, frac * TILE_H], fill=(0, 90, 255, 160), width=1)
        drift = max(abs((cuts[1] + cuts[2]) / 2 - 1 / 3), abs((cuts[3] + cuts[4]) / 2 - 2 / 3))
        d.text((3, 2), f'{key}  {drift * 100:.2f}%', fill=(0, 0, 0, 255))
        tiles.append(tile)
    cols = 11
    rows = -(-len(tiles) // cols)
    tw = max(t.width for t in tiles)
    sheet = Image.new('RGB', (cols * (tw + PAD) + PAD, rows * (TILE_H + PAD + LABEL) + PAD), '#888')
    for i, t in enumerate(tiles):
        sheet.paste(t, (PAD + (i % cols) * (tw + PAD), PAD + (i // cols) * (TILE_H + PAD + LABEL)))
    sheet.save(path)


HEADER = ['// Auto-generated by tools/panel-cuts/measure.py',
          '// Per block: [width/height, divider-1 top, divider-1 bottom, divider-2 top, divider-2 bottom];',
          '// dividers as fractions of image height, band edges just outside the line and its fringe.',
          '// A set whose blocks all share one geometry (Axis: every card is 300x900 with fixed',
          '// dividers) carries a single shared tuple instead of a per-block map.',
          'const PANEL_CUTS = {']


def set_lines(imageset, results):
    """One image set's panel-cuts.js lines (8-space indented). Blocks that all share one
    geometry collapse to a single shared tuple instead of a per-block map."""
    cells = {key: ', '.join(f'{c:.4f}' for c in cuts) for key, (cuts, *_) in results.items()}
    if len(set(cells.values())) == 1:
        return [f'        {imageset}: [{next(iter(cells.values()))}],']
    out = [f'        {imageset}: {{']
    for key, cell in cells.items():
        jskey = key if key.isdigit() else f"'{key}'"
        out.append(f'            {jskey}: [{cell}],')
    out.append('        },')
    return out


def discipline_block(discipline, sets):
    """One discipline's panel-cuts.js lines (4-space indented), sets in measure order."""
    out = [f"    '{discipline}': {{"]
    for imageset, results in sets.items():
        out += set_lines(imageset, results)
    out.append('    },')
    return out


def parse_set_blocks(text_lines):
    """{(discipline, set): [lines]} from a committed panel-cuts.js, keyed by the emitted
    indent structure, so a re-measured set can be diffed against what shipped."""
    blocks, d, s = {}, None, None
    for l in text_lines:
        indent = len(l) - len(l.lstrip(' '))
        st = l.strip()
        if indent == 4 and st.endswith('{'):     # 'discipline': {
            d, s = st.split("'")[1], None
        elif indent == 4:                         # discipline close
            d = None
        elif indent == 8 and st != '},':          # set open (shared tuple or map header)
            s = st.split(':')[0]
            blocks[(d, s)] = [l]
        elif indent == 8:                         # map set close
            blocks[(d, s)].append(l); s = None
        elif indent == 12:                        # block line within a map set
            blocks[(d, s)].append(l)
    return blocks


if __name__ == '__main__':
    only = set(sys.argv[1:])   # discipline names to re-measure; empty = full rebuild
    targets = [t for t in TARGETS if not only or t[0] in only]
    if only and not targets:
        print(f'no strip sets for {sorted(only)}, nothing to measure')
        sys.exit(0)

    cutsfile = ROOT / 'assets' / 'diagrams' / 'panel-cuts.js'
    old_blocks = parse_set_blocks(cutsfile.read_text().splitlines()) if cutsfile.exists() else {}

    measured = {}
    floor = (1.0, None)
    for discipline, imageset, *src in targets:
        print(f'{discipline}/{imageset}:')
        results, extras = measure_set(discipline, imageset, *src)
        if not results:                       # SVG-only set (4-way-cf USPA) or every pair reject-desynced
            print('  no blocks measured'); continue
        measured.setdefault(discipline, {})[imageset] = results
        for key, n in extras.items():
            print(f'  note: {key} had {n} extra full-width candidate band(s), resolved by line strength')
        drifts = [max(abs((c[1] + c[2]) / 2 - 1 / 3), abs((c[3] + c[4]) / 2 - 2 / 3)) for c, *_ in results.values()]
        clr = min(r[3] for r in results.values())
        floor = min(floor, (clr, f'{discipline}/{imageset}'))
        print(f'  {len(results)} blocks, max drift from thirds {max(drifts) * 100:.2f}%, '
              f'min ink clearance {clr:.4f}')
    print(f'min ink clearance {floor[0]:.4f} ({floor[1]}) over measured sets — SEAM_MARGIN must stay below it')

    # Write panel-cuts.js: splice scoped disciplines into the committed file, or full rebuild
    if only:
        text = cutsfile.read_text().splitlines()
        for discipline, sets in measured.items():
            block = discipline_block(discipline, sets)
            start = next((i for i, l in enumerate(text) if l == f"    '{discipline}': {{"), None)
            if start is None:
                text[text.index('};'):text.index('};')] = block   # new strip discipline
            else:
                end = next(i for i in range(start + 1, len(text)) if text[i] == '    },')
                text[start:end + 1] = block
        cutsfile.write_text('\n'.join(text) + '\n')
        print(f'merged {", ".join(measured)} into {cutsfile.relative_to(ROOT)}')
    else:
        out = list(HEADER)
        for discipline, sets in measured.items():
            out += discipline_block(discipline, sets)
        out.append('};')
        cutsfile.write_text('\n'.join(out) + '\n')
        print(f'wrote {cutsfile.relative_to(ROOT)}')

    # Audit sheets only for sets whose cuts actually moved (nothing to eyeball otherwise)
    changed = [(d, s) for d, sets in measured.items() for s in sets
               if set_lines(s, sets[s]) != old_blocks.get((d, s))]
    for discipline, imageset in changed:
        sheet = Path(__file__).parent / f'audit-{discipline}-{imageset}.png'
        audit_sheet(discipline, imageset, measured[discipline][imageset], sheet)
        print(f'  audit sheet: {sheet.relative_to(ROOT)}')
    print(f'{len(changed)} set(s) moved cuts' + ('' if changed else ', no audit sheets'))
