# thumbnails

Generates the low-quality **thumbnails** shown while a full diagram loads. Each
source diagram/figure gets a 128px-wide webp thumbnail written beside it under a `thumbs/`
subdir. The client shows the tiny thumb first (a few KB, near-instant), then swaps to the
full image once it loads, so a card never paints blank on a cold cache.

Separate files, not an inline data-URI map: the browser only fetches thumbs for the cards it
actually renders, so the page carries no inline weight however large the pool grows (the
whole inline alternative was ~4MB gzipped on every load). Trade-off: a thumb costs one quick
network hop before it paints, vs zero for inline - negligible at ~3KB, and `prefetchDeck` can
warm them with the deck.

## Output

- **Location:** `assets/diagrams/<discipline>/<set>/thumbs/<key>.webp`, and figures under
  `assets/diagrams/<discipline>/<set>/thumbs/figures/<key>.webp` - every thumb lives under the
  set's `thumbs/` dir, figure thumbs nesting in a `figures/` subdir there.
- **Format:** 128px wide (aspect preserved), webp `quality=50`, source alpha preserved so a
  thumb composites onto the card panel exactly like the diagram it stands in for (Rhythm's
  transparent jumpers, dark-mode inversion - all behave identically to the full image).
- **Size:** ~1344 thumbs, ~4MB on disk total, median ~2.7KB each. Committed like the diagrams.

Diagrams and figures get **distinct** thumbs and must stay that way: the figure is the card
**front** (the question, name/label erased), the diagram is the **back** (the answer). Reusing
a diagram's thumb on the front would blur the answer into the prompt.

## Run

```sh
python3 tools/thumbnails/generate.py            # rebuild every thumb (~1min)
python3 tools/thumbnails/generate.py 4-way 8-way # only these whole disciplines
python3 tools/thumbnails/generate.py assets/diagrams/4-way/Axis/13.webp # just these images
```

- Deterministic: re-running produces byte-identical thumbs, so an unchanged set shows no git
  diff. Re-run after any pipeline re-crop, or scoped to the disciplines that changed.
- **SVG sets (CF USPA) are skipped** - vector art is already tiny and sharp, no thumbnail
  needed. So a `.svg` src has no thumb (see Wiring).
- Deprecated/legacy art lives under `assets/sources`, outside the walk, and never gets a thumb.
- Each run **prunes orphan thumbs** whose source image is gone (scoped to the disciplines
  passed, or all when none are).

Wired into the extract workflows: each passes the exact image paths `install.py` staged
(diagrams + figures, adds/mods/deletes) to `generate.py` after the panel-cut measure, so only
the changed keys' thumbs are re-rendered - not the whole discipline (a deleted key's thumb is
dropped) - and `assets/diagrams/**` commits them. A `/reject` reverts a key's thumb alongside
its parent image (`reject-extracted-images.yml` expands each rejected key to its `thumbs/`
sibling, so the thumb is checked out from `main` - or `git rm`'d if it was a new key), so a
thumb never outlives the diagram it stands in for.

## Wiring (client side - not done here)

Derive a thumb path from any resolved image src by inserting `thumbs/` after the set dir:

```js
const thumbFor = (src) => src.replace(/\/(figures\/)?([^/]+)$/, '/thumbs/$1$2');
```

Works for both diagrams and figures (`.../USPA/A.webp` -> `.../USPA/thumbs/A.webp`,
`.../USPA/figures/A.webp` -> `.../USPA/thumbs/figures/A.webp`).

- **Guard SVG:** `.svg` srcs have no thumb, so skip the thumbnail for them (`src.endsWith('.svg')`)
  - vector loads instantly anyway.
- **Render:** point an `<img>` at the thumb, lay the full diagram over it, fade/swap the full
  in on its `load` event. The thumb shares the diagram's classes, so theme inversion and the
  white panel apply to both - no extra dark-mode handling.
- **Warm with the deck:** add each card's `thumbFor(image)` (and `thumbFor(figure)` when the
  card front is the figure) to `prefetchDeck`'s URL set so the deck's thumbs are cached too.
