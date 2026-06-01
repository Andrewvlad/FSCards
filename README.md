# FSCards
A free flashcard app to learn the Formation Skydiving (FS) dive pool.

Drill the 4-way and 8-way randoms and blocks the way I used to drill countries with GeoCards.
There are formation diagrams from every major provider.
Runs entirely clientside - no internet connection required.

## Disciplines

| Discipline   | Pool                   | Diagram sets       |
|--------------|------------------------| ------------------ |
| 4-Way        | 16 randoms + 22 blocks | Rhythm, USPA, Axis |
| 8-Way        | 16 randoms + 22 blocks | Rhythm, USPA, Axis |
| 10-Way speed | 12 formations          | USPA, Axis         |
| 16-Way       | 9 randoms + 12 blocks  | USPA, Axis         |
| VFS 4-Way    | 16 randoms + 22 blocks | USPA, Axis         |
| MFS 2-Way    | 16 randoms + 22 blocks | USPA, Axis         |
| CF 2-Way     | 6 randoms              | USPA, Axis         |
| CF 4-Way     | 14 randoms + 14 blocks | USPA, Axis         |
| CP Freestyle | 23 moves (5 groups)    | USPA               |

### Collegiate

| Discipline  | Pool                  | Diagram sets |
| ----------- | --------------------- | ------------ |
| 2-Way       | 4 randoms + 15 blocks | USPA, Axis   |
| 4-Way        | 17 randoms + 22 blocks | Rhythm, USPA, Axis |
| 6-Way speed | 5 formations          | USPA         |
| VFS 2-Way   | 10 randoms + 7 blocks | USPA         |

### CISM

| Discipline  | Pool                  | Diagram sets |
| ----------- |-----------------------| ------------ |
| 4-Way        | 17 randoms + 8 blocks | Rhythm, USPA, Axis |

## Features
- Auto-saves session, stats, and settings to localStorage
- Keybindings and gesture controls
    - `[SPACE]` (or tap) — Flip card
    - `[←]`/`[→]` (or swipe) — Mark wrong/correct/skip

## Overview
The app runs entirely clientside using HTML/CSS/JS.
Formation diagrams are bundled in `assets/diagrams/` and mapped to letters/numbers in the
per-discipline `index.js` files. Progress and settings are saved using localStorage.
Card swiping is supported for both mobile touch gestures and desktop dragging.
