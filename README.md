# FSCards
A fast, lightweight flashcard app to learn the Formation Skydiving dive pools, with diagrams from every provider.

## Disciplines

| Discipline   | Pool                  | Diagram sets            |
|--------------|-----------------------|-------------------------|
| 4-Way        | 16 randoms, 22 blocks | Rhythm, USPA, Axis, FAI |
| 8-Way        | 16 randoms, 22 blocks | Rhythm, USPA, Axis, FAI |
| 10-Way Speed | 12 formations         | USPA, Axis              |
| 16-Way       | 9 randoms, 12 blocks  | USPA, Axis              |
| VFS 4-Way    | 16 randoms, 22 blocks | USPA, Axis              |
| MFS 2-Way    | 16 randoms, 22 blocks | USPA, Axis              |
| CF 2-Way     | 6 randoms             | USPA, Axis              |
| CF 4-Way     | 14 randoms, 14 blocks | USPA, Axis              |
| CP Freestyle | 23 moves              | USPA                    |

### Collegiate

| Discipline  | Pool                   | Diagram sets            |
|-------------|------------------------|-------------------------|
| 2-Way       | 4 randoms + 15 blocks  | USPA, Axis              |
| 4-Way       | 16 randoms + 8 blocks  | Rhythm, USPA, Axis, FAI |
| 6-Way Speed | 5 formations           | USPA                    |
| VFS 2-Way   | 10 randoms + 7 blocks  | USPA, Axis              |

### CISM

| Discipline | Pool                  | Diagram sets            |
|------------|-----------------------|-------------------------|
| 4-Way      | 17 randoms + 8 blocks | Rhythm, USPA, Axis, FAI |

## Features
- Gallery view (`/gallery/`) to study the whole pool at a glance
- Filters
- Video demonstrations (compiled by Axis)
- Auto-saved session, stats, and settings to localStorage
- Dark mode
- Keybindings and gesture controls
  - `[SPACE]` (or tap) - Flip card
  - `[←]`/`[→]` (or swipe) - Mark wrong/correct/skip

## Missing Image Sets
- Spaceland 3-way/5-way (unpublished, unofficial, not actively competed)
- IBA/iFly VFS (unpublished, likely inactive)
  - They link to Axis currently for their dive pool
- CF 8-Way Speed (inactive)
- Fury Coaching
  - Only differs by watermark
- Axis experimental dive pools (since they are not active in competition)
- 2-way MFS MatriX image pool
- 6-way FS
  - Only part of Fury's Dueling DZs
- VFS Ninja
  - Basically covered with existing image pools
  - Still a really cool project that you should [check out](https://github.com/ervanalb/vfs.ninja)!

## TODO
- [x] Full mobile support
  - [x] Landscape support
- [x] Adaptive (weighted) and learn modes to endless
- [ ] 20-ways from TeXXas pool (first unofficial pool)
- [ ] Rebuild Rhythm diagram sets
- [ ] Downloadable app/image sets

## Nerd Flex
- Entirely clientside using legible HTML/CSS/JS. Clean, fast, and no dependencies/libraries/frameworks.
- GitHub Actions pipeline to automatically update Axis image sets.
- 404 hack to enable URL forwarding (shortens "anagrammatic" query param links, e.g. /mfs, /2waycf, /speed6, /8, etc. all work).
- Blocks get split horizontally on landscape devices (except Rhythm, which isn't a trifold).
- Filters are dynamic and hide when they don't apply.
- Sourced images are of lossless, max quality.
- UI scales at every size (down to ~200px wide, or ~300px tall, to be tested on ultrawide screens).

## Code Walk
- Core app is just your standard HTML/CSS/JS.
- `/assets/diagrams` contains the formations, categorized by discipline.
  - `/<discipline>/index.js` contains the per-discipline metadata.
  - `/<discipline>/<provider>/figures` are the diagrams with their labels and symbols stripped.
  - `/panel-cuts.js` contains the trifold cuts for each figure.
- `/tools` contains the image extraction pipelines (mainly AI generated).
- `/.github/workflows` contains the GitHub Actions pipeline that keeps the image sets up to date.
  - `/update-axis-sources.yml` fetches the latest Axis image set PDFs from the Axis website, and PRs per dicipline ([example](https://github.com/Andrewvlad/FSCards/pull/2)).
  - `/extract-axis-images.yml` is triggered by an updated Axis PDF, and cuts out only updated images for PR ([example](https://github.com/Andrewvlad/FSCards/pull/5)).
  - `/reject-extracted-images.yml` allows for rejecting image updates using PR comments ([example](https://github.com/Andrewvlad/FSCards/pull/5)).
