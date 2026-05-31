// Fisher-Yates shuffle (returns a new array)
function randomizeDeck(deck) {
    const shuffled = deck.slice();
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
}

// Per-discipline data — formation names, competition classes, and image sets — is defined
// alongside the diagrams in assets/diagrams/<discipline>/index.js (loaded before this file).
// Collect those globals into one registry keyed by discipline.
const DATA = {
    '4-way':     _4Way,
    '8-way':     _8Way,
    '10-way':    _10Way,
    '16-way':    _16Way,
    '4-way-vfs': _4WayVfs,
    '2-way-mfs': _2WayMfs,
};

// Blocks/formations are numbered, randoms lettered — so a numeric key is a block.
const isBlockKey = (key) => !isNaN(key);

// A discipline offers the Randoms/Blocks split only when its pool has both numbered and
// lettered entries. 10-way (numbered only) has no split, so it ignores the category filter.
function categorized(discipline) {
    const keys = Object.keys(DATA[discipline].names);
    return keys.some(isBlockKey) && keys.some(key => !isBlockKey(key));
}

// Text-free "figure-only" variant used as the diagram-front prompt (so the printed name
// and letter/number don't give away the answer). Every diagram has one under a `figures/`
// subdir alongside it.
const figureFor = (path) => path.replace(/\/([^/]+)$/, '/figures/$1');

function poolImages({discipline, outdoor, imageSet}) {
    const data = DATA[discipline];
    const set = imageSet in data.sets ? imageSet : 'USPA';
    const filename = data.sets[set];
    const dir = `assets/diagrams/${discipline}/${set}`;
    const images = {};
    for (const key of Object.keys(data.names))
        images[key] = `${dir}/${filename ? filename(key, outdoor) : `${key}.webp`}`;
    return images;
}

// Diagram sets available for a discipline, in display order (mirrors its subdirectories).
function imageSetsFor(discipline) {
    return Object.keys(DATA[discipline].sets);
}

// Keys present in a discipline's diagrams but excluded from the default pool — shown only
// when a class lists them explicitly. 4-way's 'R' (Bundy) is a CISM-only random.
const OPT_IN_KEYS = {
    '4-way': ['R'],
};

// Build the class-scoped pool (all eligible cards, unshuffled) as key -> card.
function buildPool({discipline, outdoor, imageSet, classLevel}) {
    const images = poolImages({discipline, outdoor, imageSet});
    const names = DATA[discipline].names;

    // The chosen class narrows the pool; class-less disciplines (10-way, 16-way) yield {}, no narrowing.
    const cls = classesFor(discipline).find(c => c.key === classLevel) ?? {};

    // Numbered keys are blocks/formations, lettered keys randoms; each list defaults to every
    // such key in the image map. A class may narrow either, and opt-in keys (4-way 'R') are
    // left out of the default unless the class names them.
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
            figure: figureFor(images[key]), // text-free prompt for diagram-front
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
