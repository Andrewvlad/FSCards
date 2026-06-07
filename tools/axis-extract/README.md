# axis-extract

Re-cuts the `Axis` image sets under `assets/diagrams/<discipline>/Axis/` from the
AXIS Flight School dive-pool PDFs, committed under `assets/sources/axis/`
(originally axisflightschool.com → Draw Generator → dive pools and competition
rules — re-download from there only to pick up an AXIS pool revision):

| file             | AXIS dive pool                                                | sets / keys                                    |
|------------------|---------------------------------------------------------------|------------------------------------------------|
| `fs4.pdf`        | FS 4-Way (FAI-ISC + USPA)                                     | 4-way A–Q, 1–22                                |
| `fs8.pdf`        | FS 8-Way (FAI-ISC — byte-identical cards to the USPA variant) | 8-way A–Q, 1–22                                |
| `fs8_indoor.pdf` | Indoor FS 8-Way (FAI-ISC)                                     | 8-way 13/17/20`_indoor` + `starting-formation` |
| `fs10.pdf`       | FS 10-Way (USPA)                                              | 10-way-speed 1–12                              |
| `fs16.pdf`       | FS 16-Way (USPA)                                              | 16-way A–J, 1–12                               |
| `vfs2.pdf`       | VFS 2-Way (USPA) Collegiate                                   | 2-way-vfs A–R, 1–6                             |
| `vfs4.pdf`       | VFS 4-Way **(FAI-ISC version)**                               | 4-way-vfs A–Q, 1–22                            |
| `mfs2.pdf`       | MFS 2-Way (USPA)                                              | 2-way-mfs A–Q, 1–22                            |
| `fs2.pdf`        | FS 2-Way (USPA) Collegiate                                    | 2-way A–D, 1–15                                |
| `cf2.pdf`        | CF 2-Way (FAI-ISC)                                            | 2-way-cf A–F                                   |
| `cf4.pdf`        | CF 4-Way (FAI-ISC)                                            | 4-way-cf A–N, 1–14                             |

Use the FAI-ISC VFS pool, not the USPA one: the USPA variant bakes a YouTube
badge *into block 12's inter art* (the FAI card is the revised clean one).

Run `python3 extract.py` (staging lands in `/tmp/axis_out/`, arguments are
changed source basenames like `fs2.pdf` and limit the run to their
disciplines, no arguments = every PDF), then `python3 install.py` to sync
`assets/diagrams/<d>/Axis/` against the staging (installs pixel-changed
cards, deletes keys that left the pool, skips re-encode byte noise, pins
hand mends). The `extract-axis-images` workflow runs this chain plus
`tools/panel-cuts/measure.py` on every AXIS source-PDF change on main and
opens a PR for eyeball review.

## How it works

The PDFs are mPDF output that embed each card as one flate-compressed raster —
300×300 for randoms, 300×900 for blocks (3 panels, divider lines baked in). The
key, name, INTER, rotation labels and © AXIS tag are all baked into that raster;
only the thin cell border around it is PDF-drawn. So the embedded image **is**
the full native-resolution card content "just inside the border" — extracted
losslessly with `pdfimages`, never resampled (the old 856px set was a ~2.85×
bilinear page-render upscale of these same rasters). Cards carry no text
layer, but every card bakes its pool key top-left in one consistent generator
font, so embeds are keyed by matching that glyph crop against templates
harvested from the installed verified sets (4-way's derived `R` and the
unkeyed `starting-formation` excluded as templates). The pipeline is
embed-driven: a pool revision's new keys stage themselves, art revisions land
under their stable key, and keys missing from the staging are pool drops that
`install.py` deletes (refused wholesale when the staging holds under half the
installed set). A low-margin key match prints a `CHECK` line, verify it by
eye.

- **Badges**: 8-way and 16-way blocks plus every VFS block but 12 carry a baked
  "video courtesy of …" YouTube badge, pasted over the inter/end divider.
  `remove_badges` finds the play button (solid bright red + white triangle; the
  suits' red is darker), floods the box's white interior to get its bounds,
  whites the box, and repaints the divider across the gap from its surviving
  profile. Art the box was baked over is unrecoverable in the source; fragments
  poking out survive, as in the previously-shipped set.
- **4-way `R`/Bundy**: not in any AXIS pool — the AXIS CISM pool's R is
  *Caterpillar*, in a different outline art style — so `derive_R` rebuilds it
  from block 12's entry panel (crop above the first divider, '12' key swapped
  for a drawn Liberation-Sans-Bold 'R', as in the old 856px derivation). R
  being a random, the block iconage goes too: blocks suit a reference pair in
  red (239,0,0) / blue (0,176,240) to track across panels while randoms are
  all greyscale, so the tint is un-mixed per pixel keeping the black-ink
  alpha — flat fill to the white suit, black-line AA to the grey ramp,
  white-edge AA back to white.
- **`figures/`**: geometric, component-precise erase — the top-left key and each
  panel's bottom centred name line only (plus the wrapped first line directly
  above it when one exists, recognised by text-tight leading and matching glyph
  height: 8-way 22 'Compressed / Stairstep Diamond'), keeping the © AXIS tag,
  dividers, rotation arrows/labels, instructional notes (VFS block 2),
  annotations ('foot grip', 'must use same arm' — they float higher and smaller
  than a wrap) and all art. Solid black components only (grey/coloured art never
  qualifies); a black comp attached to a mostly-grey ink region is anti-alias of
  art, not a glyph, and is preserved — but one that lines up with the erased name
  is a glyph touching art ('Ritz', whose z meets a leg) and is reclaimed. The
  divider rows are masked out of the component pass so a descender touching a
  divider ('Jelly Roll' J/y, 'Opposed Stairstep' pp) can't merge into a
  full-width structural comp and evade the erase; i-dot-like detached fragments
  are absorbed into their line's band before clustering, or they derail the wrap
  pass. Erased glyphs take a ≤2px anti-alias ring along, never surviving ink.
- **Hand mend — CF 4-way `figures/H`**: in the source card the 'O' of the
  bottom-centred name 'Step Off' overlaps the bottom canopy's triangle tip, so
  the erase pass spares the glyph (touching art) and the tip itself is occluded
  in the source raster. The shipped figure carries a hand graft: the 'O' erased
  and the tip rebuilt from `figures/K`'s clean free-hanging bottom tip (same
  canopy stamp, same orientation; aligned by line-fit, darkest-wins blend at
  the seam). Re-running the pipeline on CF4 would regress it. The named
  `H.webp` keeps its overlap — the name belongs there.
- **Source quirks**: `fs8_indoor.pdf`'s randoms page carries 16 randoms plus two
  byte-identical `starting-formation` cards; `cf2.pdf` embeds every card twice
  (byte-identical pairs). `vfs2.pdf` bakes a camera-POV dart symbol (explained
  by its page-3 legend) onto every panel, kept like any annotation.
