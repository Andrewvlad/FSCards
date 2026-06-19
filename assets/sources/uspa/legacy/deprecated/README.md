# Deprecated USPA diagrams + pipeline regression test

This folder holds USPA diagrams that were in a past dive pool but have since been
**changed or removed**, recovered by running the live `tools/uspa-extract` pipeline over
the legacy source editions in `../` (March 2021 → August 2023) and diffing each against
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
  so it located every discipline's pages in all four legacy editions despite the front
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

## Files

`<discipline>/<key>_dep-<YYYY-MM>.webp` - the **named diagram only** (the name-erased figure is a
derivation, re-creatable from the diagram, so not archived). `YYYY-MM` is the edition that
**replaced or dropped** it. The image itself is the last edition it appeared in. The tables and
notes below are the full per-file record (35 entries).

**Ch.9 (FS) - 14 versions:**

| File | Last valid | Deprecated by | Change |
|---|---|---|---|
| 8-way/K | 2022-08 | 2023-08 | Crossbow -> Double Meekers |
| 8-way/14 | 2022-08 | 2023-08 | Accordion/Zippered Opals -> Zippered Opals/Opposed Stairstep |
| 8-way/15 | 2022-08 | 2023-08 | Opal & Zipper -> Zippers/Double Vsens |
| 8-way/21 | 2022-08 | 2023-08 | Stereopod -> Free Bear/Eye |
| 4-way/20 | 2023-08 | 2026-03 | Piver -> Zipper |
| 2-way-mfs/D | 2023-08 | 2026-03 | Sole to Sole -> Thermometer |
| 2-way-mfs/F | 2023-08 | 2026-03 | Totem -> Belgian Waffle |
| 2-way-mfs/11 | 2023-08 | 2026-03 | Mova -> Tickle-Toes |
| 2-way-mfs/14 | 2023-08 | 2026-03 | WindWarp block redrawn |
| 2-way-mfs/M | 2023-08 | 2026-03 | Stairstep (redrawn) -> Caterpillar |
| 2-way-mfs/M | 2021-03 | 2022-03 | Stairstep (original pose) -> Stairstep (redrawn) |
| 2-way-mfs/N | 2021-03 | 2022-03 | original angled-pose art -> standardized top-view |
| 2-way-mfs/O | 2021-03 | 2022-03 | original angled-pose art -> standardized top-view |
| 2-way-mfs/P | 2021-03 | 2022-03 | original angled-pose art -> standardized top-view |

The 2-way-mfs pool was substantially redrawn in March 2022 (angled realistic poses ->
standardized top-view) and revised again in the 2026 redraw; `M` carries two versions.

**Ch.7 (Collegiate) - 21 versions, all 2-way-vfs:**

- **2-way** (blocks 1-15, randoms A-D): **no deprecations** - stable across every edition.
- **2-way-vfs**: a major pool revision. The pool shrank 22 -> 17 keys: randoms **M, N, O, P, Q**
  were dropped at 2023-08 and **L** at 2026-03; randoms **C-K** and blocks **5, 6** were
  redrawn (some more than once - `H`/`K` twice, `J` three times). Each `_dep-<YYYY-MM>` filename
  records the key and the edition that changed or dropped it.
- **6-way-speed**: no deprecations - the pool **grew** 3 -> 5. Star, Snowflake and Dogbone
  are unchanged across every edition; Open Accordion and Opposed Wedge were added in 2026.
  (The extractor now cuts these legacy editions cleanly - see the test result above.)

## Excluded (flagged by diff, not real deprecations)

- **2021-03 crop artifacts** (same diagram + inflated top-row crop, now **fixed** in
  `regular_edges`): 16-way A, 10-way-speed 1, 4-way A-D. A re-run no longer flags these.
- **Visually unchanged** (metric noise on grey/colored fills): 4-way-vfs B (Gulley),
  4-way-vfs J, 2-way-mfs J.
