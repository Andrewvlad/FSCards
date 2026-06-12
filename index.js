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
