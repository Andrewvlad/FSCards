#!/usr/bin/env python3
"""Generate low-quality thumbnails for progressive diagram loading.

Walks assets/diagrams/<discipline>/<set>/[figures/]<key>.webp and writes a THUMB_WIDTH-wide
low-quality webp under the set's thumbs/ dir - named thumbs sit directly in thumbs/, figure
thumbs nest in thumbs/figures/. The client derives the path the same way
(assets/diagrams/4-way/USPA/A.webp -> .../USPA/thumbs/A.webp, .../USPA/figures/A.webp ->
.../USPA/thumbs/figures/A.webp), points an <img> at it first, then swaps to the full
diagram on load. Only thumbs for cards actually rendered are ever fetched, so the page
carries no inline weight however large the library grows. Source alpha is preserved, so a
thumb composites onto the card panel exactly like the diagram it stands in for.

SVG sets (CF USPA) are skipped: vector art is already tiny and sharp, no thumbnail needed.
Deprecated/legacy art lives under assets/sources, outside the walk, so it never gets a thumb.

Args are discipline names (generate.py 4-way 8-way - re-render those whole disciplines) or
explicit image paths (generate.py assets/diagrams/4-way/Axis/13.webp - just those images); the
extract workflows pass the exact images install.py staged, so only changed thumbs are written.
A passed path whose source is gone has its thumb dropped. No args rebuilds everything.
Discipline/all runs also prune orphan thumbs whose source image is gone.
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS = ROOT / "assets" / "diagrams"

THUMB_DIR = "thumbs"
THUMB_WIDTH = 128  # Thumbnail width in px - legible across every art style, ~1-3KB encoded
WEBP_QUALITY = 50
WEBP_METHOD = 6  # Slowest/smallest encode - this is a one-shot generator


# Source webps, skipping the thumbs/ output dirs so re-runs don't thumbnail thumbnails
def sources(only):
    for path in DIAGRAMS.rglob("*.webp"):
        if THUMB_DIR in path.parts:
            continue
        if not only or path.relative_to(DIAGRAMS).parts[0] in only:
            yield path


def thumb_path(src):
    # Figure thumbs nest under thumbs/figures/; named thumbs sit directly in thumbs/
    base = src.parent.parent if src.parent.name == "figures" else src.parent
    return base / THUMB_DIR / src.relative_to(base)


def write_thumb(src):
    img = Image.open(src)
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    img = img.convert("RGBA" if has_alpha else "RGB")

    w, h = img.size
    thumb = img.resize((THUMB_WIDTH, max(1, round(h * THUMB_WIDTH / w))), Image.LANCZOS)

    out = thumb_path(src)
    out.parent.mkdir(parents=True, exist_ok=True)
    thumb.save(out, "WEBP", quality=WEBP_QUALITY, method=WEBP_METHOD)


# Drop thumbs whose source image no longer exists
def prune(only):
    removed = 0
    for thumbs in DIAGRAMS.rglob(THUMB_DIR):
        if not thumbs.is_dir():
            continue
        if only and thumbs.relative_to(DIAGRAMS).parts[0] not in only:
            continue
        for thumb in thumbs.rglob("*.webp"):  # named thumbs + the figures/ subdir
            src = Path(*(p for p in thumb.parts if p != THUMB_DIR))
            if not src.exists():
                thumb.unlink()
                removed += 1
    return removed


def main():
    args = sys.argv[1:]
    # Explicit image paths (CI passes the staged keys) vs bare discipline names (manual use)
    paths = [Path(a) for a in args if "/" in a]
    disciplines = {a for a in args if "/" not in a}

    written = removed = 0

    # Whole-discipline rebuild, or everything when no args. A path-only run skips this
    if disciplines or not args:
        for src in sources(disciplines):
            write_thumb(src)
            written += 1
        removed += prune(disciplines)

    # Just the named images - re-render a present one, drop a deleted one's thumb
    for src in paths:
        if src.suffix != ".webp":
            continue  # svg sets have no thumb
        if src.exists():
            write_thumb(src)
            written += 1
        else:
            thumb = thumb_path(src)
            if thumb.exists():
                thumb.unlink()
                removed += 1

    print(f"wrote {written} thumbs ({THUMB_WIDTH}px), pruned {removed} orphans")


if __name__ == "__main__":
    main()
