# uspa-extract

Re-cuts the FS-outline (`USPA`) image sets under `assets/diagrams/<discipline>/USPA/`
from the official USPA Skydiver's Competition Manual chapter PDFs (vector), committed
under `assets/sources/uspa/` and kept current by `fetch_uspa.py` (see "Fetching the
source PDFs" below):

| script | source PDF | sets |
|---|---|---|
| `driver_ch9.py` | Ch.9 "Formation Skydiving" — `fs.pdf` | 4-way, 8-way, 10-way-speed, 16-way, 4-way-vfs, 2-way-mfs |
| `driver_ch7.py` | Ch.7 "Collegiate" — `collegiate.pdf` | 2-way (blocks + randoms-page split, see below), 2-way-vfs |
| `p16fix.py` | Ch.7 | 2-way randoms A–D (1×4 table, too short for the grid detector) |
| `extract6.py --extract` | Ch.7 | 6-way-speed |

`extract.py` is the workflow entry point: given the changed source basename(s) it runs the
right cutters in order; `install.py` then installs the staging (next section), and the shared
`tools/validate_ordering.py` cross-checks the result (below). `find_pages.py` is the page
locator they all share, and `canvas.py` pads each cut set to one size before it stages
("One canvas per set" below).

**Ordering cross-check (`tools/validate_ordering.py`).** Shared across all extract pipelines
(Axis as well as USPA), run as a post-install step in each workflow so it sees exactly the
sets the PR proposes. It asserts the fixed pool ordering every source follows: randoms run
contiguously `A..` (FS skips `I` as never used and easily misread, CF disciplines use it),
blocks/formations run contiguously `1..N`. This catches a mis-cut key or a reordered edition
the per-driver `missing`/`extra` set-diff can't - it validates the key SET, not physical
order, so the CISM split-out `M` never trips it, and CISM's extra `R` needs no special case
(in the skip-`I` alphabet `R` is just the letter after `Q`, so 4-way's `A..R` is contiguous).
Non-pool files (8-way `*_indoor` / `starting-formation*`, the `solo` base figure) are ignored.
Warnings print as `[ordering]` lines into the review PR body, never blocking the cut (the PR is
for eyeballing anyway). Standalone: `python3 tools/validate_ordering.py` checks every shipped
set, `python3 tools/validate_ordering.py 4-way 8-way` only the named disciplines.

**Pages are located per edition, never hardcoded.** `find_pages.py` reads each diagram page's
running header ("Appendix C: FS 4-Way Block Sequences", "Appendix F: VFS 2-Way Random
Formations", …) and returns a discipline's randoms/block pages keyed on style + way-count +
section. This is the one thing that must survive the years: SCM front matter shifts the
appendix pages every revision (Ch.9 has run 34–41 pages, Ch.7 19–26), and the appendix LETTER
drifts too (a symbols appendix inserted in 2026 pushed MFS from L/M to M/N; Collegiate swapped
its 4-way/MFS pages for 6-way-speed/VFS-2 between 2017 and 2026) — only the style+way+section
text holds steady, so that is the key, ToC lines (dot leaders) and rules-body mentions (no
"Appendix") rejected. Verified to locate every discipline across all Wayback editions
2015→2026 — page location is the cross-year-critical part and is robust across all of them.

The **crop geometry** targets the current edition's layout: one unified USPA outline set in a
continuous touching-cell grid (shared borders, full-span grid lines), which `detect_grid` (and
`extract6` for 6-way speed) key on by scanning the whole page for its border lines - no
hardcoded page positions or cell counts, so a revision that shifts the grid down the page or
changes a discipline's formation count still cuts (6-way speed grew 3 -> 5 formations across
2023 -> 2026, no code change), and it is page-relative so it follows render size within that
family. It is **not** built for the pre-2026 editions, which are a heterogeneous mix of legacy
art generations — 2017 4-way randoms are filled-black silhouettes in separated boxes with gaps,
2017 8-way is Ted Wagner's colored "PrintPool" in a different grid — none of which is the
shipped outline style. The 2026 SCM redrew every pool into the one outline set; current and
future editions descend from that, so the detector targets the right thing. (To re-cut a legacy
edition you would add a separated-box detection mode, the p16fix band approach generalized;
left undone deliberately since that art is not shipped.) Pages render at 600 DPI; renders/text
are cached under per-chapter `/tmp/fsx_ch*` prefixes (same page numbers exist in both chapters
— a shared cache would silently serve the wrong render).

One header wart handled by hand: the 2026 Collegiate 2-way randoms page prints no appendix
subtitle, so `p16fix.py` falls back to the page right after the 2-way block run. (Single
"…Formations" pages with no Block/Random word — 10-way, 6-way speed, VFS-2 blocks — are
routed to the right cutter by the driver's per-discipline layout flag, since the header can't
tell a one-panel formation from a 3-panel block.)

Staging lands in `/tmp/fsx_out/ch9|ch7/<discipline>/`; `install.py` copies it over
`assets/diagrams/<discipline>/USPA/` **pixel-aware** (twin of axis-extract's): a card is
replaced only when its decoded pixels move past `RECUT_TOLERANCE`, so a re-encode's byte drift
or a re-exported vector's anti-alias jitter never floods the diff with phantom re-cuts, while a
real ink edit (255 delta) always installs. Repo keys absent from staging are pool drops and
get deleted, refused wholesale when staging holds under half the set (botched-run guard).
`install.py` exempts 4-way `R`/Bundy from the orphan sweep so a routine re-run keeps it: it is
CISM-only, absent from the SCM, never extracted, so without the exemption its committed pair would
be dropped as an orphan (`rkey.py` is the one-time key-reposition already applied to that pair, art
untouched, self-noops if re-run). Every card that IS in the source — including 8-way `D`/Hope
Diamond's graft (below) — re-proposes on each re-cut and is kept by rejecting it in the review PR,
not by code.

**One canvas per set (`canvas.py`).** Every cutter hands its cells to `canvas.fit` before
staging, so a set's randoms, and its blocks or formations, all stage at one size. Raw crops
differ by a few pixels: the SCM template's first table row runs short at the top, a block
page's lower table can carry a taller middle panel, and render rounding (Ch.9's 1100px resize
turns its 1108/1109px native widths into a pixel or two of height). Randoms and formations pad
white rows at the top, keeping every name the same distance above its bottom rule, and blocks
pad in the white gap at the top of each panel, so both dividers sit on the same rows in every
block (aligned on each divider's first core row) and `tools/panel-cuts/measure.py` ships one
shared tuple per set. Ch.9 pads after the resize, so no art pixel changes, and a Ch.7 crop that
a column's sub-pixel phase leaves a pixel narrow pads evenly on both sides.

The canvas is each table row's most common size, the largest row winning, never below what
the set already ships at. Cutting every legacy edition, plus sub-pixel page shifts of the
current one, showed rows moving as a unit, so this grow-only ratchet keeps an edition's
phase from resizing a set back and forth. A card that outgrows its row still grows the
canvas, and gets a `[canvas]` line in the review PR, as does every canvas that moves.
`extract.py --reset-canvas` (by hand only) drops the shipped floor, for an edition that
tightens its tables. It leaves `R` at its old height, so trim `R`'s top rows by hand after
one. A change that is only canvas padding installs without a `deprecated/` copy,
`install.py` pads the cards it keeps (`R`) to a grown canvas, and the reject workflow pads
the cards a `/reject` restores (`D`) the same way.

**Never re-install 8-way `D`/Hope Diamond without re-applying its feet.** The
bottom jumper's feet are flat-sliced **in the source art itself** (ink stops
mid-cell, well above the name text - nothing for the crop to recover), so the
shipped `D.webp` + `figures/D.webp` carry a hand graft of C/Hourglass's intact
feet (same template pose, rect `[700:777, 440:660]` copied from C at offset
dy −129 / dx +1, seam verified AA-level identical). The **top** jumper's shoes run
past the cell's top border, and the SCM clips them at the border's top edge (2026:
`498.965 668.054 17.56 24.486 re W n` in page 21's content stream), so a crop's first
row slices them flat. The pair carries their tips in the canvas's top padding:
page 21 re-rendered at 600 DPI with that clip rect raised and the border's stroke
dropped, resized on the shipped grid (Lanczos `box` starting 10 rows above the crop),
and spliced into rows 0-11, cols 460-624 of the 874-row canvas. `install.py` no longer
freezes `D`: a re-cut re-proposes the flat-sliced source `D`, so keep both fixes by
**rejecting `D` in the review PR** (`/reject D`), or re-apply them if a deliberate re-cut
should carry them forward.

Output contract:

- **Named diagrams**: band-edge crops — only border-line pixels (plus anti-alias halo)
  are removed; every interior white pixel survives. (A fixed inset can't do this:
  border thickness varies, and art can hug a thin border — 8-way `P`/Venus, `D`'s
  top feet.) Ch.9 resizes to 1100px wide (lossless webp); Ch.7 keeps native crop size.
  Both then pad with white to the set's canvas.
- **`figures/`**: same crop with the corner key and each panel's bottom name line
  erased glyph-precisely (text-layer bboxes + connected-component preserve), keeping
  rotation/description labels, divider rules, inter arrows, and any art that crosses
  a label.

## Fetching the source PDFs

`fetch_uspa.py` keeps `assets/sources/uspa/fs.pdf` (Ch.9) and `collegiate.pdf`
(Ch.7) current, the way `axis_sources.json` + the Axis workflow do for the Axis
sets. It is **discovery-based, not a pinned URL**: the SCM page (uspa.org/SCM)
serves its chapters from an S3-backed DnnSharp folder through a per-file LinkClick
token the page builds server-side, so there is no stable direct path to pin.

Per run the script resolves each chapter live (stdlib `urllib` only, no deps):

1. GET the SCM page with a browser UA, scrape the DNN antiforgery token, the
   Evotiva module id, the tab id, and the root folder id.
2. Walk the Evotiva file-library API (`GetItemsServices/GetItems`) **by name** -
   root, then the `Individual Chapters` folder, then `SCM_Ch09.pdf` /
   `SCM_Ch07.pdf` (falls back to scanning every folder if that one is renamed).
3. POST the file's `ItemID` to `FileActionsServices/DownloadFileInline`, which
   returns the `LinkClick.aspx?fileticket=...` URL.
4. GET that URL, verify a `%PDF` header, and diff against the committed copy.

Resolving by **name** each run is what makes it future-proof: a yearly edition
swap, a new file id, or a rotated token are all re-discovered, never hardcoded.
(The LinkClick token has in fact stayed stable across editions, verified against
the Internet Archive's history of these URLs, but the script does not rely on it.)

`tools/uspa_sources.json` is the config: committed path to `{folder, file, slug}`.
`.github/workflows/update-uspa-sources.yml` runs the fetcher monthly (and on
dispatch), and opens one PR per changed chapter updating the source PDF, mirroring
the Axis source workflow.

Merging a source-PDF PR triggers `.github/workflows/extract-uspa-images.yml`, which re-cuts
the changed chapter (`extract.py` → `install.py`) and opens a **review** PR carrying an
old-vs-new image table, mirroring the Axis pipeline. It never auto-merges — the cut is for
eyeball review. 4-way `R`/Bundy is the one card kept by code (`install.py` exempts it from the
orphan sweep, since it is absent from the SCM and would otherwise be dropped). 8-way `D`'s graft
is no longer code-held — a re-cut re-proposes the ungrafted source `D`, so veto it (and any other
bad cut) with a `/reject <keys>` comment in that PR (the shared `reject-extracted-images.yml`
covers USPA as well as Axis). A deliberate deeper re-cut still means running `driver_ch9.py` /
`driver_ch7.py` by hand and minding those exceptions.

On a re-cut `install.py` also parks the outgoing art of every changed or dropped key (the named
diagram only) under `assets/sources/uspa/legacy/deprecated/<disc>/<key>_dep-<year>.webp` (year = the
re-cut day), and `update-uspa-sources` archives each fetched edition under
`assets/sources/uspa/legacy/<year>/` (shared `legacy_archive.py`); a `/reject` drops the matching
`_dep-` copy, `/upscale` keeps the card and drops only its archive. See
`assets/sources/uspa/legacy/README.md`.
