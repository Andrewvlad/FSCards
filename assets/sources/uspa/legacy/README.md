# Legacy USPA SCM editions

USPA Skydiver's Competition Manual dive-pool chapters, March 2021 onward, one copy per edition
(the current one included - the parent directory's `fs.pdf`/`collegiate.pdf` are just the most
recent). Each edition is stored as the two chapters that carry the image sets:

- `fs.pdf` - Ch.9, the FS dive pool (4-way, 8-way, 10-way speed, 16-way, VFS 4-way, MFS 2-way)
- `collegiate.pdf` - Ch.7, the Collegiate dive pool (2-way, VFS 2-way, 6-way speed)

```
legacy/2021/          fs.pdf  collegiate.pdf
legacy/2022/March/    fs.pdf  collegiate.pdf
legacy/2022/August/   fs.pdf  collegiate.pdf
legacy/2023/          fs.pdf  collegiate.pdf
legacy/2026/          fs.pdf  collegiate.pdf
```

The archive labels each edition by the **year** of its PDF's CreationDate - the granularity the
watcher uses, robust to the InDesign export date sliding a month off the manual's stated month.
A year with one edition is a plain `<year>/` folder; a year that saw more than one revision nests
each edition under its month name (`<year>/March/`, `<year>/August/`) - so far only 2022.

## Editions

| Folder | Manual date | Notes |
|---|---|---|
| `2021` | March 2021 | Last edition with per-chapter footer dates (Ch.9 and Ch.7 both March 2021) |
| `2022/March` | March 2022 | Footer redesigned to one manual-wide date, per-chapter `9-N` page numbering dropped |
| `2022/August` | August 2022 | |
| `2023` | August 2023 | Last edition before the March 2026 redraw |
| `2026` | March 2026 | The outline redraw; current, also the parent directory's live source |

The current edition (2026) is kept here too, a copy of the parent directory's `fs.pdf` +
`collegiate.pdf` (the live extraction pipeline's input), so the archive holds every edition.

There is no 2024 or 2025 edition. The USPA Archives folder jumps from August 2023
straight to the current edition, and the Internet Archive holds no SCM capture in
that window, so August 2023 was current until March 2026.

## Auto-archiving

`update-uspa-sources.yml` now archives each fetched edition here as it replaces the working copy
(`tools/legacy_archive.py archive-pdf`), so future editions land automatically. And on a merged
SCM revision, `install.py` parks the old art of every changed key under
`deprecated/<discipline>/<key>_dep-<year>.webp` (+ `figures/`), labeled by the new edition's
year (the four hand-built deprecations there used finer `YYYY-MM`); a `/reject`-ed re-cut drops
its `_dep-` copy too. So the deprecated corpus grows on its own.

## How these were made

Recent editions are published only as one combined manual (USPA dropped the
per-chapter `Portals/0/files/SCM_chNN.pdf` downloads after the 2019 edition, and
the current chapters are served through a per-file LinkClick token the Internet
Archive never captures). The full manuals were pulled from the live USPA Evotiva
file library's `Archives` folder (uspa.org/SCM), reached by the same name-based
API walk `tools/uspa-extract/fetch_uspa.py` uses for the current chapters. The
folder keeps one canonical copy per edition, named by revision date, so no
Internet Archive snapshot dedup was needed.

Ch.9 and Ch.7 were then sliced out of each full manual losslessly (pypdf
object-copy, no re-render, verified pixel-identical to the source). Chapter
ranges were located by heading and section-divider, not hardcoded page numbers,
the same robustness `find_pages.py` relies on. Each chapter keeps its leading
section-divider tab page, matching the parent-directory chapter PDFs. Slicing
drops the manual's other twelve chapters but barely shrinks the bytes (105 MB
versus 119 MB of full manuals) because the dive-pool diagrams are most of each
manual's weight, and that is the content being kept.

## Not pipeline input

Archival only. The `tools/uspa-extract` crop geometry targets the current
edition's unified outline grid and does not handle pre-2026 art (see that tool's
README). The 2026 SCM redrew every pool into the shipped outline set, so cutting
image sets from these editions would need new legacy-art detection modes, left
undone deliberately. Pre-2021 editions (2016 through 2020) also exist in the same
Archives folder and the Internet Archive but are outside this set's scope.
