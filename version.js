// MUST BE BUMPED FOR ANY CHANGE TO PROPOGATE TO INSTALLED/CACHED VERSIONS

/*
Updates:
    - Major: Large changes, requires opt-in (new mode/dicipline)
    - Minor: Small features, automatically installed (new filters)
    - Patch: Minor fixes and adjustments, automatically installed (CSS changes)
    - Image changes do not bump the version, rather bump their respective manifest
*/
const APP_VERSION = '1.0.0';

// Major updates require banner consent (offline.js), while smaller updates apply silently (sw.js)
const majorOf = (version) => version.split('.')[0];

// Cache identity shared across the SW/page boundary (sw.js serves, shared.js sizes and prunes)
const SHELL_PREFIX = 'fsc-shell-v';
const SHELL_CACHE = SHELL_PREFIX + APP_VERSION;
const SET_CACHE = 'fsc-sets'; // User-downloaded image sets, written page-side, served local-first
const BROWSE_CACHE = 'fsc-browse'; // Opportunistic browse retention the SW fills, pruned page-side

// Discipline keys, one per-discipline data file each in the offline shell
const DISCIPLINES = [
    '2-way',
    '4-way',
    '6-way-speed',
    '8-way',
    '10-way-speed',
    '16-way',
    '2-way-vfs',
    '4-way-vfs',
    '2-way-mfs',
    '2-way-cf',
    '4-way-cf',
    'cp-freestyle',
];

// Necessary files for offline shell (sw.js captures, offline.js verifies the capture on install)
const SHELL = [
    '',
    'cards/',
    'gallery/',
    'quiz/',
    '404.html',
    'stylesheet.css',
    'index.js',
    'shared.js',
    'play.js',
    'offline.js',
    'version.js',
    'manifest.webmanifest',
    'favicon.ico',
    'apple-touch-icon.png',
    'assets/icons/icon-192.png',
    'assets/icons/icon-512.png',
    'assets/icons/icon-maskable-192.png',
    'assets/icons/icon-maskable-512.png',
    'assets/icons/icon-maskable-1024.png',
    'assets/diagrams/panel-cuts.js',
    ...DISCIPLINES.map(disc => `assets/diagrams/${disc}/index.js`),
];
