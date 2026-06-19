# fai-extract

Extraction pipelines for the FAI ISC raster dive pools, reading the CR PDFs
committed under `assets/sources/fai/` (originally fai.org — re-download only to
pick up a CR revision). Output is **lossless webp at native embedded-raster
size** — never resampled.

| script | set | source | pages |
|---|---|---|---|
| `extract.py` | `FAI` 4-way + 8-way (outdoor) | `fs.pdf` (current FS CR) | **located per edition** from annex running titles (2026: 4-way blocks pp17–19 / randoms p20, 8-way pp21–23 / p24) |
| `usis.py` | indoor 8-way, merged into `FAI` | `indoor.pdf` (current Indoor CR) | **located per edition** (2026: blocks pp26–28, randoms p29, starting formations p30) |
| `rext.py` | 4-way `R`/Bundy (derived) | `fs.pdf` block 12 | — |

Sources are yearless and overwritten per edition (the year lives in `legacy/<year>/`); the live
pipeline re-extracts whenever they change. Run `python3 extract.py && python3 rext.py` (outdoor
4-way + 8-way + the derived R, staging `/tmp/faiext/out/<d>/`) and/or `python3 usis.py` (indoor
8-way, staging `/tmp/usisext/8-way/USIS/`), then `python3 install.py` to copy the staged sets over
`assets/diagrams/<d>/FAI/`. Install is **pixel-aware**: a card installs only when its decoded
pixels changed (so a libwebp re-encode or a re-rendered source never floods the diff), a key that
left the pool is deleted (refused wholesale if staging covers under half the set). The indoor cut
ships **merged** into 8-way/FAI: only the cells whose indoor art differs from the outdoor card
install, renamed `<13|17|20>_indoor.webp` (+ `figures/` siblings), plus the two starting-formation
reference cards — every other indoor cell is byte-identical to the outdoor cell (block 21 differs
only by ~45 px of anti-alias jitter, below the variant threshold), so the indoor-variant set is
read from the art, never a hardcoded `13/17/20` list. The whole run is automated by
`.github/workflows/extract-fai-images.yml` on a merged CR (see **Pipeline** below).
`rext.py` adds
**4-way `R`/Bundy** (CISM-only, absent from the FAI pool): block 12's first
panel *is* the Bundy formation, cut with the "12" key swapped for a drawn "R"
and the "Bundy" name kept. The R is Liberation Sans Regular (the PDF's text
face is ArialMT; Liberation Sans is its metric-compatible local stand-in, as in
the Axis derivation), sized and placed from a sibling random's measured key so
it sits exactly like the lettered keys around it. R being a random, the block
iconage goes too — the panel X-marks jumper 2's back to track him across the
block, while randoms carry no marking (USPA's R equally sheds its back-dot).
The marked torso is a different drawing, not an overlay (narrower outline), so
erasing the X strokes leaves a wrong-shaped back; instead, block 12 ending in
a second Bundy, the end panel's clean torso window is grafted 1-1 — the two
stamps register within a pixel (dy −1, measured like the key box; elsewhere
they differ only in subpixel rendering). A seam check on the window's border
band trips if a CR revision shifts the stamps.

**The FS CR's VFS annex (pp25–28) is deliberately not extracted**: its art is
USPA's ("Images Copyright United States Parachute Association"), already
shipped better in the USPA set — and only p25 embeds it as a raster (pp26–28
draw the jumpers as vector over an empty grid raster, so reviving them would
need a render-mode page source, not `pdfimages`).

## How it works

**Pages are located per edition, never hardcoded.** `locate()` reads each page's annex running
title and keys on the stable core `CURRENT [INDOOR ][VERTICAL ]FORMATION SKYDIVING <N>-WAY
<BLOCK|RANDOM> POOL` shared by every edition — the prefix drifts (`Addendum <L> -` in 2018, none
in 2022–24, `ANNEX <L> -` in 2025–26) so it is not matched; `current` anchors the title and never
appears in body text. The optional `INDOOR` word marks the Indoor CR's 8-way pool, so `usis.py`
calls the same `locate(indoor=True, widths=(8,))` instead of hardcoded page numbers (the indoor
8-way pool was added in 2020; 2018 has none, located as empty). A block annex spans from its title
page to the next annex's; the contents page (which lists every annex) and TOC dot-leader lines are
rejected by keeping only a page that names exactly one annex. This is the robustness `uspa-extract`'s
`find_pages` relies on (CR front matter and annex order drift every revision), verified across the
2018–2026 editions kept in `legacy/`.

**Keys are read from the art, never assigned by position.** Each detected cell's baked top-left
key glyph (`keyglyph`, isolated by the same top-left zone + size caps `erase_key` uses — FAI art is
solid black like the key, so position and size separate them, not colour) is matched (`glyph_dist`,
size-gated mismatch fraction) against a template library harvested from the installed FAI set
(`key_templates`: the filename is the key, the baked art is the glyph), and the cell takes its
best match. This is the approach `axis-extract` uses on its identical no-text-layer PDFs, so a pool
reorder or addition is picked up from the art itself, with no `RAND_KEYS`/`BLOCK_KEYS` list to edit.
A block's key lives in panel 1, so its strip is sliced to the first panel both when harvesting and
when reading. A weak or ambiguous match prints a `CHECK` flag; a key read twice is dropped with a
`!!`. Verified on the 2026 CR: the glyph reads reproduce the old positional output byte-for-byte
(152/152 cells) and recover every cell's own key from pixels alone (80/80, both disciplines,
including the synthetic `R` and the `_indoor` variants). Harvesting depends on the installed set
existing — a fresh checkout always has it (it is shipped), and an empty harvest asserts loudly.

Every extracted page embeds its complete art as **one native raster** (verified:
a page render adds only title/footer furniture), composited over white through
its smask when one is embedded (paired by PDF object number in `pdfimages
-list`). There is no per-cell text layer — key + name are baked into the art —
so geometry and text removal are pixel-based:

- **Cells** crop between the **full extents** of the detected grid-line spans,
  then shrink only past full-length line residue (grid-line core + pale
  anti-alias fringe, `shrink`) — **no original white space is ever removed**,
  and line-hugging art keeps every pixel up to the line itself. `shrink`'s
  contiguous-run test misses three fringe shapes the outer edges carry, so
  `edge_fringe` finishes the walk there: partial-height fringe (line beside
  some panels, white beside others — 8-way 14/21), full-height fringe broken
  by stray white px (8-way 6/22, a ~234-grey line the split-panel view showed
  as border bleed), and faint 248–253 fringe above `shrink`'s 245 threshold
  entirely. A line goes when it is **mostly pale** (< 254 over ≥ 0.25 of its
  length — art at an edge measures ≤ 0.11, white 0) or blank while directly
  shielding such a line (a halo detached across a 1px gap, 4-way G/O — the
  only case where a border's own internal 1px white gap goes with it); a white
  margin row still stops the walk before any caption or art. Gapped
  block-row seams keep both lines — the earlier midpoint-merge bled each row's
  border into its neighbour (stray line at a cell's top/bottom). Only
  near-duplicates (< 0.1 pitch) merge. Randoms rows anchor on the detected
  H-lines at the rows' own pitch (their median spacing, **not** the column
  width: cells are square on recent editions but ~3% shorter than wide on 2018,
  and assuming square overshot the raster), each predicted edge refining to a
  detected span where one exists, an anchor whose grid falls off the raster
  rejected. Block columns pair adjacent vertical lines at the median cell width,
  so both layouts cut: gutter-separated strips (own L+R border each, 2026) and
  the contiguous shared-border grid older editions draw (one line per boundary —
  the earlier skip-ahead-by-two dropped every other column there).
  Neither set ships frame borders: FAI cells have none in-source, and `usis.py`
  strips USIS's printed ones by the same line+fringe rule (`strip_border`,
  applied after the erase; internal block dividers stay), matching the
  borderless USPA/Axis cells.
- **Dust** baked into the source rasters is removed by `despeckle` (both
  pipelines, named card and figure alike): lone stray specks (8-way C/K) and
  *ghosting* — shattered pale remnants of leftover art on the page (8-way 21's
  free-bear ghost legs, block 9, USIS 17 and the USIS starting-formation
  variant, plus ~40 cards of single-pixel dirt). Dust is a small non-spanning
  component (a full-width pale row is a divider's detached AA halo, kept) that
  either never reaches ink darkness (min luminance ≥ 185 — real art bottoms
  out near 0) or sits ≥ 12 px from all other ink (every legitimate detached
  mark — i-dot, degree sign, AA-split limb tip — measures within ~4 px of its
  parent). Pale components are spared when they tail a text run (y-overlap +
  x-adjacency to a glyph-sized dark component): the faintly-rendered degree
  rings of 8-way 21's inter labels never get darker than the ghost crumbs, but
  only they hug a digit. Painting dilates like the glyph erase, so the speck's
  own fringe whisper goes too. Figures despeckle *after* their erase (a spared
  caption-hugging crumb loses its anchor glyphs with the caption and goes);
  `usis.py` despeckles after the border strip — a speck just inside the
  printed frame fuses into the border component through its AA fringe and
  would ride the spanning exemption.
  **connected component**: a component lying fully inside the corner/bottom zone
  and under glyph-size caps is wiped, and art dipping beside a caption belongs
  to a large component and survives. Caption candidates must additionally form
  the **caption's own text cluster** (`baseline=0.07`): members chain by
  x-adjacency (≤ 0.14 W spans word gaps, measured ≤ 24px) plus y-overlap — or a
  small y-gap for tiny ≤ 6px components, the i-dots hovering overlap-free above
  an all-lowercase word (Bunyip, Marquis, Iroquois) — and the cluster erases
  only if it has ≥ 3 members (every caption measures ≥ 3) and a member's bottom
  reaches within 7% of the panel bottom (caption bottoms measure ≤ 4.7%
  everywhere). Detached art in the band is also small and zone-bound, and
  without the test the erase swallowed ~50 such components whole across the
  three sets, invisibly to the partial-component audit: art floating higher
  fails the baseline reach (leg pieces split off by an AA gap, rotation arrows,
  the `360°`/`540°` labels — one touches its row at y-gap 0, so tall components
  never gap-join), and art *at caption height* (8-way 20's mid-panel foot, 76px
  left of `Inter`) is x-distant and under-sized as a cluster of its own.
  Components form on the fringe-inclusive mask (< 200) *without* dilation
  (dilation bridged glyphs to art above and spared them), and painting dilates
  the erased component so its anti-alias fringe goes too (no ghost outline) —
  spilling only onto unlabeled fringe, never another component's pixels (a
  caption descender two px off a USIS frame border must not nibble the border).
  Block strips keep their internal divider lines; the erase slices exclude the
  divider **cores by span and their AA fringe by `shrink`** — the fringe rows
  otherwise form a full-width sub-white component inside the slice that a
  caption descender fuses with, hiding its glyph from the erase (8-way 15
  "Zippers" kept both p's; their sub-slice descender tips remain as invisible
  ≤ 5px wisps on the divider fringe). `usis.py` shares these erasers, slicing
  panels between the full-width line spans (frame top, dividers, frame bottom),
  shrunk the same way, with wider caps for the larger-type starting-formation
  label. (Its earlier rectangle wipes flat-cut any art reaching into the key
  window or a name band — 32 of 40 cards; the still-older full-width band erase
  also clobbered the side borders and needed a post-hoc heal pass.)
- **Self-audit**: after every card, the script checks the crop's outer 2px for
  full-length line runs *and* mostly-pale fringe lines (under-shrunk border,
  mirroring both `shrink`'s and `edge_fringe`'s rules), asserts the
  **partial-component invariant** — every ink component is erased whole (a
  glyph) or kept whole (art), so an erase zone misfiring into art is caught;
  cell-spanning components are exempt, since erasing a divider-fused descender
  legitimately takes part of the merged component — and re-runs the caption
  erase per panel third expecting no further ink drop (missed caption); `!!`
  warnings print per key. `usis.py` asserts the same invariant plus an erase
  re-run, and the line-residue check after its border strip. Visual QA montages
  land in the staging dirs.

The FAI and USIS strips' panels are equal thirds within ≤ 0.21% divider drift
vs exact H/3 (the earlier 0.65–1.5% FAI figure was an artifact of the old
fixed-margin crop), inside the ≤ 0.4% bound the app's split-panel view was
verified against — see the split-panels note in CLAUDE.md.

## Pipeline

A merged FAI CR re-extracts itself. `.github/workflows/extract-fai-images.yml` fires on a push to
`main` touching `assets/sources/fai/fs.pdf` or `indoor.pdf` (the watcher that would open
those source PRs is not yet wired — download a CR revision by hand for now): it runs `extract.py` +
`rext.py` when the FS CR changed and `usis.py` when either CR changed (the indoor-variant decision
reads the outdoor cards), then `install.py`, the shared `validate_ordering.py` ordering canary and
`panel-cuts/measure.py`, and opens a review PR with the install summary, any `CHECK` key-match
flags, and a bot comment tabling each changed image old-vs-new (SHA-pinned raw URLs, since webp
gets no GitHub rich diff). Reject individual cards with a `/reject <keys>` comment, or approve a
same-art quality bump with `/upscale <keys>` (keeps the card, drops only its deprecation archive) -
both via the shared `reject-extracted-images.yml` (e.g. `/reject 13 20_indoor:figure`); the PR is
never auto-merged. Mirrors the AXIS and USPA extract pipelines.

## Legacy and the deprecated corpus

`assets/sources/fai/legacy/<year>/` holds every CR edition back to 2018, the current one included
(see its README; 2020 FS is unrecoverable). `legacy.py` runs the live extractor over every **outdoor**
FS edition — mapping cells to the canonical pool order **by position** (`process(keys=...)`, since the
baked-key glyph reader is within-edition and older letterforms drift) — and compares each key's
**name-erased figure** to the current shipped one with a shift / scale / whitespace-tolerant metric
(ink-bbox crop, 128x128, mean abs diff), writing the deprecated-image corpus under `legacy/deprecated/`.
The figure (art only), not the named diagram, is the deprecation signal:
it ignores a baked name-text fix (e.g. Open Acordian -> Open Accordion), the threshold (>= 16) sitting
above the erasure-pixel noise floor (~10-14) and below a real redraw (>= 20). It doubles as the
extractor's cross-edition regression test: on the current-art lineage the position extraction
reproduces the shipped set, so a clean run proves the geometry (page location, randoms pitch, block
columns) survives the older editions — building this corpus is what surfaced and hardened those three paths.

Going forward the corpus also grows on its own: on each real re-cut `install.py` parks the outgoing art
of a changed or dropped key as `legacy/deprecated/<disc>/<key>_dep-<year>.webp` (the named diagram only -
the name-erased figure is a derivation, re-creatable, so not archived; year = the new edition's
`fs`/`indoor` source via `tools/legacy_archive.py`), so `legacy.py` is only needed for a full rebuild.
A `/reject`-ed re-cut drops the matching `_dep-` copy; `/upscale <keys>` instead keeps the new card and
drops only its archive (a same-art quality bump that needs no deprecation record).

**Held card.** 4-way `H` (Bow) ships at its 2018 render: the 2022 CR redrew it with thinner strokes,
the 2018 art reads cleaner. This is no longer enforced in code — a re-cut re-proposes the 2022+ redraw,
and `legacy.py` now gives `H` an ordinary cross-edition deprecation record like any other key — so the
2018 render is kept by **rejecting `H` in the review PR** (`/reject H`). Accept the re-cut to adopt a
future redraw.

The corpus is **outdoor only**. The legacy indoor pool is an edition-varying, non-contiguous subset
(2020/2022 carry 20 blocks, omitting 14 and 20; 2023 grew to the full 22), which `usis.py`'s
position-keying mis-maps across editions, and the shipped indoor variants (`13/17/20_indoor`) were
introduced in 2023 rather than changed — so no superseded indoor art exists to archive. The indoor CRs
are kept under `legacy/<year>/indoor.pdf` only as the source-edition record; future indoor changes
are caught by the live extract workflow (`usis.py` → `install.py` diff), not by `legacy.py`.
