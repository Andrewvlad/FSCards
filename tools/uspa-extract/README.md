# uspa-extract

Re-cuts the FS-outline (`USPA`) image sets under `assets/diagrams/<discipline>/USPA/`
from the official USPA Skydiver's Competition Manual chapter PDFs (vector), committed
under `assets/sources/uspa/` (originally https://uspa.org/scm — re-download only to
pick up an SCM revision):

| script | source PDF | sets |
|---|---|---|
| `driver_ch9.py` | Ch.9 "Formation Skydiving" — `scm_fs.pdf` | 4-way, 8-way, 10-way, 16-way, 4-way-vfs, 2-way-mfs |
| `driver_ch7.py` | Ch.7 "Collegiate" — `scm_ch07.pdf` | 2-way (blocks + randoms-page split, see below), 2-way-vfs |
| `p16fix.py` | Ch.7 p16 | 2-way randoms A–D (1×4 table, too short for the grid detector) |
| `extract6.py --extract` | Ch.7 p17 | 6-way |

Printed appendix labels are PDF page − 2. Pages render at 600 DPI; renders/text are
cached under per-chapter `/tmp/fsx_ch*` prefixes (same page numbers exist in both
chapters — a shared cache would silently serve the wrong render). The June-2025 and
March-2026 SCM revisions render the Ch.7 pages pixel-identically.

Staging lands in `/tmp/fsx_out/`; install by copying staged files over
`assets/diagrams/<discipline>/USPA/`. **Never overwrite 4-way `R`/Bundy** — it is
CISM-only, absent from the SCM, and never extracted, so a plain copy is safe.
Its prior-pair key sat up-left of every SCM-cut sibling; `rkey.py` translated
the glyph (art untouched) to the siblings' measured key geometry and self-noops
if re-run.

**Never re-install 8-way `D`/Hope Diamond without re-applying its graft.** The
bottom jumper's feet are flat-sliced **in the source art itself** (ink stops
mid-cell, well above the name text — nothing for the crop to recover), so the
shipped `D.webp` + `figures/D.webp` carry a hand graft of C/Hourglass's intact
feet (same template pose; rect `[690:767, 440:660]` copied from C at offset
dy −129 / dx +1, seam verified AA-level identical). The **top** jumper's feet sit
exactly ON the cell border (zero ink above the line); the band-edge crop keeps
them automatically — the old fixed-inset crop amputated them, which is why `D`
once needed a hand-healed "skip D" rule. No skip is needed now, only the graft.

Output contract:

- **Named diagrams**: band-edge crops — only border-line pixels (plus anti-alias halo)
  are removed; every interior white pixel survives. (A fixed inset can't do this:
  border thickness varies, and art can hug a thin border — 8-way `P`/Venus, `D`'s
  top feet.) Ch.9 resizes to 1100px wide (lossless webp); Ch.7 keeps native crop size.
- **`figures/`**: same crop with the corner key and each panel's bottom name line
  erased glyph-precisely (text-layer bboxes + connected-component preserve), keeping
  rotation/description labels, divider rules, inter arrows, and any art that crosses
  a label.
