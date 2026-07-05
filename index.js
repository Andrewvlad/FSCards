// Fisher-Yates shuffle (returns a new array)
function randomizeDeck(deck) {
    const shuffled = deck.slice();
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

// All per-discipline data
const DATA = {
    '2-way':        _2Way,
    '4-way':        _4Way,
    '6-way-speed':  _6WaySpeed,
    '8-way':        _8Way,
    '10-way-speed': _10WaySpeed,
    '16-way':       _16Way,
    '2-way-vfs':    _2WayVfs,
    '4-way-vfs':    _4WayVfs,
    '2-way-mfs':    _2WayMfs,
    '2-way-cf':     _2WayCf,
    '4-way-cf':     _4WayCf,
    'cp-freestyle': _CpFreestyle,
};

const isBlock = (key) => !isNaN(key);
const clamp = (value, lo, hi) => Math.min(hi, Math.max(lo, value));

// Sort A-Z, 1-99
const keyOrder = (a, b) => {
    const blockCheckA = isBlock(a), blockCheckB = isBlock(b);

    if (blockCheckA !== blockCheckB) return blockCheckA - blockCheckB; // Randoms before blocks
    else return blockCheckA
        ? a - b // Int comparison
        : a.localeCompare(b); // String comparison
};

// A discipline offers the Randoms/Blocks split only when it holds both numbered and lettered keys.
// Speed, 2-Way CF, CP, and block-less classes (4-way Rookie) have no split and skip the filter.
function categorized(settings) {
    const keys = Object.keys(buildPool(settings));
    return keys.some(isBlock) && keys.some(key => !isBlock(key));
}

// USPA fallback
function activeImageSet(discipline, imageSet) {
    return imageSet in DATA[discipline].sets ? imageSet : 'USPA';
}

function poolImages({discipline, indoor, imageSet, split}) {
    const data = DATA[discipline];
    const set = activeImageSet(discipline, imageSet);
    const resolve = (setName, key) => {
        const filename = data.sets[setName];
        const file = filename ? filename(key, indoor) : `${key}.webp`;
        // A filename with a path borrows from a sibling set (ex. USPA indoor uses FAI (USIS))
        return `assets/diagrams/${discipline}/${file.includes('/') ? file : `${setName}/${file}`}`;
    };
    const images = {};
    for (const key of Object.keys(data.names)) {
        // USPA fallback when the set's blocks are too tall to split
        const fallback = split && isBlock(key) && SINGLE_PANEL_BLOCKS.has(set) && 'USPA';
        images[key] = resolve(fallback || set, key);
    }
    return images;
}

// Not inversion-friendly
// TODO: Try out different methods
const LIGHT_USPA = new Set(['4-way-vfs', 'cp-freestyle']);

// 'dark' diagrams invert with the theme while 'light' remain white
function diagramMode(discipline, imageSet) {
    const set = activeImageSet(discipline, imageSet);
    return ['USPA', 'FAI'].includes(set) && !LIGHT_USPA.has(discipline) ? 'dark' : 'light';
}

// Sets that are unsplittable
const SINGLE_PANEL_BLOCKS = new Set(['Rhythm']);

// Look up pre-computed divider positions
function panelCutsFor(src) {
    const [, , discipline, set, ...file] = src.split('/');
    const cuts = PANEL_CUTS[discipline]?.[set];
    return Array.isArray(cuts) ? cuts : cuts?.[file.at(-1).split('.')[0]];
}

// Text-free card variant used for the front
const figureFor = (path) => path.replace(/\/([^/]+)$/, '/figures/$1');

// Low-res thumbnail sibling (tools/thumbnails); figures nest under thumbs/figures/, no thumb for SVG sets
const thumbFor = (path) => path.replace(/\/(figures\/)?([^/]+)$/, '/thumbs/$1$2');

function imageSetsFor(discipline) {
    return Object.keys(DATA[discipline].sets);
}

function videoFor(discipline, key) {
    return DATA[discipline].videos?.[key];
}

function includeCaption(discipline) {
    return DATA[discipline].includeCaption;
}

// 'R' is a CISM-only random.
const OPT_IN_KEYS = {
    '4-way': ['R'],
};

// Build the class-scoped pool (all eligible cards, unshuffled) as key -> card.
function buildPool({discipline, indoor, imageSet, classLevel, tunnel, includeFusions = true, split}) {
    const images = poolImages({discipline, indoor, imageSet, split});
    const names = DATA[discipline].names;

    const cls = classesFor(discipline).find(c => c.key === classLevel) ?? {};

    const keys = Object.keys(images);
    const optIn = OPT_IN_KEYS[discipline] ?? [];
    let blocks    = cls.blocks  ?? keys.filter(isBlock);
    const randoms = cls.randoms ?? keys.filter(k => !isBlock(k) && !optIn.includes(k));

    // Apply 12-foot tunnel toggle
    const tunnelBlocks = tunnelFor(discipline);
    if (tunnel && tunnelBlocks)
        blocks = blocks.filter(k => tunnelBlocks.includes(Number(k)));

    // Apply Fusions toggle
    const fusions = fusionsFor(discipline);
    if (!includeFusions && fusions)
        blocks = blocks.filter(k => !fusions.includes(Number(k)));

    const pool = {};
    for (const key of [...randoms, ...blocks]) {
        pool[key] = {
            key: String(key),
            name: names[key],
            image: images[key],
            figure: figureFor(images[key]),
            video: videoFor(discipline, key),
        };
    }
    return pool;
}

function classesFor(discipline) {
    return DATA[discipline].classes ?? [];
}

function tunnelFor(discipline) {
    return DATA[discipline].tunnel;
}

function fusionsFor(discipline) {
    return DATA[discipline].fusions;
}

// Whole-collegiate discipline (collegiate: true) - dropped from the mode bar unless revealed on the landing page
const isCollegiate = discipline => DATA[discipline].collegiate === true;

function buildDeck(settings) {
    return randomizeDeck(Object.values(buildPool(settings)));
}

// Rebuild a deck in its saved key order, dropping any keys that no longer exist
function deckFromKeys(keys, settings) {
    const pool = buildPool(settings);
    return keys.map(k => pool[k]).filter(Boolean);
}

const SHARED_STORE = 'fscards-shared';
const SHARED_FIELDS = ['discipline', 'category', 'classLevel', 'indoor', 'tunnel', 'includeFusions', 'imageSet', 'invert'];

// Standalone landing-page toggle (own key like the theme, not a shared filter): reveal collegiate disciplines in the views
const COLLEGIATE_KEY = 'fscards-collegiate';
function collegiateShown() {
    try { return localStorage.getItem(COLLEGIATE_KEY) === '1'; }
    catch (e) { return false; } // Storage may be unavailable
}

function saveShared(state) {
    try {
        const shared = {};
        for (const field of SHARED_FIELDS) shared[field] = state[field];
        localStorage.setItem(SHARED_STORE, JSON.stringify(shared));
    } catch (e) {} // Storage may be unavailable
}

function loadShared() {
    let shared = null;
    try { shared = JSON.parse(localStorage.getItem(SHARED_STORE)); }
    catch (e) {} // Unavailable or malformed

    // Discipline override from query param
    const params = new URLSearchParams(location.search);
    const discipline = params.get('discipline');

    // Strip the param for clean URL
    if (discipline !== null) {
        params.delete('discipline');
        const query = params.toString();
        history.replaceState(null, '', location.pathname + (query ? '?' + query : ''));
    }
    if (discipline in DATA) {
        shared = {...shared, discipline};
        saveShared(shared);
    }
    return shared;
}

/** Restore in-progress run (when navigating the app) **/
function storedRun() {
    try {
        const run = JSON.parse(localStorage.getItem(SAVE_KEY));
        if (run?.endless === true) run.endless = 'random'; // Migration from the pre-strategy boolean
        return run;
    } catch (e) { return null; } // Storage may be unavailable
}

// Stored run matches the current in-memory pool identity (discipline + pool-defining filters)
function poolMatches(data) {
    return data.discipline === discipline
        && data.classLevel === classLevel
        && data.tunnel === tunnel
        && data.includeFusions === includeFusions
        && data.category === category;
}

// Shared body of each page's restoreRun. False if the stored deck no longer builds (pool revised)
function restoreRunCore(data) {
    // Rebuild the full pool (for category switching), then restore the played deck
    fullDeck = buildDeck(poolSettings());
    deck = deckFromKeys(data.deck, poolSettings());
    if (!deck.length) return false;

    // Endless before rebuildEndlessState so a counter past pool size isn't read as complete
    recycle = data.recycle ?? recycle;
    endless = data.endless ?? false;
    rebuildEndlessState(data);
    missed = data.missed ?? {};

    correct.textContent = data.correct;
    wrong.textContent   = data.wrong;
    streak.textContent  = data.streak;
    return true;
}

// A pool-filter switch resumes the stored run when it matches the new pool, else builds fresh
function switchDeck(buildFresh, canResume = () => true) {
    const run = storedRun();
    if (run?.deck?.length && canResume(run) && poolMatches(run) && restoreRun(run)) {
        syncSettingsUI(); // Reflect the resumed run's settings (endless, recycle, category, page-own)
        nextCard();
        saveSession(); // Rewrites the same run, but the cross-page filter mirror must see the switch
    } else {
        buildFresh();
    }
}

/** Card carousel **/
const DRIFT_SPEED = 30; // px/s idle auto-scroll
const DRIFT_IDLE = 2000; // ms delay before drift resumes
const FRAME_MAX_STEP = 50; // ms before freezing background tab (so it doesn't jump forward on return)
const GLIDE_MS = 380; // tap-to-center glide length
const TAP_SLOP = 6; // px of travel that still counts as a tap, not a drag
const FLING_MIN = 0.08; // min px/ms release to fling
const FLING_STOP = 0.02; // px/ms which a coast ends
const FLING_FRICTION = 0.94; // velocity kept per 60fps frame of coast
const FLING_WINDOW = 100; // ms of recent moves averaged for the release velocity

const DRIFT_KEY = 'fscards-drift'; // Remembers the auto-scroll on/off choice
let driftEnabled = loadDrift();

// Auto-scroll preference, default on when unset or storage is unavailable
function loadDrift() {
    try { return localStorage.getItem(DRIFT_KEY) !== 'off'; } catch (e) { return true; }
}
function saveDrift() {
    try { localStorage.setItem(DRIFT_KEY, driftEnabled ? 'on' : 'off'); } catch (e) {} // Storage may be unavailable
}

// The wrong-answer cards, ordered like the chip row, dropping any key no longer in the pool
function collectMissed() {
    return Object.keys(missed)
        .sort(keyOrder)
        .map(key => ({card: fullDeck.find(card => card.key === key), count: missed[key]}))
        .filter(entry => entry.card);
}

// Every card in the played deck, ordered like the chip row (shown on a clean run)
function allDeckItems() {
    return deck.map(card => ({card})).sort((a, b) => keyOrder(a.card.key, b.card.key));
}

// Add caption if needed, never split trifold
function carouselFace(card) {
    const img = `<img class="diagram" ${lazySrc(card.image)} alt="${card.key}">`;
    if (!includeCaption(discipline)) return img;
    return `<figure class="captionedDiagram">${img}<figcaption>${card.name}</figcaption></figure>`;
}

// Carousel markup: label, key chips, carousel, tap hint, and auto-scroll toggle, plus pop-out logic
function carouselMarkup(items, label) {
    const chips = items.map(({card, count}) =>
        `<button type="button" class="carouselChip" data-key="${card.key}" onclick="centerCard('${card.key}')">${card.key}${count > 1 ? `(${count})` : ''}</button>`).join('');
    const cards = items.map(({card}) =>
        `<div class="carouselCard" data-key="${card.key}">${carouselFace(card)}</div>`).join('');
    // Carets on either end of the strip, each advancing the center one key
    const caret = (dir) => {
        const prev = dir === 'prev';
        return `<button type="button" class="carouselCaret ${dir}" aria-label="${prev ? 'Previous' : 'Next'} card" onclick="stepCard(${prev ? -1 : 1})"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></button>`;
    };
    return `<div id="carouselSection">
                ${label ? `<div class="label">${label}</div>` : ''}
                <div id="carouselChips">${chips}</div>
                <div id="carouselViewport">
                    ${caret('prev')}
                    <div id="carouselStrip"><div id="carouselTrack">${cards}</div></div>
                    ${caret('next')}
                </div>
                <p class="carouselHint">Tap to center, tap again to expand</p>
                <button type="button" id="driftToggle" class="carouselChip" onclick="toggleDrift()">
                    <!--Play icon (SVG looks better than its Unicode/emoji counterparts)-->
                    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.5L18.5 12L8 18.5Z"/></svg>
                    Auto-scroll
                </button>
                <div id="cardPopout" class="hidden" role="dialog" aria-modal="true" aria-label="Expanded card"></div>
            </div>`;
}

let carousel = null; // Active controller, self-stops when the carousel leaves the DOM

// A chip tap centers its real card (no-op while the strip already fits)
function centerCard(key) {
    carousel.centerKey(key);
}

// A caret advances the focus one key and centers it
function stepCard(dir) {
    carousel.step(dir);
}

function toggleDrift() {
    carousel.toggleDrift();
}

// Wire the carousel once the card images have sized, so the loop width is measured true
function initCarousel(items) {
    const strip = document.getElementById('carouselStrip');
    const track = document.getElementById('carouselTrack');
    const chips = [...document.getElementById('carouselChips').children];
    const reals = [...track.children];
    const viewport = strip.parentElement; // #carouselViewport, holds the flanking carets
    const caretPrev = viewport.querySelector('.carouselCaret.prev');
    const caretNext = viewport.querySelector('.carouselCaret.next');
    const driftBtn = document.getElementById('driftToggle');
    const popout = document.getElementById('cardPopout');
    const keyIndex = (key) => items.findIndex(entry => entry.card.key === key);

    // Scroll + focus state
    let pos = 0; // px scrolled left, sub-pixel
    let looping = false; // temporary seam loop, granted by a grab made mid-drift
    let drifting = false, gliding = false;
    let suppressClick = false; // ignore the opening tap's trailing click so it does not re-close the pop-out
    let held = null; // pinned / edge-snapped focus, held until drift recenters it
    let focusIndex = null, litIndex = null; // Chip to light / chip currently lit
    let driftHandle = 0, glideHandle = 0, idleHandle = 0, lastTs = 0;
    let velocity = 0, coasting = false, momentumHandle = 0, momentumTs = 0, samples = [];

    // Geometry, filled by measure()
    let viewW = 0, loopW = 0, clampMax = 0, overflow = false, cloned = false, centers = [];

    const render = () => track.style.transform = `translateX(${-pos}px)`;
    const alive = () => track.isConnected; // false once finish/New Session/Replay wipes the arena
    const paint = () => { render(); updateHighlight(); updateCarets(); }; // Apply pos to the DOM: transform + lit chip + edge carets

    // View + loop geometry, re-run on every resize. Clones build once, the rest re-measures
    function measure() {
        viewW = strip.clientWidth;
        const origin = reals[0].offsetLeft;
        const contentW = reals.at(-1).offsetLeft + reals.at(-1).offsetWidth - origin;
        centers = reals.map(card => card.offsetLeft + card.offsetWidth / 2 - origin);
        const gainedOverflow = contentW > viewW + 1 && !overflow; // fit -> overflow, (re)start drift
        overflow = contentW > viewW + 1;
        clampMax = Math.max(0, contentW - viewW);
        strip.classList.toggle('overflowing', overflow); // left-align + grab cursor when scrollable

        if (overflow && !cloned) {
            // One full copy after the last card covers a viewport, so the seam wraps seamlessly
            reals.forEach(card => {
                const clone = card.cloneNode(true);
                clone.classList.add('clone');
                clone.querySelectorAll('img[data-full]').forEach(swapToFullImage); // upgrade thumbs
                track.appendChild(clone);
            });
            cloned = true;
        }
        if (cloned) loopW = track.children[reals.length].offsetLeft - origin; // first clone's offset = one cycle

        // Keep the scroll valid after a resize/rotate reflows the cards
        if (!overflow) { cancelDrift(); cancelMomentum(); pos = 0; looping = false; }
        else if (drifting || looping) wrapPos();
        else pos = clamp(pos, 0, clampMax);

        if (gainedOverflow) startDrift(); // drift immediately once the strip overflows, no initial idle wait
        paint();
    }

    // The real card nearest the view center, counting its looped clone copy too
    function centeredIndex() {
        const mid = pos + viewW / 2;
        let best = 0, bestDist = Infinity;
        centers.forEach((cx, i) => {
            const dist = Math.min(Math.abs(cx - mid), Math.abs(cx + loopW - mid));
            if (dist < bestDist) { bestDist = dist; best = i; }
        });
        return best;
    }

    const atEdge = () => !looping && (pos <= 1 || pos >= clampMax - 1);
    const popped = () => !popout.classList.contains('hidden'); // card expanded, drift suspended until it closes

    // Canonicalize pos into the base cycle so seam math never runs off the one clone copy
    const wrapPos = () => { while (loopW && pos >= loopW) pos -= loopW; };

    function lightChip(index) {
        if (index === litIndex) return; // Called per frame, most frames change nothing
        litIndex = index;
        chips.forEach((chip, i) => chip.classList.toggle('lit', i === index));
    }

    // Focus priority: pin/edge hold, then a hard-clamp edge, otherwise the centered card
    function updateHighlight() {
        if (!overflow) return lightChip(null); // nothing scrolls, nothing lit
        const centered = centeredIndex();
        if (held !== null) {
            focusIndex = held;
            if (centered === held && (drifting || gliding)) held = null; // drift caught up, release
        } else if (!drifting && !gliding && atEdge()) {
            focusIndex = pos <= 1 ? 0 : reals.length - 1; // edge snap so the end chips can light
        } else {
            focusIndex = centered;
        }
        lightChip(focusIndex);
    }

    // Hide the caret on whichever hard-clamp edge the strip rests against, so a tap can't step past it
    function updateCarets() {
        const clamped = !drifting && !gliding && atEdge();
        caretPrev.classList.toggle('hidden', clamped && pos <= 1);
        caretNext.classList.toggle('hidden', clamped && pos >= clampMax - 1);
    }

    // Apply a scroll delta under the clamp model: hard clamp by default, temporary loop only at the seam
    function manualScroll(delta) {
        if (!overflow) return;
        if (pos > clampMax) looping = true; // grabbed within the drift seam region
        let next = pos + delta;
        if (looping) {
            while (next >= loopW) next -= loopW; // wrap forward across the seam
            if (next < 0) next = 0; // never loop backward past the first card
            if (next <= clampMax) looping = false; // seam left the view (crossed or backed out), hard clamp returns
            pos = next;
        } else {
            pos = clamp(next, 0, clampMax);
        }
        paint();
    }

    function cancelDrift() {
        drifting = false;
        cancelAnimationFrame(driftHandle);
    }

    function scheduleDrift() {
        clearTimeout(idleHandle);
        idleHandle = setTimeout(startDrift, DRIFT_IDLE);
    }

    // Any interaction pauses drift and restarts the idle countdown
    function interact() {
        cancelDrift();
        scheduleDrift();
    }

    // Reflect the auto-scroll choice on the pill (markup renders neutral, this is the one writer)
    function updateDriftButton() {
        driftBtn.classList.toggle('lit', driftEnabled);
        driftBtn.setAttribute('aria-pressed', driftEnabled);
    }

    function toggleDrift() {
        driftEnabled = !driftEnabled;
        saveDrift();
        updateDriftButton();
        if (driftEnabled) startDrift();
        else { cancelDrift(); clearTimeout(idleHandle); }
    }

    function startDrift() {
        if (!overflow || !alive() || gliding || coasting || !driftEnabled || popped()) return;
        looping = false; // a manual-only state, surrendered once drift owns the scroll
        held = null; // drift owns the highlight now - follow the centered chip, not a frozen edge/near-edge pin
        drifting = true;
        lastTs = 0;
        driftHandle = requestAnimationFrame(driftFrame);
    }

    function driftFrame(now) {
        if (!alive()) return cancelDrift();
        const dt = lastTs ? Math.min(now - lastTs, FRAME_MAX_STEP) : 0;
        lastTs = now;
        pos += DRIFT_SPEED * dt / 1000; // sub-pixel so hi-DPI phones do not judder
        wrapPos();
        paint();
        if (drifting) driftHandle = requestAnimationFrame(driftFrame);
    }

    function cancelMomentum() {
        coasting = false;
        velocity = 0;
        cancelAnimationFrame(momentumHandle);
    }

    function cancelGlide() {
        gliding = false;
        cancelAnimationFrame(glideHandle);
    }

    // Seed a decaying coast from the release velocity, feeding the same clamp model as a drag
    function startMomentum() {
        const now = performance.now();
        const recent = samples.filter(s => now - s.t <= FLING_WINDOW);
        if (recent.length < 2) return false;
        const first = recent[0], last = recent.at(-1);
        const span = last.t - first.t;
        if (span <= 0) return false;
        const v = -(last.x - first.x) / span; // pos-space px/ms (drag right scrolls pos left)
        if (Math.abs(v) < FLING_MIN) return false;
        cancelDrift();
        clearTimeout(idleHandle);
        cancelAnimationFrame(momentumHandle);
        velocity = v;
        coasting = true;
        momentumTs = now;
        momentumHandle = requestAnimationFrame(momentumFrame);
        return true;
    }

    function momentumFrame(now) {
        if (!alive()) return cancelMomentum();
        const dt = Math.min(now - momentumTs, FRAME_MAX_STEP);
        momentumTs = now;
        const before = pos;
        manualScroll(velocity * dt);
        velocity *= FLING_FRICTION ** (dt / 16.6667); // frame-rate independent decay
        if ((pos === before && !looping) || Math.abs(velocity) < FLING_STOP) { // hit a hard edge or spent
            cancelMomentum();
            scheduleDrift();
            return;
        }
        momentumHandle = requestAnimationFrame(momentumFrame);
    }

    // Smoothly glide the carousel (horizontal only) to center a card, as far as the clamp allows
    function glideTo(target) {
        cancelMomentum();
        cancelDrift();
        cancelGlide();
        clearTimeout(idleHandle);
        gliding = true;
        looping = false;
        const start = pos, dist = target - start, t0 = performance.now();
        const step = (now) => {
            if (!alive()) return gliding = false;
            const k = Math.min(1, (now - t0) / GLIDE_MS);
            pos = start + dist * (1 - (1 - k) ** 3); // easeOutCubic
            paint();
            if (k < 1) glideHandle = requestAnimationFrame(step);
            else { gliding = false; paint(); scheduleDrift(); } // final paint once rested to hide an edge caret
        };
        glideHandle = requestAnimationFrame(step);
    }

    // Pin the tapped card's highlight and center it as far as the clamp allows, false when it
    // cannot scroll any closer (no overflow, or already at the clamp) so a card tap can expand instead
    function centerKey(key) {
        if (!overflow) return false;
        const i = keyIndex(key);
        // If the seam is showing, center the tapped copy, not the real card back in the strip
        if (pos > clampMax) {
            wrapPos();
            return glideLoop(i, pos + viewW / 2);
        }
        const target = clamp(centers[i] - viewW / 2, 0, clampMax);
        held = i; // pin the highlight to the tapped card, even when it cannot scroll further
        if (Math.abs(target - pos) < 1) { updateHighlight(); return false; } // already as centered as the clamp allows
        glideTo(target);
        return true;
    }

    // A caret pages one card - loop-walk through the drift seam, else shift one clamped card pitch
    function step(dir) {
        if (!overflow) return;
        const from = centeredIndex();
        const wraps = from + dir < 0 || from + dir >= items.length;
        if ((drifting || looping) && (pos > clampMax || wraps)) return stepLoop(from, dir);
        const to = clamp(from + dir, 0, items.length - 1);
        held = null; // paging follows the centered chip, not a stale pin
        glideTo(clamp(pos + centers[to] - centers[from], 0, clampMax));
    }

    // Step to the adjacent card, referencing the from-card's own copy so the wrap keeps the drift direction
    function stepLoop(from, dir) {
        wrapPos();
        const mid = pos + viewW / 2;
        const vcFrom = Math.abs(centers[from] - mid) <= Math.abs(centers[from] + loopW - mid) ? centers[from] : centers[from] + loopW;
        glideLoop((from + dir + items.length) % items.length, vcFrom);
    }

    // Glide to card i's copy nearest ref (a pos-space x), staying in loop space so it never snaps back to the strip
    function glideLoop(i, ref) {
        const targetPos = [centers[i], centers[i] + loopW, centers[i] - loopW]
            .reduce((best, c) => Math.abs(c - ref) < Math.abs(best - ref) ? c : best) - viewW / 2;
        held = i; // pin the highlight to the target card
        if (Math.abs(targetPos - pos) < 1) { updateHighlight(); return false; } // rested on it already, let the tap expand
        glideTo(targetPos);
        looping = targetPos > clampMax; // keep loop state so the rested seam is not read as a hard edge
        return true;
    }

    // Keybindings to close the popout
    const onPopoutKey = (event) => {
        if (!alive()) return document.removeEventListener('keydown', onPopoutKey); // page re-rendered mid-popout, self-clean
        if (event.key !== 'Escape' && event.key !== ' ') return;
        event.preventDefault(); // Space would otherwise scroll the page
        closePopout();
    };

    // Expand the tapped (already-centered) card over the viewport, suspending drift while open
    function openPopout(key) {
        const entry = items[keyIndex(key)];
        popout.innerHTML = carouselFace(entry.card);
        popout.classList.remove('hidden');
        suppressClick = true; // a touch tap emits a trailing compat click over the fresh overlay that would re-close it
        cancelDrift();
        clearTimeout(idleHandle);
        document.addEventListener('keydown', onPopoutKey);
    }

    // Close the pop-out, letting drift resume if it was left on
    function closePopout() {
        popout.classList.add('hidden');
        popout.innerHTML = '';
        document.removeEventListener('keydown', onPopoutKey);
        if (driftEnabled) scheduleDrift();
    }

    // The real card key under a pointer, mapping any clone back to its real card
    const keyAt = (event) => event.target.closest('.carouselCard')?.dataset.key ?? null;

    // Pointer drag (mouse) + swipe (touch); touch-action keeps vertical as page scroll
    let dragging = false, downKey = null, lastX = 0, moved = 0;
    strip.addEventListener('pointerdown', event => {
        cancelMomentum(); // a fresh grab takes over any coast in progress
        cancelGlide(); // and any in-flight tap-to-center glide
        if (overflow) interact(); // no drift to pause/reschedule when the strip fits
        held = null; // a fresh grab releases a pin / edge snap
        dragging = true;
        moved = 0;
        lastX = event.clientX;
        samples = [{t: performance.now(), x: event.clientX}];
        downKey = keyAt(event);
        strip.classList.add('grabbing');
        strip.setPointerCapture(event.pointerId);
    });
    strip.addEventListener('pointermove', event => {
        if (!dragging) return;
        const now = performance.now();
        const dx = event.clientX - lastX;
        lastX = event.clientX;
        moved += Math.abs(dx);
        samples.push({t: now, x: event.clientX});
        while (samples.length > 2 && now - samples[0].t > FLING_WINDOW) samples.shift();
        manualScroll(-dx); // drag right moves content right (pos decreases)
        interact();
    });
    const endDrag = (event) => {
        if (!dragging) return;
        dragging = false;
        strip.classList.remove('grabbing');
        strip.releasePointerCapture(event.pointerId);
        if (moved <= TAP_SLOP && downKey !== null) { // a clean press
            if (drifting || gliding) return centerKey(downKey); // moving strip: a tap stops it and centers
            if (!centerKey(downKey)) openPopout(downKey); // a card that cannot be centered (edge / no overflow / already centered) expands on this tap
            return;
        }
        if (overflow && !startMomentum()) scheduleDrift(); // a fling coasts (and self-schedules drift), else idle now
    };
    strip.addEventListener('pointerup', endDrag);
    strip.addEventListener('pointercancel', endDrag);

    // Dismiss on click (not pointerup) so the overlay consumes the tap's own click instead of a chip below
    popout.addEventListener('click', () => {
        if (suppressClick) { suppressClick = false; return; }
        closePopout();
    });
    // A real dismissal press starts with a pointerdown on the overlay, the opening tap's ghost click has none
    popout.addEventListener('pointerdown', () => suppressClick = false);

    // Vertical wheel scrolls the horizontal strip (down = right)
    strip.addEventListener('wheel', event => {
        if (!overflow) return;
        event.preventDefault();
        cancelMomentum();
        cancelGlide();
        held = null;
        interact();
        manualScroll(event.deltaY);
    }, {passive: false});

    // Dragging a diagram scrolls the strip rather than ghosting the image
    strip.addEventListener('dragstart', event => event.preventDefault());

    carousel = {centerKey, step, toggleDrift};
    updateDriftButton(); // paint the persisted auto-scroll state onto the neutral markup

    // Build clones only once the images (and caption font) have sized, under rAF so a
    // backgrounded tab (frozen rAF) defers the build until it is foregrounded again
    const ready = [...track.querySelectorAll('img')].map(img =>
        img.complete ? null : new Promise(resolve => {
            img.addEventListener('load', resolve, {once: true});
            img.addEventListener('error', resolve, {once: true});
        }));
    Promise.all([...ready, document.fonts.ready]).then(() =>
        alive() && requestAnimationFrame(() => {
            if (!alive()) return;
            measure();
            const ro = new ResizeObserver(() => alive() ? measure() : ro.disconnect());
            ro.observe(strip); // re-measure loop width + clamp when the window/phone resizes
        }));
}
