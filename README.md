# FSCards
A free flashcard app to learn the Formation Skydiving (FS) dive pool.

Drill the 4-way and 8-way randoms and blocks the way I used to drill countries with GeoCards.
There are formation diagrams from every major provider.
Runs entirely clientside - no internet connection required.

## Disciplines
- All of them

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
