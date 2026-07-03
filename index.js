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

// The page's stored run, parsed fresh. Null if absent or corrupt
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

// Card carousel
const DRIFT_SPEED = 30; // px/s idle auto-scroll
const DRIFT_IDLE = 2500; // ms of stillness before drift resumes
const FRAME_MAX_STEP = 50; // ms cap per frame so a backgrounded tab doesn't lurch on return
const GLIDE_MS = 380; // tap-to-center glide length
const TAP_SLOP = 6; // px of travel that still counts as a tap, not a drag
const FLING_MIN = 0.08; // px/ms release speed floor to seed a fling coast
const FLING_STOP = 0.02; // px/ms speed at which a coast ends
const FLING_FRICTION = 0.94; // velocity kept per 60fps frame of coast
const FLING_WINDOW = 100; // ms of recent moves averaged for the release velocity

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

// Results-screen markup: a label, the key chips, and the carousel track
function missedMarkup(items, perfect) {
    const chips = items.map(({card, count}) =>
        `<button type="button" class="missedChip" data-key="${card.key}" onclick="centerMissed('${card.key}')">${card.key}${count > 1 ? `(${count})` : ''}</button>`).join('');
    const cards = items.map(({card}) =>
        `<div class="missedCard" data-key="${card.key}">${diagramFace(card.image, card, false, true)}</div>`).join('');
    return `<div id="missedSection">
                <div class="label">${perfect ? 'Perfect' : 'Missed Cards'}</div>
                <div id="missedChips">${chips}</div>
                <div id="missedCarousel"><div id="missedTrack">${cards}</div></div>
            </div>`;
}

let missedCarousel = null; // Active controller, self-stops when the results screen leaves the DOM

// A chip tap centers its real card (no-op while the strip already fits)
function centerMissed(key) {
    missedCarousel.centerKey(key);
}

// Wire the carousel once the card images have sized, so the loop width is measured true
function initMissedCarousel(items) {
    const carousel = document.getElementById('missedCarousel');
    const track = document.getElementById('missedTrack');
    const chips = [...document.getElementById('missedChips').children];
    const reals = [...track.children];
    const keyIndex = (key) => items.findIndex(entry => entry.card.key === key);

    // Scroll + focus state
    let pos = 0; // px scrolled left, sub-pixel
    let looping = false; // temporary seam loop, granted by a grab made mid-drift
    let drifting = false, gliding = false;
    let held = null; // pinned / edge-snapped focus, held until drift recenters it
    let focusIndex = null, litIndex = null; // Chip to light / chip currently lit
    let driftHandle = 0, glideHandle = 0, idleHandle = 0, lastTs = 0;
    let velocity = 0, coasting = false, momentumHandle = 0, momentumTs = 0, samples = [];

    // Geometry, filled by measure()
    let viewW = 0, loopW = 0, clampMax = 0, overflow = false, cloned = false, centers = [];

    const render = () => track.style.transform = `translateX(${-pos}px)`;
    const alive = () => track.isConnected; // false once finish/New Session/Replay wipes the arena
    const paint = () => { render(); updateHighlight(); }; // Apply pos to the DOM: transform + lit chip

    // View + loop geometry, re-run on every resize. Clones build once, the rest re-measures
    function measure() {
        viewW = carousel.clientWidth;
        const origin = reals[0].offsetLeft;
        const contentW = reals.at(-1).offsetLeft + reals.at(-1).offsetWidth - origin;
        centers = reals.map(card => card.offsetLeft + card.offsetWidth / 2 - origin);
        const gainedOverflow = contentW > viewW + 1 && !overflow; // fit -> overflow, (re)start drift
        overflow = contentW > viewW + 1;
        clampMax = Math.max(0, contentW - viewW);
        carousel.classList.toggle('overflowing', overflow); // left-align + grab cursor when scrollable

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
        else if (drifting || looping) { while (loopW && pos >= loopW) pos -= loopW; }
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

    // Apply a scroll delta under the clamp model: hard clamp by default, temporary loop only at the seam
    function manualScroll(delta) {
        if (!overflow) return;
        if (pos > clampMax) looping = true; // grabbed within the drift seam region
        let next = pos + delta;
        if (looping) {
            while (next >= loopW) next -= loopW; // forward across the seam keeps looping
            if (next < 0) next = 0; // never loop backward past the first card
            if (delta < 0 && next <= clampMax) looping = false; // seam left to the left, hard clamp returns
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

    function startDrift() {
        if (!overflow || !alive() || gliding || coasting) return;
        looping = false; // a manual-only state, surrendered once drift owns the scroll
        // Carry an off-center pin / edge focus into a hold so drift does not flash it away
        const centered = centeredIndex();
        if (focusIndex !== null && focusIndex !== centered) held = focusIndex;
        drifting = true;
        lastTs = 0;
        driftHandle = requestAnimationFrame(driftFrame);
    }

    function driftFrame(now) {
        if (!alive()) return cancelDrift();
        const dt = lastTs ? Math.min(now - lastTs, FRAME_MAX_STEP) : 0;
        lastTs = now;
        pos += DRIFT_SPEED * dt / 1000; // sub-pixel so hi-DPI phones do not judder
        while (pos >= loopW) pos -= loopW;
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
            else { gliding = false; scheduleDrift(); }
        };
        glideHandle = requestAnimationFrame(step);
    }

    function centerKey(key) {
        const i = keyIndex(key);
        if (!overflow) return;
        held = i; // pin the highlight to the tapped card
        glideTo(clamp(centers[i] - viewW / 2, 0, clampMax));
    }

    // The real card key under a pointer, mapping any clone back to its real card
    const keyAt = (event) => event.target.closest('.missedCard')?.dataset.key ?? null;

    // Pointer drag (mouse) + swipe (touch); touch-action keeps vertical as page scroll
    let dragging = false, downKey = null, lastX = 0, moved = 0;
    carousel.addEventListener('pointerdown', event => {
        if (!overflow) return;
        cancelMomentum(); // a fresh grab takes over any coast in progress
        cancelGlide(); // and any in-flight tap-to-center glide
        interact();
        held = null; // a fresh grab releases a pin / edge snap
        dragging = true;
        moved = 0;
        lastX = event.clientX;
        samples = [{t: performance.now(), x: event.clientX}];
        downKey = keyAt(event);
        carousel.classList.add('grabbing');
        carousel.setPointerCapture(event.pointerId);
    });
    carousel.addEventListener('pointermove', event => {
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
        carousel.classList.remove('grabbing');
        carousel.releasePointerCapture(event.pointerId);
        if (moved <= TAP_SLOP && downKey !== null) return centerKey(downKey); // a clean press is a tap-to-center
        if (!startMomentum()) scheduleDrift(); // a fling coasts (and self-schedules drift), else idle now
    };
    carousel.addEventListener('pointerup', endDrag);
    carousel.addEventListener('pointercancel', endDrag);

    // Vertical wheel scrolls the horizontal strip (down = right)
    carousel.addEventListener('wheel', event => {
        if (!overflow) return;
        event.preventDefault();
        cancelMomentum();
        cancelGlide();
        held = null;
        interact();
        manualScroll(event.deltaY);
    }, {passive: false});

    // Dragging a diagram scrolls the strip rather than ghosting the image
    carousel.addEventListener('dragstart', event => event.preventDefault());

    missedCarousel = {centerKey};

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
            ro.observe(carousel); // re-measure loop width + clamp when the window/phone resizes
        }));
}
