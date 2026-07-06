// Run machinery shared by the Flashcards and Quiz views, loaded after shared.js
// Pages define: SAVE_KEY, nextCard, finish, frontFace, fullsOf, cardIdle, ownSettings + applyOwnSettings

/** Run state **/
const correct = document.getElementById('statCorrect');
const wrong = document.getElementById('statWrong');
const streak = document.getElementById('statStreak');
const progress = document.getElementById('statCard');
const progressCount = document.getElementById('progressCount');
const getIndex = () => +correct.textContent + +wrong.textContent;
const runComplete = () => !endless && getIndex() >= deck.length; // Endless never completes
const hasScored = () => getIndex() > 0; // A graded answer commits the run (skip doesn't)

function setProgress(text) {
    progress.textContent = text;
    progressCount.textContent = `(${text})`;
}

let fullDeck = [];
let deck = [];
let flipped = false;
let recycle = false;
let endless = false;
let currentCard = null; // The formation on screen (needed for endless)
let missed = {};

const recycleToggle = document.getElementById('recycleToggle');

// The settings object every deck/image build takes. Split tracks the viewport at call time
const poolSettings = () => ({discipline, indoor, classLevel, imageSet, tunnel, includeFusions, split: splitView});

/** Save progress **/
// Save after each grading. A run persists only once it has been played (hasScored), so browsing
// other modes never overwrites the stored run - the cross-page filter mirror below still runs
function saveSession() {
    if (hasScored() && !runComplete()) try {
        localStorage.setItem(SAVE_KEY, JSON.stringify({ // Can only store string data
            deck:    deck.map(f => f.key), // Store formation keys (letters/numbers)
            correct: correct.textContent,
            wrong:   wrong.textContent,
            streak:  streak.textContent,
            discipline,
            category,
            classLevel,
            indoor,
            tunnel,
            includeFusions,
            imageSet,
            recycle,
            endless,
            // Endless engine progress, so a strategy switch / resume keeps its weights + mastery
            weights,
            masteredKeys,
            unlockedCount,
            missed,
            ...ownSettings(),
        }));
    } catch(e) {} // Fail silently if storage full or unavailable

    // Mirror the pool/image filters into the cross-page store the gallery also reads
    saveShared({discipline, category, classLevel, indoor, tunnel, includeFusions, imageSet, invert});
}

function loadSession() {
    try {
        const data = storedRun(); // This page's run

        const shared = loadShared(); // Filters, also written by the gallery

        // Page-own settings restore even when the pool won't resume
        if (data) {
            applyOwnSettings(data);
            recycle = data.recycle ?? false;
            endless = data.endless ?? false;
        }

        if (shared ?? data) applySharedFilters(shared ?? data);

        syncSettingsUI();

        // On load, shared (cross-page filters) overrides the run's pool, so resume only when they agree
        if (!data || !data.deck?.length || (shared && !poolMatches(data)) || !restoreRun(data)) return false;

        showToast('Resumed');
        return true;
    } catch(e) {return false;}
}

// Load a stored run into memory, the shared core plus this page's own settings
function restoreRun(data) {
    if (!restoreRunCore(data)) return false;
    applyOwnSettings(data);
    prefetchDeck();
    return true;
}

// Only clear when game complete. Progress in a new mode will override
function clearSession() {
    try {
        localStorage.removeItem(SAVE_KEY);
    } catch(e) {} // Fail silently if storage unavailable
}

/** Filter fallout (the chrome hooks): resume the stored run when it matches, else rebuild **/
function disciplineChanged() {
    // Land on the played class before updateDisciplineUI resets it to the discipline default
    const run = storedRun();
    if (run?.discipline === discipline) classLevel = run.classLevel;
    updateDisciplineUI();
    switchDeck(newDeck);
}

function poolChanged() {
    switchDeck(newDeck);
}

function categoryChanged() {
    switchDeck(applyCategory);
}

function imagesChanged() {
    hotSwapImages();
}

/** Define deck **/
function newDeck() {
    fullDeck = buildDeck(poolSettings());
    applyCategory();
}

// Derive the played deck from fullDeck by category (no reshuffle) and restart the run
function applyCategory() {
    // Pools without the blocks/randoms split show everything
    deck = categorized(poolSettings()) ? fullDeck.filter(matchesCategory) : [...fullDeck];
    rebuildEndlessState();
    missed = {};
    prefetchDeck();

    correct.textContent = '0';
    wrong.textContent = '0';
    streak.textContent = '0';
    window.resetTimer?.(); // Quiz stopwatch

    saveSession();
    nextCard();
}

// Warm each diagram URL at most once a session (set swaps / resizes re-call this)
const warmed = new Set();
function prefetchDeck() {
    // Current card loads at render (swapToFullImage); warm the rest upcoming-first, all thumbs then all full-res
    const idx = currentCard ? deck.findIndex(c => c.key === currentCard.key) : -1;
    const ordered = [...deck.slice(idx + 1), ...deck.slice(0, Math.max(idx, 0))];
    const thumbsOf = (card) => fullsOf(card).filter(u => !u.endsWith('.svg')).map(thumbFor);
    const queue = [...ordered.flatMap(thumbsOf), ...ordered.flatMap(fullsOf)].filter(u => !warmed.has(u));
    if (!queue.length) return;
    queue.forEach(u => warmed.add(u));
    // Sequential so the ordering holds and a flaky link warms one at a time instead of flooding
    const warm = async () => {
        for (const url of queue) {
            const res = await fetch(url, {priority: 'low'}).catch(() => null);
            if (res?.ok && !url.includes('/thumbs/')) loadedFulls.add(url); // full now cached, no thumb needed
        }
    };
    if (window.requestIdleCallback) requestIdleCallback(warm);
    else setTimeout(warm);
}

// Re-point every card's diagram at the current set/indoor without rebuilding the deck
function hotSwapImages() {
    const images = poolImages(poolSettings());
    for (const card of fullDeck) { card.image = images[card.key]; card.figure = figureFor(images[card.key]); }
    for (const card of deck)     { card.image = images[card.key]; card.figure = figureFor(images[card.key]); }

    if (currentCard && cardIdle()) renderCardFaces(currentCard);
    prefetchDeck(); // re-warm the cache for the swapped-in set

    saveSession();
}

/** Create card **/
const arena = document.getElementById('arena');

const SPLIT_RATIO = 2; // Cards at least twice as wide as tall show blocks as side-by-side panels
const SEAM_MARGIN = 0.0035;

// Add captions to images
function diagramFace(src, formation, hideCaption) {
    if (!includeCaption(discipline)) {
        // When the card renders wide, show a block's three panels as separate horizontally arranged images
        const cuts = splitView && isBlock(formation.key) && panelCutsFor(src);
        if (cuts) {
            const fallback = SINGLE_PANEL_BLOCKS.has(activeImageSet(discipline, imageSet));
            const [ar, d1t, d1b, d2t, d2b] = cuts;
            const windows = [[0, d1t - SEAM_MARGIN], [d1b + SEAM_MARGIN, d2t - SEAM_MARGIN], [d2b + SEAM_MARGIN, 1]];
            const grows = windows.map(([t, b]) => 1 / (b - t));
            const panels = windows.map(([t, b], i) =>
                `<img class="diagram" ${lazySrc(src)} alt="" style="flex-grow: ${grows[i].toFixed(4)}; object-position: 50% ${(100 * t / (1 - b + t)).toFixed(3)}%">`).join('');
            return `<div class="splitDiagram"${fallback && invert ? ' data-diagram="dark"' : ''} role="img" aria-label="${formation.key}"
                        style="aspect-ratio: ${(ar * grows.reduce((s, g) => s + g)).toFixed(4)}">${panels}</div>`;
        }
        return `<img class="diagram" ${lazySrc(src)} alt="${formation.key}">`;
    }
    return `<figure class="captionedDiagram">
                <img class="diagram" ${lazySrc(src)} alt="${formation.key}">
                <figcaption${hideCaption ? ' class="captionHidden"' : ''}>${formation.name}</figcaption>
            </figure>`;
}

// Build the two card faces. Re-render split-block images
function renderCardFaces(formation) {
    document.querySelector('#card .front').innerHTML = frontFace(formation);
    document.querySelector('#card .back').innerHTML = `
        <div class="cardContent thumbLoading">
            ${diagramFace(formation.image, formation, false)}
        </div>
    `;

    // Pre-decode the backside image
    document.querySelector('#card .back .diagram')?.decode?.().catch(() => {});
}

// Crossing the threshold changes split markup and, for single-panel sets, image resolution
let splitView = false;
const cardObserver = new ResizeObserver(([entry]) => {
    const {width, height} = entry.contentRect;
    if (!height) return; // Detached card on results screen reports zero

    arena.style.setProperty('--cardH', height + 'px'); // Anchors the quiz report FAB to the card's bottom edge

    const split = width >= SPLIT_RATIO * height;
    if (split === splitView) return;

    splitView = split;
    hotSwapImages();
});

/** Grade + results **/
const MAX_ROT = 20; // Max degrees of card rotation
const SWIPE_DURATION = 300; // Number of milliseconds that the swipe animation will play

// Score a graded answer: stats, recycle, missed tally, endless feedback
function applyGrade(direction) {
    if (direction) { // Correct
        correct.textContent++;
        streak.textContent++;
    } else { // Wrong
        if (!endless && recycle) deck.push(currentCard);
        missed[currentCard.key] = (missed[currentCard.key] ?? 0) + 1;
        wrong.textContent++;
        streak.textContent = '0';
    }
    if (endless) endlessResult(currentCard.key, direction);
}

const restartActionBar = `<button id="restart" onclick="newDeck()">Play Again</button>`;
const replayActionBar = `<button id="replay" onclick="replayMissed()">Replay Missed</button>`;

// Results screen: missed-card (or full-deck) carousel plus the restart actions
function showResults() {
    const missedItems = collectMissed();
    const perfect = !missedItems.length;
    const items = perfect ? allDeckItems() : missedItems;

    setProgress('✓');
    document.getElementById('progressFill').style.width = '100%';
    arena.innerHTML = `
        <div id="done">
            ${carouselMarkup(items, perfect ? 'Perfect' : 'Missed Cards')}
            <div id="actionBar">${perfect ? '' : replayActionBar}${restartActionBar}</div>
        </div>
    `;
    initCarousel(items);
}

// Replay just the missed cards as a fresh finite run
function replayMissed() {
    const cards = collectMissed().map(entry => entry.card);
    deck = randomizeDeck(cards);
    missed = {};
    rebuildEndlessState();
    prefetchDeck();
    correct.textContent = wrong.textContent = streak.textContent = '0';
    window.resetTimer?.(); // Quiz stopwatch
    saveSession();
    nextCard();
}

/** Endless mode **/
// Swap between a finite deck and an endless draw (defaults to random)
function toggleEndless() {
    endless = endless ? false : 'random';
    syncEndlessUI();
    // Resume stored run only if its endless-ness matches the new toggle
    switchDeck(newDeck, run => !!run.endless === !!endless);
}

// Switch the endless draw strategy
function selectStrategy(button) {
    selectSegment('strategyRow', button);
    endless = button.dataset.strategy;
    // Resume only a stored run of the same strategy
    switchDeck(newDeck, run => run.endless === endless);
}

function syncEndlessUI() {
    const toggle = document.getElementById('endlessToggle');
    toggle.classList.toggle('active', endless);
    toggle.setAttribute('aria-pressed', !!endless);

    document.querySelectorAll('#strategyRow [data-strategy]').forEach(button =>
        button.classList.toggle('active', button.dataset.strategy === endless));

    // Recycle does not matter in endless mode
    document.getElementById('recycleSetting')
        .classList.toggle('hidden', endless);

    fitStrategyRow();
}

// Keep endless strategy options inline with stats, otherwise fall back into a drawer
function fitStrategyRow() {
    const row = document.getElementById('strategyRow');
    const content = document.getElementById('drawerContent');
    const drawer = document.getElementById('endlessDrawer');

    if (!endless) { // Early exit
        if (row.parentElement !== content) content.prepend(row);
        drawer.classList.add('hidden');
        return;
    }

    const statsRow = document.getElementById('statsRow');
    const container = document.getElementById('progressContainer');

    if (row.nextElementSibling !== container) document.getElementById('statsBar').insertBefore(row, container);
    const fits = statsRow.scrollHeight <= statsRow.clientHeight + 1 // Early check - multi-lined stats (hidden overflow) = no room
        && container.getBoundingClientRect().top < statsRow.getBoundingClientRect().bottom;
    if (!fits && row.parentElement !== content) content.prepend(row);

    drawer.classList.toggle('hidden', fits);
}
new ResizeObserver(fitStrategyRow).observe(document.body);
document.fonts.ready.then(fitStrategyRow);

function setDrawer(open) {
    document.getElementById('drawerContent').classList.toggle('hidden', !open);
    document.getElementById('drawerCaret').setAttribute('aria-expanded', open);
}

function toggleDrawer() {
    setDrawer(document.getElementById('drawerContent').classList.contains('hidden'));
}

// Body grows by the open drawer's height so the arena never resizes (mirrors --panelH)
new ResizeObserver(([entry]) => {
    document.body.style.setProperty('--drawerH', `${entry.borderBoxSize[0].blockSize}px`);
}).observe(document.getElementById('drawerContent'));

// Strategy tunables
const MASTERY_STREAK = 2;
const UNLEARNED_WEIGHT = 3;
const MISS_MULTIPLIER = 2.2;
const HIT_MULTIPLIER = 0.55;
const WEIGHT_MIN = 0.4, WEIGHT_MAX = 6;

// Engine state
let weights = {};
let learnKeys = [];
let unlockedCount = 6;
let masteredKeys = {}; // reset key's value on miss

function rebuildEndlessState(saved) {
    weights = saved?.weights ?? {};
    masteredKeys = saved?.masteredKeys ?? {};

    // Initialize learn props (or resume)
    if (endless === 'learn') {
        learnKeys = deck.map(card => card.key).sort((a, b) => isBlock(a) - isBlock(b));
        unlockedCount = saved?.unlockedCount ?? Math.min(6, learnKeys.length);
    }
}

// Pick the next card by the active strategy
function pickEndlessCard() {
    switch (endless) {
        case 'adaptive': return pickAdaptive();
        case 'learn':    return pickLearn();
        default:         return pickRandom();
    }
}

// Fold a graded answer back into the active strategy's state
function endlessResult(key, correct) {
    switch (endless) {
        case 'adaptive': return adaptiveResult(key, correct);
        case 'learn':    return learnResult(key, correct);
    }
}

// No back-to-back repeats
const notLast = (pool) => pool.filter(card => card.key !== currentCard?.key);
const learned = (key) => (masteredKeys[key] ?? 0) >= MASTERY_STREAK;

function weightedPick(cards, weightOf) {
    let r = Math.random() * cards.reduce((sum, card) => sum + weightOf(card), 0);
    return cards.find(card => (r -= weightOf(card)) <= 0) ?? cards.at(-1);
}

// Random (uniform draw)
function pickRandom() {
    const pool = notLast(deck);
    return pool[Math.floor(Math.random() * pool.length)];
}

// Adaptive (weight toward missed cards)
function pickAdaptive() {
    return weightedPick(notLast(deck), card => weights[card.key] ?? 1);
}
function adaptiveResult(key, correct) {
    weights[key] = clamp((weights[key] ?? 1) * (correct ? HIT_MULTIPLIER : MISS_MULTIPLIER), WEIGHT_MIN, WEIGHT_MAX);
}

// Learn (draw from the unlocked cross-section and slowly add new cards to pool)
function pickLearn() {
    const unlocked = new Set(learnKeys.slice(0, unlockedCount));
    const live = deck.filter(card => unlocked.has(card.key));
    return weightedPick(notLast(live), card => learned(card.key) ? 1 : UNLEARNED_WEIGHT);
}
function learnResult(key, correct) {
    masteredKeys[key] = correct ? (masteredKeys[key] ?? 0) + 1 : 0;
    if (!correct) return; // A miss only zeroes mastery, never completes the slice

    // Expand the slice by one once the whole unlocked slice is learned
    if (unlockedCount < learnKeys.length && learnKeys.slice(0, unlockedCount).every(learned)) unlockedCount++;
}
