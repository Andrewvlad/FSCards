# FSCards
A fast, lightweight app to learn the Formation Skydiving dive pools through flashcards, quizzes, and gallery overview, with diagrams from every major source.
[Play now!](https://andrewvlad.github.io/FSCards/)

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
- Pick how you learn
  - Flashcards (`/cards/`) to drill the pool card by card
  - Gallery (`/gallery/`) to study the whole pool at a glance
  - Quiz (`/quiz/`) to test your knowledge with multiple-choice
- Filters
- Endless mode
  - Random: Fully random
  - Adaptive: See incorrect/correct cards more/less
  - Learn: Learn a handful of formations at a time
- Video demonstrations (compiled by Axis)
- Auto-saved session, stats, and settings to localStorage
- Take it offline
  - Loaded image sets continue to work, even with weak/dropped connection
  - Download a discipline's image set ahead of time
    - Manage/update/remove saved sets from the settings panel
  - Installable as a lightweight app for any device
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
- [x] Downloadable app/diagrams (diagrams work; standalone app status below)
  - [x] Chrome (Standalone app verified on Desktop and Android)
  - [x] Safari (iPhone verified)
  - [ ] Rest (Brave, Firefox, Edge, Opera)
- [ ] 20-ways from TeXXas pool (first unofficial pool)
- [ ] Rebuild Rhythm diagrams

## Nerd Flex
- Entirely clientside using legible HTML/CSS/JS. Clean, fast, and no dependencies/libraries/frameworks.
- GitHub Actions pipeline to automatically update Axis and USPA image sets whenever a new PDF is automatically found online.
- 404 hack to enable URL forwarding (shortens "anagrammatic" query param links, e.g. /mfs, /2waycf, /speed-6, /8, etc. all work).
- Blocks get split horizontally on landscape devices (except Rhythm, which isn't a trifold).
- Downloaded images are served from a unified on-device cache, so a browser tab and its installed app both use them (Chromium, whereas iOS keeps the app's storage separate).
- Offline updates use three independent pathways:
  - Silent shell updates on minor and patch version bumps.
  - Opt-in consent banner on major version bumps.
  - Diagram updates have individual hashes, preventing redundant updates and version bumps (image updates are also opt-in).
- Filters are dynamic and hide when they don't apply.
- Sourced images are of lossless, max quality.
- UI scales at every size (down to ~200px wide, or ~300px tall, to be tested on ultrawide screens).

## FAQ
- Why not use the Rhythm 101 app? 
  - You should! 
    It's just that the Rhythm App only has flashcards of the 4-way randoms.
    This app is not a replacement, and I will never add any of the other flashcards from the Rhythm app.
    If you'd like to learn about body flight or study for a license exam, I highly recommend getting the Rhythm app on the [Android](https://play.google.com/store/apps/details?id=com.rhythm.android) or [Apple App Store](https://apps.apple.com/us/app/rhythm-skydiving-101/id1054896853).

## Code Walk
- Core app is just your standard HTML/CSS/JS.
  - `/index.js` contains the generic pool/deck logic.
  - `/shared.js` contains shared, repeated elements such as filters, settings, image loading, and offline downloads.
  - `/play.js` contains the "game" portions, that are specific to the Flashcards and Quiz modes (grading, saves, endless mode).
  - The offline layer is broken into three parts: 
    - `/version.js` is the basic versioning file that gets bumped.
    - `/sw.js` is the service worker, which captures the whole app shell (pages, scripts, fonts, etc.) and serves it cache-first, so the app works offline.
    - `/offline.js` is the page-side client, handling registration, update banner, and install.
- `/assets/diagrams` contains the formations, categorized by discipline.
  - `/<discipline>/index.js` contains the per-discipline metadata.
  - `/<discipline>/<provider>/figures` are the diagrams with their labels and symbols stripped.
  - `/panel-cuts.js` contains the trifold cuts for each figure.
- `/tools` contains the image extraction pipelines (mainly AI generated).
- `/.github/workflows` contains the GitHub Actions pipeline that keeps the image sets up to date.
  - `/update-axis-sources.yml` checks and fetches the latest Axis image set PDFs from the Axis website, and PRs per discipline ([example](https://github.com/Andrewvlad/FSCards/pull/2)).
  - `/extract-axis-images.yml` is triggered by an updated Axis PDF, and cuts out only updated images for PR ([example](https://github.com/Andrewvlad/FSCards/pull/5)).
  - `/update-uspa-sources.yml` and `/extract-uspa-images.yml` are equivalents for USPA.
  - `/extract-fai-images.yml` are equivalents for FAI (no fetch as the URL format is inconsistent).
  - `/reject-extracted-images.yml` allows for rejecting image updates (Axis, USPA, or FAI) using PR comments ([example](https://github.com/Andrewvlad/FSCards/pull/5)).
