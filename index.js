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
    '4-way':     _4Way,
    '8-way':     _8Way,
    '10-way':    _10Way,
    '16-way':    _16Way,
    '4-way-vfs': _4WayVfs,
    '2-way-mfs': _2WayMfs,
};

const isBlockKey = (key) => !isNaN(key);

// A discipline offers the Randoms/Blocks split only when its pool has both numbered and
// lettered entries. 10-way (numbered only) has no split, so it ignores the category filter.
function categorized(discipline) {
    const keys = Object.keys(DATA[discipline].names);
    return keys.some(isBlockKey) && keys.some(key => !isBlockKey(key));
}

function poolImages({discipline, indoor, imageSet}) {
    const data = DATA[discipline];
    const set = imageSet in data.sets ? imageSet : 'USPA';
    const filename = data.sets[set];
    const dir = `assets/diagrams/${discipline}/${set}`;
    const images = {};
    for (const key of Object.keys(data.names))
        images[key] = `${dir}/${filename ? filename(key, indoor) : `${key}.webp`}`;
    return images;
}

// Text-free card variant used for the front
const figureFor = (path) => path.replace(/\/([^/]+)$/, '/figures/$1');

function imageSetsFor(discipline) {
    return Object.keys(DATA[discipline].sets);
}

function videoFor(discipline, key) {
    return DATA[discipline].videos?.[key];
}

// 'R' is a CISM-only random.
const OPT_IN_KEYS = {
    '4-way': ['R'],
};

// Build the class-scoped pool (all eligible cards, unshuffled) as key -> card.
function buildPool({discipline, indoor, imageSet, classLevel}) {
    const images = poolImages({discipline, indoor, imageSet});
    const names = DATA[discipline].names;

    const cls = classesFor(discipline).find(c => c.key === classLevel) ?? {};

    const keys = Object.keys(images);
    const optIn = OPT_IN_KEYS[discipline] ?? [];
    const blocks  = cls.blocks  ?? keys.filter(isBlockKey);
    const randoms = cls.randoms ?? keys.filter(k => !isBlockKey(k) && !optIn.includes(k));

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

function buildDeck(settings) {
    return randomizeDeck(Object.values(buildPool(settings)));
}

// Rebuild a deck in its saved key order, dropping any keys that no longer exist
function deckFromKeys(keys, settings) {
    const pool = buildPool(settings);
    return keys.map(k => pool[k]).filter(Boolean);
}
