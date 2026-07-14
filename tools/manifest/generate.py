#!/usr/bin/env python3
"""Generate per-discipline image-identity manifests for offline update delivery (lane C).

Walks assets/diagrams/<discipline>/<set>/[figures/]<file> (webp + svg, thumbs/ skipped -
thumbnails ride their parent: same pipeline writes both, so a changed parent implies a
changed thumb) and writes assets/diagrams/<discipline>/manifest.json mapping each
discipline-relative path to [sha256-16hex, bytes]. The client compares these hashes to
judge saved-set staleness and sums the byte sizes for the download-size preview, so a
manifest must be regenerated whenever the discipline's images change: the extract
workflows do it per re-cut PR, update-image-manifest.yml backstops hand edits on main.

Args are discipline names (generate.py 4-way 8-way) or explicit image paths (the extract
workflows pass what install.py staged - each path just marks its discipline for a rebuild).
No args rebuilds every discipline.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS = ROOT / "assets" / "diagrams"

THUMB_DIR = "thumbs"
HASH_LEN = 16  # sha256 hex prefix - collision-safe at this corpus size, keeps manifests lean


# Pool order per dir: randoms A-Z, blocks 1-99 (variants like 13_indoor beside their key), extras last
def entry_key(rel):
    if m := re.fullmatch(r"([A-Za-z])(?![A-Za-z])(.*)", rel.stem):
        rank = (0, m[1].upper(), m[2])
    elif m := re.fullmatch(r"(\d+)(.*)", rel.stem):
        rank = (1, int(m[1]), m[2])
    else:
        rank = (2, rel.stem, "")
    return (rel.parts[:-1], *rank)


def build_manifest(discipline):
    entries = {}
    files = [path for path in discipline.rglob("*") if path.suffix in (".webp", ".svg") and THUMB_DIR not in path.parts]
    for path in sorted(files, key=lambda path: entry_key(path.relative_to(discipline))):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:HASH_LEN]
        entries[path.relative_to(discipline).as_posix()] = [digest, path.stat().st_size]
    return entries


def write_manifest(discipline):
    entries = build_manifest(discipline)
    lines = ",\n".join(f'"{k}": {json.dumps(v)}' for k, v in entries.items())
    (discipline / "manifest.json").write_text("{\n" + lines + "\n}\n")
    return len(entries)


def main():
    # Explicit image paths (CI passes the staged keys) map to their disciplines
    names = {a if "/" not in a else Path(a).relative_to("assets/diagrams").parts[0] for a in sys.argv[1:]}

    total = 0
    for discipline in sorted(DIAGRAMS.iterdir()):
        if not discipline.is_dir() or (names and discipline.name not in names):
            continue
        total += write_manifest(discipline)
        print(f"{discipline.name}/manifest.json")
    print(f"{total} images hashed")


if __name__ == "__main__":
    main()
