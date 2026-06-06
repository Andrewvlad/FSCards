# tools

*The code in this directory is predominantly AI-generated.
Reuse with caution.*

The image-set extraction pipelines. Each subdirectory produces one family of
committed image sets under `assets/diagrams/` from the source PDFs committed
under `assets/sources/`, so a re-run needs no downloads. **Each tool's own
README is the authoritative source/crop/erase contract for its sets** — read
it before touching those assets or re-running a pipeline.

| tool           | produces                                                                                                                                     | from                   |
|----------------|----------------------------------------------------------------------------------------------------------------------------------------------|------------------------|
| `uspa-extract` | the FS-outline `USPA` sets — SCM Ch.9 (4-way, 8-way, 10-way-speed, 16-way, VFS 4-way, MFS) + Ch.7 Collegiate (2-way, VFS 2-way, 6-way-speed) | `assets/sources/uspa/` |
| `axis-extract` | the `Axis` sets (all nine disciplines)                                                                                                       | `assets/sources/axis/` |
| `fai-extract`  | the `FAI` sets (incl. 8-way's USIS-cut indoor cards)                                                                                         | `assets/sources/fai/`  |
| `cf-vectorize` | the CF-outline `USPA` SVG sets (CF 2-way, CF 4-way)                                                                                          | `assets/sources/cf/`   |

All four are Python (numpy/Pillow, plus scipy for the raster pipelines and
potrace/cairosvg for the vectorizer). Staging lands under `/tmp`; install is a
copy over `assets/diagrams/` — but see each README first for the hand-managed
exceptions a blind re-run would regress (4-way `R`/Bundy, 8-way `D`'s foot
graft, the CF4 canopy re-stamp).
