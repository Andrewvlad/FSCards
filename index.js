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
    '2-way':     _2Way,
    '4-way':     _4Way,
    '6-way':     _6Way,
    '8-way':     _8Way,
    '10-way':    _10Way,
    '16-way':    _16Way,
    '2-way-vfs': _2WayVfs,
    '4-way-vfs': _4WayVfs,
    '2-way-mfs': _2WayMfs,
    '2-way-cf':  _2WayCf,
    '4-way-cf':  _4WayCf,
    'cp-freestyle': _CpFreestyle,
};

const isBlock = (key) => !isNaN(key);

// A discipline offers the Randoms/Blocks split only when its pool has both numbered and
// lettered entries. 10-way (numbered only) has no split, so it ignores the category filter.
function categorized(discipline) {
    const keys = Object.keys(DATA[discipline].names);
    return keys.some(isBlock) && keys.some(key => !isBlock(key));
}

// USPA fallback
function activeImageSet(discipline, imageSet) {
    return imageSet in DATA[discipline].sets ? imageSet : 'USPA';
}

function poolImages({discipline, indoor, imageSet}) {
    const data = DATA[discipline];
    const set = activeImageSet(discipline, imageSet);
    const filename = data.sets[set];
    const dir = `assets/diagrams/${discipline}/${setDisplayName(discipline, set, indoor)}`;
    const images = {};
    for (const key of Object.keys(data.names))
        images[key] = `${dir}/${filename ? filename(key, indoor) : `${key}.webp`}`;
    return images;
}

// Swaps USPA indoor to USIS
function setDisplayName(discipline, imageSet, indoor) {
    return (indoor && DATA[discipline].indoorSets?.[imageSet]) || imageSet;
}

// Not inversion-friendly
// TODO: Try out different methods
const DARK_PAPER_USPA = new Set(['4-way-vfs', 'cp-freestyle']);

function diagramInvertsInDark(discipline, imageSet, indoor) {
    const data = DATA[discipline];
    const set = setDisplayName(discipline, imageSet in data.sets ? imageSet : 'USPA', indoor);
    return ['USPA', 'USIS', 'FAI'].includes(set) && !DARK_PAPER_USPA.has(discipline);
}

// Text-free card variant used for the front
const figureFor = (path) => path.replace(/\/([^/]+)$/, '/figures/$1');

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
function buildPool({discipline, indoor, imageSet, classLevel, tunnel, includeFusions = true}) {
    const images = poolImages({discipline, indoor, imageSet});
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
const SHARED_FIELDS = ['discipline', 'category', 'classLevel', 'indoor', 'tunnel', 'includeFusions', 'imageSet'];

function saveShared(state) {
    try {
        const shared = {};
        for (const field of SHARED_FIELDS) shared[field] = state[field];
        localStorage.setItem(SHARED_STORE, JSON.stringify(shared));
    } catch (e) {} // Storage may be unavailable
}

function loadShared() {
    try { return JSON.parse(localStorage.getItem(SHARED_STORE)); }
    catch (e) { return null; } // Unavailable or malformed
}
