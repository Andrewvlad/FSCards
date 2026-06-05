# fai-extract

Re-cuts the `FAI` image sets under `assets/diagrams/<discipline>/FAI/` from the
official **2026 FAI ISC FS+VFS Competition Rules** PDF, committed at
`assets/sources/fai/fai_fs_2026.pdf` (originally fai.org → `2026_ISC_CR FS.pdf`).
The dive-pool annexes A–F sit on pp17–28:

| discipline | blocks | randoms |
|---|---|---|
| 4-way | pp17–19 | p20 |
| 8-way | pp21–23 | p24 |
| 4-way-vfs | pp25–27 | p28 |

These are the only FAI-governed pools — there is no FAI 10-way/16-way/6-way, MFS,
2-way-FS or VFS 2-way set.

Run `python3 extract.py`; staging lands in `/tmp/faiext/out/<discipline>/`, install
by copying over `assets/diagrams/<d>/FAI/`. Then `python3 rext.py` adds **4-way
`R`/Bundy** (CISM-only, absent from the FAI pool): block 12's first cell *is* the
Bundy formation, so it is cropped above its first divider with the "12" key erased
and the "Bundy" name kept.

## How it works

Annex pages are single page-wide rasters with key+name baked in — no per-cell text
layer (only the page title/footer are real text). Pages render at 300 DPI and cells
are found geometrically:

- **Randoms**: a 4×4 grid. Columns detect reliably; rows are snapped to a square
  pitch (= the column width) anchored on the detected horizontal lines, preferring
  the **topmost** scoring candidate — some pages render top-row borders at less
  than half width, which the raw line detector misses.
- **Blocks**: 4 columns × N block-rows, each block a 3-cell strip. Adjacent
  block-rows sometimes share their seam line and are sometimes gapped, so
  near-duplicate lines are collapsed first, then edges walked in strides of 3.
- **`figures/`**: geometric erase of the top-left key glyph plus each cell's
  bottom-most *text band*, discriminated by band **height** ≤ 0.14·H rather than
  ink spread (short labels like "Inter"/"Box" have low spread); thin full-width
  border/divider rules are wiped and scanned past so a name above/below a rule is
  still found. Line art, dividers, and rotation arrows / `360°`–`540°` labels
  survive.

Output is **560px-wide q90 webp**, matching the USIS set (the comparable
FAI-source raster resolution). Visual QA montages land at `/tmp/faiext/qa_*.png`.
