// FSCards service worker: offline shell + image caches + update lanes (see version.js)
// Path-relative throughout so the site works at / locally and under /<repo>/ on Pages
importScripts('version.js');

const FONT_CACHE = 'fsc-fonts'; // Shell cache names live in version.js, shared with the pages

const IMAGE_TIMEOUT = 4000; // ms a cached image waits on a slow network before serving local

const scopeUrl = new URL(self.registration.scope); // Origin + path prefix, / locally and /<repo>/ on Pages
const shellUrl = (path) => new URL(path, scopeUrl).href;

// Opened once per worker start instead of per request (no SET_CACHE handle - the pages
// delete and recreate that cache, which would strand a held reference)
const fontCache = caches.open(FONT_CACHE);
const browseCache = caches.open(BROWSE_CACHE);
const shellCache = caches.open(SHELL_CACHE);

// The pages' Google Fonts stylesheets, scanned from the just-captured docs so a page's
// font-link edit can't drift from what install captures
async function fontCssUrls(cache) {
    const docs = SHELL.filter(path => !path.includes('.') || path.endsWith('.html'));
    const pages = await Promise.all(docs.map(async path => (await cache.match(shellUrl(path)))?.text() ?? ''));
    return [...new Set(pages.flatMap(html => [...html.matchAll(/href="(https:\/\/fonts\.googleapis\.com[^"]+)"/g)].map(m => m[1])))];
}

// Fetch and store one shell entry, revalidating past the HTTP cache so a new version's
// capture can't seed itself with stale files
async function captureShellEntry(cache, path) {
    const res = await fetch(shellUrl(path), {cache: 'no-cache'});
    if (res.ok) await cache.put(shellUrl(path), res);
}

// One missing or renamed asset must not abort capturing the rest
async function captureShell(cache, paths) {
    await Promise.allSettled(paths.map(path => captureShellEntry(cache, path)));
}

// Store the font stylesheets with their woff2 files so fonts survive a first visit that
// predates SW control
async function captureFonts(urls) {
    const cache = await fontCache;
    await Promise.allSettled(urls.map(async url => {
        const res = await fetch(url);
        if (!res.ok) return;
        const css = await res.clone().text();
        await cache.put(url, res);
        // Each font file referenced by the stylesheet
        const files = [...css.matchAll(/url\((https:[^)]+)\)/g)].map(m => m[1]);
        await Promise.allSettled(files.map(async file => {
            if (await cache.match(file)) return;
            const font = await fetch(file);
            if (font.ok) await cache.put(file, font);
        }));
    }));
}

self.addEventListener('install', event => {
    event.waitUntil((async () => {
        const cache = await shellCache;
        await captureShell(cache, SHELL);
        await captureFonts(await fontCssUrls(cache));

        // Minor and patch updates apply silently. A major waits for banner consent
        // (page posts SKIP_WAITING), judged against whichever shell version is installed
        const oldShell = (await caches.keys()).find(name => name.startsWith(SHELL_PREFIX) && name !== SHELL_CACHE);
        const oldVersion = oldShell?.slice(SHELL_PREFIX.length);
        if (!oldVersion || majorOf(oldVersion) === majorOf(APP_VERSION)) self.skipWaiting();
    })());
});

self.addEventListener('activate', event => {
    event.waitUntil((async () => {
        // Drop superseded shell versions, then take the open pages
        const names = await caches.keys();
        await Promise.all(names.filter(name => name.startsWith(SHELL_PREFIX) && name !== SHELL_CACHE).map(name => caches.delete(name)));
        await self.clients.claim();

        // Self-heal a partial capture (single 404 at install, eviction) without failing activation
        const cache = await shellCache;
        const cached = new Set((await cache.keys()).map(req => req.url));
        const missing = SHELL.filter(path => !cached.has(shellUrl(path)));
        if (missing.length) await captureShell(cache, missing);
    })());
});

self.addEventListener('message', event => {
    if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
    if (event.data?.type === 'GET_VERSION') event.source?.postMessage({type: 'VERSION', version: APP_VERSION});
});

// Race the network against a bound, resolving to null on failure or timeout while the
// fetch itself keeps running (its result still refreshes the browse cache)
function bounded(promise, ms) {
    return Promise.race([promise, new Promise(resolve => setTimeout(() => resolve(null), ms))]).catch(() => null);
}

// Diagram images: downloaded sets serve local first (instant, consistent, saves data), everything
// else is network-first so online users see current art, falling back to browse retention offline or past the slow bound
async function serveImage(request, event) {
    // A page-side download/refresh bypasses local copies to pull current bytes
    const bypass = request.cache === 'reload' || request.cache === 'no-cache';

    if (!bypass) {
        const saved = await caches.match(request, {cacheName: SET_CACHE});
        if (saved) return saved;
    }

    const network = fetch(request);
    // Retention write registered while the event is live, so a slow resolve past the timeout still lands (a waitUntil from a late .then throws on the dead event)
    if (!bypass) event.waitUntil(network.then(res => res.ok ? browseCache.then(cache => cache.put(request, res.clone())) : null).catch(() => {})); // Storage may be unavailable

    // Fallback looked up while the network request is already in flight
    const cached = bypass ? null : await (await browseCache).match(request);
    if (!cached) return network;
    // A bad HTTP status resolves rather than rejects, so keep the cached copy over an error response
    const net = await bounded(network, IMAGE_TIMEOUT);
    return net?.ok ? net : cached;
}

// Shell files (and any other same-origin asset): current shell cache first, network behind
// it, opportunistically re-capturing shell entries a partial install missed
async function serveShell(request) {
    const cached = await (await shellCache).match(request, {ignoreSearch: true});
    if (cached) return cached;

    const res = await fetch(request);
    const path = new URL(request.url).pathname.slice(scopeUrl.pathname.length);
    if (res.ok && SHELL.includes(path)) await (await shellCache).put(shellUrl(path), res.clone());
    return res;
}

// Navigations ride the shell lane, so a doc a partial install missed re-captures too
async function serveNavigation(request) {
    try {
        return await serveShell(request);
    } catch (e) {
        // Unknown route offline: the captured 404 page (its forwarder still resolves cached views)
        const notFound = await (await shellCache).match(shellUrl('404.html'));
        if (notFound) return notFound;
        throw e;
    }
}

async function serveFont(request, event) {
    const cache = await fontCache;
    const cached = await cache.match(request);
    // Stale-while-revalidate: fonts change rarely and a stale one renders fine
    const network = fetch(request).then(async res => {
        if (res.ok) await cache.put(request, res.clone());
        return res;
    }).catch(() => null);
    event.waitUntil(network); // Refresh rides the event lifetime, not dropped if the worker is killed
    return cached ?? await network ?? Response.error();
}

self.addEventListener('fetch', event => {
    const request = event.request;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);

    if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') {
        event.respondWith(serveFont(request, event));
        return;
    }
    if (url.origin !== scopeUrl.origin) return;

    // Never wedge: any handler failure falls through to a plain network attempt
    if (request.mode === 'navigate') {
        event.respondWith(serveNavigation(request).catch(() => fetch(request)));
    } else if (url.pathname.startsWith(scopeUrl.pathname + 'assets/diagrams/') && !url.pathname.endsWith('.js') && !url.pathname.endsWith('.json')) {
        // Manifests fall through to the shell lane: plain network, never browse-cached
        event.respondWith(serveImage(request, event).catch(() => fetch(request)));
    } else {
        event.respondWith(serveShell(request).catch(() => fetch(request)));
    }
});
