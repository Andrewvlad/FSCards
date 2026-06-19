# Legacy Axis dive-pool PDFs

Every edition of the AXIS Draw Generator dive-pool PDFs (the sources behind the Axis image
sets), one copy per edition. Unlike FAI/USPA there is no separate current-vs-old split: each
PDF is archived here when it is fetched, and the working copy in `../` is just the most recent.

Layout is `legacy/<year>/<name>.pdf`, where `<year>` is the PDF's own revision year read from
its embedded CreationDate (the generator stamps one - the year, not the month, so the label is
stable). A year that saw more than one revision nests each edition under its month name
(`<year>/<Month>/`), so no edition is ever overwritten.

```
legacy/2023/   cf2  cf4  fs8  fs8_indoor  fs10  fs16
legacy/2025/   fs4  mfs2  vfs4
legacy/2026/   fs2  fs4_cism  vfs2
```

## How they get here

`.github/workflows/update-axis-sources.yml` fetches the pinned PDFs monthly
(`tools/axis_sources.json`); when one changed it opens an update PR that both replaces
`../<name>.pdf` and drops a dated copy here, via `tools/legacy_archive.py archive-pdf`. The
dozen current editions above were backfilled with the same helper.

## deprecated/

When a merged PDF revision runs `extract-axis-images.yml`, `install.py` copies the OLD diagram
of every changed or dropped key to `deprecated/<discipline>/<key>_dep-<year>.webp` (+ its
`figures/` sibling), labeled by the **new** edition's year (the one that replaced it), matching
the FAI/USPA deprecated-corpus naming. So superseded art is preserved as the pool evolves. The
folder is created on the first real re-cut (absent until then). A `/reject`-ed re-cut drops the
matching `_dep-` copy too (`reject-extracted-images.yml`), so a kept card leaves no orphan.

## Not pipeline input

Archival and provenance only. The Axis extractor targets the current generator output; there is
no cross-edition regression test over these (unlike the FAI legacy corpus).
