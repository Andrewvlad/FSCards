# Image-identity manifests

Generates `assets/diagrams/<discipline>/manifest.json`: every shipped diagram, figure, and
svg (thumbs excluded, they ride their parent) mapped to `[sha256-16hex, bytes]`. The offline
machinery is the consumer: hashes decide when a user's downloaded set is stale (update lane C,
see the offline design), byte sizes power the download-size preview, and the app fetches the
manifest network-first so an online client always judges against the deployed truth.

## Usage

```
python3 tools/manifest/generate.py                 # all disciplines
python3 tools/manifest/generate.py 4-way 8-way     # named disciplines
python3 tools/manifest/generate.py assets/diagrams/4-way/Axis/13.webp  # paths mark their discipline
```

## Sync contract

A manifest must be regenerated whenever its discipline's images change, or saved offline sets
mis-judge staleness until the next regen:

- The three extract workflows run it on the staged image paths inside each re-cut PR, so art
  and manifest deploy atomically.
- `update-image-manifest.yml` backstops everything else that lands on main (hand edits,
  `/reject` reverts): regenerates on any `assets/diagrams/**` push and commits the drift.
  Idempotent, so its own commit cannot loop it.
- A manual image add (new discipline, hand-managed set) should run it alongside
  `tools/thumbnails/generate.py`, the backstop covers a forgotten run after push.

One entry per line, keys sorted, so git diffs read per-image.
