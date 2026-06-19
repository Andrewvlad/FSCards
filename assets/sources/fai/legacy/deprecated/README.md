# Deprecated FAI diagrams + pipeline regression test

This folder holds FAI ISC diagrams that were in a past dive pool but have since been
**changed**, recovered by running the live `tools/fai-extract` pipeline over the legacy
source editions in `../` (2018 through 2025) and diffing each against the current shipped
set. It doubles as a regression test of the extractor: running it on known past pools
shows whether it will cut future editions correctly.

Going forward it also grows on its own: on each real re-cut `install.py` parks the outgoing art
of a changed or dropped key here as `<key>_dep-<year>.webp` (year = the new edition's source PDF,
via `tools/legacy_archive.py`), so a full `legacy.py` rebuild is only needed to re-derive the whole
corpus from the archived editions. A `/reject`-ed re-cut drops the matching `_dep-` copy too.

Covered: the **outdoor** FS pools, **4-way** and **8-way**. Indoor 8-way is excluded - see
the bottom of this file.

## Pipeline test result

- **Page location is robust.** `locate()` reads the appendix running titles (keying on the
  stable `... FORMATION SKYDIVING <N>-WAY <BLOCK|RANDOM> POOL` core, since the annex prefix
  drifts `Addendum` / none / `ANNEX` across editions), so it found every pool page in all five
  FS editions despite the front matter and annex letters shifting each revision.
- **Cell crop reproduces the shipped set exactly.** The 2025 edition (current art lineage)
  extracts to a figure distance of **0.0** from the shipped set on every key, and 2022-2024
  differ only on keys whose art actually changed. The geometry is found, never assumed.
- **Conclusion.** A future edition that keeps the current art now extracts correctly even if
  it shifts the grid or changes a discipline's formation count. Building this corpus is what
  surfaced and hardened the three edition-fragile paths: the running-title page location, the
  randoms **row pitch** (older editions' cells are not square, so the pitch is read from the
  horizontal grid lines, not the column width), and the block **columns** (older grids share
  cell borders, newer ones gutter them, so columns step one border at a time). See
  `tools/fai-extract/README.md`.

## How a deprecation was decided

Each edition was extracted, then every key's **name-erased figure** was compared to the
current shipped figure with a shift / scale / whitespace-tolerant metric (crop to the ink
bounding box, downscale to 128x128, mean abs diff). Per key the editions form version runs
over time; a run that differs from the current art is a deprecated version, written here as
its last-appearing edition.

The figure (art only), not the named diagram, is the signal: it ignores a baked **name-text**
edit, so a spelling or font fix (4-way `F` "Open Acordian" -> "Open Accordion", 8-way `O`) is
not mistaken for an art change. The threshold (figure distance >= 16) sits in a wide gap -
unchanged art drifts to ~10-14 from name-erase pixel noise, a real redraw or formation swap
moves >= 20 - so neither the noise nor the name fixes are archived. See the excluded list below.

## Files

`<discipline>/<key>_dep-<YYYY>.webp` - the **named diagram only** (the name-erased figure is a
derivation, re-creatable from the diagram, so not archived). `YYYY` is the edition that
**replaced** it; the image itself is the last edition it appeared in. The tables below are the
full per-file record (8 entries).

**4-way - 4 versions:**

| File | Last valid | Deprecated by | Change |
|---|---|---|---|
| 4-way/1 | 2018 | 2022 | Snowflake -> Molar |
| 4-way/13 | 2018 | 2022 | Offset/Spinner -> Mixed Accordion |
| 4-way/E | 2018 | 2022 | Meeker, redrawn |
| 4-way/20 | 2024 | 2025 | Piver -> Zipper |

**8-way - 4 versions:**

| File | Last valid | Deprecated by | Change |
|---|---|---|---|
| 8-way/K | 2022 | 2023 | Crossbow -> Double Meekers |
| 8-way/14 | 2022 | 2023 | Accordion/Opposed Stairstep -> Zippered Opals |
| 8-way/15 | 2022 | 2023 | Opal & Zipper -> Zippers/Double Yuans |
| 8-way/21 | 2022 | 2023 | Stereopod -> Free Bear/Eye |

The 2023 edition reworked the 8-way block pool (`K`/`14`/`15`/`21`). FAI ISC is the standard
the USPA SCM tracks, so these match the USPA set's own 2023-08 8-way revision (`K` Crossbow ->
Double Meekers, `21` Stereopod -> Free Bear/Eye) at the same boundary - see the USPA deprecated
folder. The 4-way `1`/`13`/`E` changes predate USPA's kept editions (2021+), so they have
no USPA counterpart.

## Held - shipped against the source

- **4-way `H` / Bow.** The 2022 edition redrew Bow with thinner strokes; the 2018 render reads
  cleaner, so the shipped card is **held at the 2018 art** and `H` carries no deprecation record.
  `install.py` PROTECTs `H` (+ its figure) and `legacy.py` excludes it (`HELD`), so a re-cut or a
  full corpus rebuild never restages the 2022+ redraw. To adopt a future redraw, drop `H` from both.

## Excluded (flagged by the raw diff, not real art deprecations)

- **Name-erase pixel noise** (art unchanged, figure distance 10-14, below the threshold):
  4-way `O` (Satellite), 4-way `3` (Side Flake Opal / Turf), 4-way `22` (Tee / Chinese Tee),
  8-way `E` (Rubik). The named diagrams are unchanged across editions.
- **Name-text only** (the art is identical, the baked name changed): 4-way `F`
  (Open Acordian -> Open Accordion spelling fix) and 8-way `O`.

## Indoor 8-way - excluded

The indoor 8-way pool is **not** in this corpus. Unlike the stable contiguous outdoor pool,
the indoor pool is an edition-varying, non-contiguous **subset**: the 2020 and 2022 Indoor CRs
carry 20 blocks (omitting 14 and 20), and 2023 grew it to the full 22. `usis.py` keys cells by
grid position - correct only for the current full pool, it mis-maps the legacy subset (in the
2022 grid, position 17 holds the baked-18 cell). It is also moot: the shipped indoor variants
(`13/17/20_indoor`) were **introduced**, not changed. Shape-matching every edition's indoor
cells against the correctly-keyed outdoor pool shows `13_indoor` tracks the outdoor card and is
stable throughout, while `17_indoor` and `20_indoor` first diverge from the outdoor card only in
the 2023 edition. So there is no superseded indoor art to archive. The legacy `indoor.pdf`
editions are kept in `../<year>/` as the source-edition record, and future indoor changes are
caught by the live extract workflow (`usis.py` -> `install.py` diff), not here.
