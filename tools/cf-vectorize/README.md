# cf-vectorize

Produces the CF-outline (`USPA`) **SVG** sets under `assets/diagrams/2-way-cf/USPA/`
and `assets/diagrams/4-way-cf/USPA/` by vector-tracing the native PDF raster cells.
The CF sources embed low-res rasters (no vector master exists), so the scalable set
is a trace, not a re-render.

| script | input | output |
|---|---|---|
| `cfborder_ll.py` | FAI/APF CF CR page extracts (`fai18-*`, `fblk*`, `fblk17-*`, `cf2-*` PNGs — `pdfimages` output, regenerated into `/tmp/cf4` from `assets/sources/cf/` when absent) | `native/` — border-stripped cells at native res, lossless webp (CF4 randoms ~260px A–H / ~174px I–N, blocks ~310×975; CF2 ~430px, A ~258px) |
| `trace.py` | one cell webp | one SVG |
| `batch.py` | all of `native/` | all 68 SVGs in `assets/`, plus a render-back MAE QA screen |
| `restamp.py` | the batch-traced CF4 SVGs + CF2 `figures/E.svg` | the shipped CF4 set: every canopy re-stamped with the CF2 donor glyph |

`native/` is committed as the archival trace input — the previously committed webps
(lossy, resampled to 700/860px) are not valid trace input. Re-running `batch.py`
reproduces the assets from the repo alone, and with the source PDFs committed under
`assets/sources/cf/` (FAI CF CR 2025 + APF CF CR 01-2025 — the APF annex is the
highest-res raster of the CF2 outline art) `cfborder_ll.py` re-cuts `native/` from
the repo alone too. It also documents the border-only `strip_box` (no margin, no
resample), the figures' label erasure, and the `GRIDS` map decoding the source
PDF's out-of-order block grids.

Trace contract (`trace.py`):

- `descrumb` first clears border-strip residue hugging the cell edges: ≤6px crumbs
  near an edge, any ink component fully contained in the 3px edge band, and the
  faint (≥128) halo in the outer 2px ring, which Lanczos overshoot would otherwise
  pull under the threshold and trace as an edge hairline. Real art survives both
  rules — it extends inward past the band and its core ink is darker (block dividers
  still run edge to edge). The committed `native/` cells keep the residue.
- Grayscale cell is Lanczos-upscaled (min side ≥ ~2400px) before a 50% threshold, so
  the traced contour follows the anti-aliased ink boundary at sub-native-pixel
  accuracy; potrace (pure-Python `potracer`) fits curves to that. Render-back MAE vs
  the source at native size is ≲2/255 (denser cards ~4).
- Cells keep their full extents — no content crop. The SVGs are **background-free**
  (no white rect): the art floats on the app's card/tile, with the stylesheet's
  `:root[data-diagram="invert"]` rule keeping the global white `img` background off
  these diagrams in both themes.
- Intrinsic `width`/`height` attrs are inflated to min side 1100 (FS-set scale):
  CSS `max-width/max-height` never upscales an `img` past its intrinsic size, so
  native-size attrs would render small; for vectors the attrs are free.

Canopy re-stamp (`restamp.py`) — **the shipped CF4 set is NOT the bare batch.py
trace**: the CF4 cells' 174-343px sources put their ~1-3px strokes below clean
trace resolution (wobbly contours, uneven weight), so every canopy in the CF4
set is replaced by a donor glyph cut from CF2 E — the top canopy's
arc/slider/lines completed with the bottom canopy's free tip,
translation-grafted along the matching suspension lines (same glyph, slopes
match to ~1e-4); line weight is the CF2 stroke by construction. Formation
geometry is preserved from the batch trace: per-canopy template fits over a
scale ladder (canopy size varies ~40-76 native px by card class), one
consensus scale per card (per-canopy measures skew on abutting pairs and
filled domes — B/I/J/M's canopies overlapped in v1 from exactly that; on
blocks the median is further arbitrated by dock success, since filled domes
can drag a majority of fits — and the median with them — a rung low, which
left block 5's stack joints gapped and bridged by a stray weld line), a 0.87
vertical squash (the CF4 source glyph is squatter than CF2's: stack spacing /
arc width 0.85-0.88 vs 0.98), apexes re-anchored on the old art's line-fit
tips, and the poses constraint-solved against the formation's attachment
graph, per panel on blocks: a tip docks at exactly one of three points of its
target canopy (either arc corner or the slider-bump top at center, sinking
0.4 stroke when the source merges them), a joint dock (tip into the meeting
point of two canopies) holds both corners, and abutting corners snap onto
each other — canopies touch at the attachment points and never overlap. The
old touch topology is enforced by a weld pass; there is deliberately **no
separation-channel pass** — extra old components are trace damage whose
breaks a channel would carve into the clean stamps (as one did to randoms
D/E/F/G and to the block fills before it was dropped).

Blocks additionally restore the **canopy coloring** (clear / full black /
half black / two black stripes — the block pools mark jumper groupings):
each canopy's pattern classifies from the old art's erosion cores (strokes
erode away, solid fills survive; cores are owned by the pose whose dome
contains them) and composes from the authentic CF2 fill — E's bottom canopy
is the donor glyph's filled twin, aligned exactly by the same suspension-line
fits, so the band-window shape is genuine; CF4 fills paint solider than
CF2's (slider-detail whites go black, only the window stays white), and
half-fills cover their side of the window when the source draws it dark.
Striped canopies all paint one canonical pair, mirrored about the arc
centre (survey medians over every striped canopy) — the source stripes
vary canopy to canopy and lean wider on the right, so the measured spans
only classify.
Block cards compose **preserve-and-replace**: the old trace survives verbatim
— INTER arrows, marks, dividers, text (the v1 rebuild silently dropped the
arrows) — and only canopy ink (old components mostly inside the stamp
silhouettes) is erased and re-stamped. Randoms rebuild from parts (text +
dividers + stamps) as before. Key/name/INTER text and the block dividers are copied verbatim from
the batch trace; the composite re-traces with `trace.py`'s potrace settings.
Regenerate CF4 with `python3 batch.py && python3 restamp.py` — **running
batch.py alone regresses the CF4 set to the wobbly native traces** (the CF2
set IS the plain batch trace; restamp does not touch it).

Deps beyond stdlib: `numpy`, `pillow`, `scipy` (extractor only), `potracer`,
`cairosvg` (QA render only). The latter two are pip-only; on a PEP-668 system:
`pip install --user --break-system-packages potracer cairosvg`.
