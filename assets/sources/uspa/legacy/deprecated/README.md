# Deprecated USPA diagrams + pipeline regression test

This folder holds USPA diagrams that were in a past dive pool but have since been
**changed or removed**, recovered by running the live `tools/uspa-extract` pipeline over
the legacy source editions in `../` (March 2021 → October 2025) and diffing each against
the current shipped set. It doubles as a regression test of the extractor: running it on
known past pools shows whether it will cut future editions correctly.

Going forward it also grows on its own: on each real re-cut `install.py` parks the outgoing art
of a changed or dropped key here as `<key>_dep-<year>.webp` (year, the going-forward label - the
hand-built entries below use finer `YYYY-MM`; via `tools/legacy_archive.py`). A `/reject`-ed re-cut
drops the matching `_dep-` copy too.

Covered: **Ch.9 (FS)** - 4-way, 8-way, 10-way-speed, 16-way, 4-way-vfs, 2-way-mfs - and
**Ch.7 (Collegiate)** - 2-way, 2-way-vfs, 6-way-speed.

## Pipeline test result

- **Page location was already robust.** `find_pages.py` reads the appendix running headers,
  so it located every discipline's pages in every legacy edition despite the front
  matter shifting each revision. No discipline was mislocated.
- **Cell crop is pixel-identical from March 2022 onward.** The 2023-08 extraction matches
  the shipped set on every key whose art did not change (mean diff 0.00); 2022 agrees. On
  the current outline-art lineage the extractor reproduces the shipped images exactly.
- **Conclusion.** A future edition that keeps the current outline art now extracts correctly
  even if it shifts the grid's position or changes a discipline's formation count - the
  geometry is found, never assumed. What still needs hand work is a genuinely new ART
  generation (the pre-2026 realistic-pose sets), which is why these legacy editions stay
  archival, not pipeline input. See `tools/uspa-extract/README.md`.

## How a deprecation was decided

Each edition was extracted, then every key's figure was compared to the current shipped
figure with a shift/whitespace/line-tolerant metric (trim full-width/height lines, crop to
the ink bounding box, downscale to 128x128, mean abs diff). Per key the editions form
version runs over time; a run that differs from the current art is a deprecated version.
FS candidates were each confirmed by eye (the metric over-flags the 2021 crop artifact and
colored-VFS fills). 2-way-vfs is black-and-white, so its larger candidate set is reliable;
its removals are factual (the keys are absent from the current pool).

The 2024 and 2025 editions came later. Each was compared cell by cell with the editions on
either side, which dated the changes first credited to 2026-03 and found some the first pass
missed. Those were archived only where a formation or an inter changed.

## Files

`<discipline>/<key>_dep-<YYYY-MM>.webp` - the **named diagram only** (the name-erased figure is a
derivation, re-creatable from the diagram, so not archived). `YYYY-MM` is the edition that
**replaced or dropped** it. The image itself is the last edition it appeared in. The tables and
notes below are the full per-file record (39 entries).

**Ch.9 (FS) - 17 versions:**

| File | Last valid | Deprecated by | Change |
|---|---|---|---|
| 8-way/K | 2022-08 | 2023-08 | Crossbow -> Double Meekers |
| 8-way/14 | 2022-08 | 2023-08 | Accordion/Zippered Opals -> Zippered Opals/Opposed Stairstep |
| 8-way/15 | 2022-08 | 2023-08 | Opal & Zipper -> Zippers/Double Vsens |
| 8-way/21 | 2022-08 | 2023-08 | Stereopod -> Free Bear/Eye |
| 4-way/20 | 2024-07 | 2025-10 | Piver -> Zipper |
| 4-way-vfs/12 | 2024-07 | 2025-10 | Pinwheel inter 540° -> 180°, closing Pinwheel redrawn |
| 2-way-mfs/D | 2024-07 | 2025-10 | Sole to Sole -> Thermometer |
| 2-way-mfs/F | 2024-07 | 2025-10 | Totem -> Belgian Waffle |
| 2-way-mfs/A | 2023-08 | 2024-07 | WindMarp -> MindWarp, lower jumper redrawn |
| 2-way-mfs/6 | 2023-08 | 2024-07 | Gears inter Flip 360° -> All 360°, closing grip moved |
| 2-way-mfs/11 | 2023-08 | 2024-07 | Mova -> Tickle-Toes |
| 2-way-mfs/14 | 2023-08 | 2024-07 | WindWarp block redrawn |
| 2-way-mfs/M | 2023-08 | 2024-07 | Stairstep (redrawn) -> Caterpillar |
| 2-way-mfs/M | 2021-03 | 2022-03 | Stairstep (original pose) -> Stairstep (redrawn) |
| 2-way-mfs/N | 2021-03 | 2022-03 | original angled-pose art -> standardized top-view |
| 2-way-mfs/O | 2021-03 | 2022-03 | original angled-pose art -> standardized top-view |
| 2-way-mfs/P | 2021-03 | 2022-03 | original angled-pose art -> standardized top-view |

The 2-way-mfs pool was substantially redrawn in March 2022 (angled realistic poses ->
standardized top-view) and revised again in July 2024 and October 2025. `M` carries two versions.

**Ch.7 (Collegiate) - 22 versions:**

- **2-way** (blocks 1-15, randoms A-D): one version. Block **13** became Turnstile at 2025-06,
  renamed from Line with one jumper's inter turn reversed. The rest is stable across every edition.
- **2-way-vfs**: a major pool revision. The pool shrank 22 -> 17 keys: randoms **M, N, O, P, Q**
  were dropped at 2023-08 and **L** at 2024-04. Randoms **C-K** and blocks **5, 6** were
  redrawn (some more than once - `H`/`K` twice, `J` three times). Each `_dep-<YYYY-MM>` filename
  records the key and the edition that changed or dropped it.
- **6-way-speed**: no deprecations - the pool **grew** 3 -> 5. Star, Snowflake and Dogbone
  are unchanged across every edition. Open Accordion and Opposed Wedge were added in 2024-04.
  (The extractor now cuts these legacy editions cleanly - see the test result above.)

## Excluded (flagged by diff, not real deprecations)

- **2021-03 crop artifacts** (same diagram + inflated top-row crop, now **fixed** in
  `regular_edges`): 16-way A, 10-way-speed 1, 4-way A-D. A re-run no longer flags these.
- **Visually unchanged** (metric noise on gray/colored fills): 4-way-vfs B (Gulley),
  4-way-vfs J, 2-way-mfs J.
- **Marker, label, symbol or shading only**: 2-way-mfs 13 (2024-07, inter labels added and its
  jumpers darkened), 4-way 2 (2025-10, a dot marks one jumper), 4-way-vfs 2 (2025-10, a square
  marker added and feet redrawn), 2-way-mfs 3 (2025-10, the inter's two helmet shades swapped),
  2-way-mfs M (2025-10, Caterpillar gains its orientation symbol).
