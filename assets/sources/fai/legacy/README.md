# Legacy FAI ISC Competition Rules editions

FAI ISC FS Competition Rules, 2018 onward, one copy per edition (the current one included -
the parent directory's `fs.pdf`/`indoor.pdf` are just the most recent). Each edition is stored
as the two CRs that carry the image sets, named like the parent directory's sources:

- `fs.pdf` - the FS CR, carrying the 4-way + 8-way (and VFS, not extracted) dive pools
- `indoor.pdf` - the Indoor FS CR, carrying the indoor 8-way pool

```
legacy/2018/   fs.pdf  indoor.pdf
legacy/2020/           indoor.pdf
legacy/2022/   fs.pdf  indoor.pdf
legacy/2023/   fs.pdf  indoor.pdf
legacy/2024/   fs.pdf  indoor.pdf
legacy/2025/   fs.pdf  indoor.pdf
legacy/2026/   fs.pdf  indoor.pdf
```

## Editions

FAI revises the FS CR roughly every other year, so a given edition stands for two
seasons. The editions that exist as distinct dive-pool documents from 2018 on:

| Folder | Notes |
|---|---|
| `2018` | First edition kept. Titles its pool annexes `Addendum <L> - ...`; no indoor 8-way pool yet (added 2020) |
| `2020` | FS CR omitted - see below. Indoor 8-way pool introduced |
| `2022` | Pool annexes carry no `Annex <L>` running title, only `Current ... Pool` |
| `2023` | |
| `2024` | |
| `2025` | Running titles switch to uppercase `ANNEX <L> - ...` |
| `2026` | Current edition, also the parent directory's live extraction source |

The current edition (2026) is kept here too, a copy of the parent directory's `fs.pdf` +
`indoor.pdf` (the live extraction pipeline's input), so the archive holds every edition. There
is no 2019/2021 edition (each ran two seasons), confirmed against the FAI ISC document archive
and the Internet Archive.

New editions are added by year as they arrive. The `deprecated/` diagram corpus now also grows
automatically: `install.py` parks the old art of every changed key as `<key>_dep-<year>.webp`
on each re-cut (`tools/legacy_archive.py`), so re-running `legacy.py` is only for a full rebuild.
PDF archiving is by hand or via the future source-fetch watcher (deferred) - the helper does it
in one line: `python3 tools/legacy_archive.py archive-pdf assets/sources/fai/fs.pdf assets/sources/fai/legacy`.

## How these were made

The CRs were downloaded from fai.org (`/page/competition-rules-section-5`). The site
serves the PDFs but puts a Cloudflare challenge on its HTML, so the listing is not
script-fetchable - the files were pulled through a real browser session. FAI keeps
every past edition live at its original URL, so no Internet Archive snapshot was
needed except for one gap below. Each PDF is the final published revision of its
edition (where FAI posted a mid-year `-2`/`_v2`, that one).

**The 2020 FS CR is omitted.** Its live URL (`.../documents/2020_isc_cr_fsvfs.pdf`)
is gone (404), and the only Internet Archive capture was made by Common Crawl, which
truncates payloads at 1 MiB - the archived copy is a corrupt 1 MiB fragment of the
real 6.9 MB file (its own `x-crawler-content-length` header records the true size).
No complete copy survives anywhere reachable. The 2020 FS 4-way/8-way pools are
bracketed by the 2018 and 2022 editions that are kept, so the deprecation analysis
loses no coverage it could otherwise have had. The 2020 *indoor* CR is intact and kept.

## Pipeline input - unlike USPA's legacy

The FAI dive-pool art is the same solid-black filled style across every edition
2018-2026 (no separate drawing era to special-case, unlike USPA's pre-2026 realistic
poses), so `tools/fai-extract` cuts these editions cleanly. `tools/fai-extract/legacy.py`
runs the live extractor over them to build the deprecated-image corpus in
`deprecated/` and doubles as the extractor's cross-edition regression test - see that
folder's README and the tool's README.

The corpus is built from the **outdoor** FS CRs (4-way + 8-way) only. The `indoor.pdf`
editions are kept here as the source-edition record but are **not** extracted into the
corpus: the indoor 8-way pool is an edition-varying, non-contiguous subset (the 2020 and
2022 editions carry 20 blocks, omitting 14 and 20; 2023 grew it to the full 22), which the
extractor's position-keying cannot map across editions, and the shipped indoor variants
(`13/17/20_indoor`) were introduced in the 2023 edition rather than changed - so there is no
superseded indoor art to archive. The deprecated folder's README has the full analysis.
