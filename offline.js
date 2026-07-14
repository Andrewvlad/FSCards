// Service-worker client (all four pages, landing included so the installed start URL registers) plus the update banner: minor/patch shells apply silently, a major waits for consent
// Standalone - no shared.js deps (it reuses fscBanner for lane C). The sets core below needs index.js pool data, but only at call time

const dismissIcon = '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" d="M2.75 2.75l6.5 6.5M9.25 2.75l-6.5 6.5"/></svg>';

// One banner slot at page top, first caller wins until dismissed. Each action {label, act, subtle?} (subtle = secondary outlined button)
// A title gives the stacked layout (kicker + detail + action row), no title a single inline row. dismiss {key, value}: skip while sessionStorage holds value, set it on the x
function fscBanner(text, actions, dismiss, title) {
    if (document.getElementById('updateBanner')) return;
    try { if (dismiss && sessionStorage.getItem(dismiss.key) === dismiss.value) return; } catch (e) {} // Storage may be unavailable
    const banner = document.createElement('div');
    banner.id = 'updateBanner';
    banner.role = 'status';
    banner.className = title ? 'stacked' : 'inline';
    const pills = actions.map(a => `<button type="button" class="pill${a.subtle ? '' : ' active'} bannerAction">${a.label}</button>`).join('');
    const dismissBtn = `<button type="button" class="iconBtn bannerDismiss" aria-label="Dismiss">${dismissIcon}</button>`;
    banner.innerHTML = title ? `
        ${dismissBtn}
        <div class="bannerTitle"><span>${title}</span></div>
        <span class="bannerText">${text}</span>
        <div class="bannerActions">${pills}</div>
    ` : `
        <span class="bannerText">${text}</span>
        <div class="bannerActions">${pills}${dismissBtn}</div>
    `;
    banner.querySelectorAll('.bannerAction').forEach((btn, i) => btn.addEventListener('click', () => actions[i].act(banner)));
    banner.querySelector('.bannerDismiss').addEventListener('click', () => {
        banner.remove();
        try { if (dismiss) sessionStorage.setItem(dismiss.key, dismiss.value); } catch (e) {} // Storage may be unavailable
    });
    document.body.prepend(banner);
}

(() => {
    if (!('serviceWorker' in navigator)) return;

    // Reload into the new version only on banner consent, never on a silent swap
    let accepted = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => accepted && location.reload());

    // The waiting worker's version, or null when the handshake goes unanswered
    const workerVersion = (worker) => new Promise(resolve => {
        const onMessage = (event) => {
            if (event.data?.type !== 'VERSION') return;
            clearTimeout(timer);
            navigator.serviceWorker.removeEventListener('message', onMessage);
            resolve(event.data.version);
        };
        const timer = setTimeout(() => {
            navigator.serviceWorker.removeEventListener('message', onMessage); // Drop the listener on the timeout path too
            resolve(null);
        }, 1000);
        navigator.serviceWorker.addEventListener('message', onMessage);
        worker.postMessage({type: 'GET_VERSION'});
    });

    // A worker held in waiting is a major update (or an unanswered handshake, treated as one)
    async function offerUpdate(worker) {
        const version = await workerVersion(worker);
        // Same-major workers activate themselves (silent lane) - the waiting state was a race
        if (version && majorOf(version) === majorOf(APP_VERSION)) return;
        // No dismiss memory for an unknown (timed-out) version - it would collapse distinct updates onto one key
        fscBanner(version ? `v${version} Ready` : 'Update installed', [{label: 'Update', act: () => {
            accepted = true;
            worker.postMessage({type: 'SKIP_WAITING'});
        }}], version ? {key: 'fscards-dismissed', value: version} : undefined);
    }

    // updateViaCache none: a version.js bump must not hide behind the HTTP cache
    navigator.serviceWorker.register('sw.js', {updateViaCache: 'none'}).then(reg => {
        // No controller means first install, not an update
        if (reg.waiting && navigator.serviceWorker.controller) offerUpdate(reg.waiting);
        reg.addEventListener('updatefound', () => {
            const worker = reg.installing;
            worker?.addEventListener('statechange', () => {
                if (worker.state === 'installed' && reg.waiting && navigator.serviceWorker.controller) offerUpdate(reg.waiting);
            });
        });
    }).catch(() => {}); // Private mode may deny registration - run as a normal website
})();

// Install to home screen: Chromium's beforeinstallprompt (captured to back the landing Install button and the views' menu action), iOS never fires it so a Share hint stands in
// Only the landing page still carries the #installGroup markup
let installPrompt = null;

function showInstallUI(childId) {
    document.getElementById('installGroup')?.classList.remove('hidden');
    document.getElementById(childId)?.classList.remove('hidden');
}

window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
    showInstallUI('installApp');
});

async function installApp() {
    if (!installPrompt) return; // Already consumed (a stale row or still-visible button)
    const prompt = installPrompt;
    installPrompt = null; // A captured prompt is single-use, spent no matter the choice
    prompt.prompt();
    await prompt.userChoice;
    hideInstallUI(); // A dismissal rests until the next page load
}

// A running install-all keeps its progress up, the landing page hides the group at completion.
// The install button itself always hides - a spent prompt leaves it dead
function hideInstallUI() {
    document.getElementById('installApp')?.classList.add('hidden');
    if (!activeDownload) document.getElementById('installGroup')?.classList.add('hidden');
}

window.addEventListener('appinstalled', () => {
    hideInstallUI();
    confirmOfflineReady();
});

// Post-install confirmation the shell capture completed, so the user knows the app opens
// offline with no second online visit (Chromium shares the registration, so the install visit is the only online one needed)
async function confirmOfflineReady() {
    try {
        await navigator.serviceWorker.ready;
        const captured = await (await caches.open(SHELL_CACHE)).keys();
        if (captured.length >= SHELL.length) fscBanner('FSCards works offline now', []);
    } catch (e) {} // Storage may be unavailable
}

// iPadOS reports itself as MacIntel, the touch check separates it from desktop Safari
const onIOS = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

// Install availability for the views' menu action, the nudge, and the landing hint:
// 'prompt' = native prompt captured, 'ios' = uninstalled Safari (Share-sheet hint only)
const installMode = () => installPrompt ? 'prompt'
    : onIOS && !matchMedia('(display-mode: standalone)').matches && !navigator.standalone ? 'ios' : null;

if (installMode() === 'ios') showInstallUI('installHint');

/** Offline sets core: registry + download machinery (the views' UI over it lives in shared.js) **/
// Pages that download define renderOfflineUI (progress), views also pairingSaved (menu refresh)
const OFFLINE_STORE = 'fscards-offline'; // Saved-set registry + browse-retention LRU stamps
const RETENTION_CAP = 600; // Browse images kept (a few sets' worth including thumbnails)
const FETCH_LANES = 5; // Parallel image fetches per download chunk

// Private mode or denied storage degrades to normal online behavior, zero surfaced errors
const offlineReady = 'caches' in window && 'serviceWorker' in navigator;

// DISCIPLINES (version.js, the SW shell list) can't read DATA - warn early if the two drift
if (DISCIPLINES.length !== Object.keys(DATA).length || DISCIPLINES.some(d => !(d in DATA)))
    console.warn('FSCards: DISCIPLINES (version.js) out of sync with DATA (index.js)');

// SHELL (version.js) hand-lists cached assets - warn if a page loads a same-origin script/style missing from it (a silent 404 offline)
const shellUrls = new Set(SHELL.map(path => new URL(path, document.baseURI).href));
for (const el of document.querySelectorAll('script[src], link[rel="stylesheet"]')) {
    const url = (el.src || el.href).split('?')[0];
    if (url.startsWith(location.origin) && !shellUrls.has(url))
        console.warn('FSCards: asset missing from SHELL (version.js), absent offline -', url);
}

let offlineData = loadOffline();
function loadOffline() {
    try {
        const data = JSON.parse(localStorage.getItem(OFFLINE_STORE));
        return {sets: data?.sets ?? {}, lru: data?.lru ?? {}};
    } catch (e) { return {sets: {}, lru: {}}; } // Storage may be unavailable
}

// Debounced for the per-image LRU stamps, immediate for registry changes. Writes merge over a
// fresh read (registry ops as mutators, own LRU lane) so a stale tab can't clobber another's records
let offlineSaveTimer = 0;
function saveOffline(now = false, mutate) {
    clearTimeout(offlineSaveTimer);
    const write = () => {
        const fresh = loadOffline();
        fresh.lru = offlineData.lru;
        mutate?.(fresh);
        offlineData = fresh;
        if (mutate) reindexSavedUrls(); // Only registry mutations change savedUrls - LRU-only writes skip the rebuild
        try { localStorage.setItem(OFFLINE_STORE, JSON.stringify(offlineData)); } catch (e) {} // Storage may be unavailable
    };
    if (now) write();
    else offlineSaveTimer = setTimeout(write, 1000);
}
window.addEventListener('pagehide', () => saveOffline(true));

const absUrl = (url) => new URL(url, document.baseURI).href;
const fmtMB = (bytes) => `${Math.max(0.1, bytes / 1048576).toFixed(1)} MB`;
const pairKey = (disc, set) => `${disc}|${set}`;

// Per-discipline image-identity manifests (tools/manifest), network-first via the SW
const manifestPromises = {};
function manifestFor(disc) {
    return manifestPromises[disc] ??= fetch(`assets/diagrams/${disc}/manifest.json`, {cache: 'no-cache'}) // Revalidate so a changed manifest is seen at once, not after the HTTP max-age
        .then(res => res.ok ? res.json() : null)
        .catch(() => null)
        .then(manifest => {
            if (!manifest) delete manifestPromises[disc]; // Failure is not memoized - the next caller retries
            return manifest;
        });
}

// Manifest key for a resolved image URL (absolute or discipline-relative), thumbs folded onto their parent
const manifestKey = (disc, url) => {
    const root = `assets/diagrams/${disc}/`;
    return url.slice(url.indexOf(root) + root.length).replace('thumbs/', '');
};
// Manifest [hash, bytes] entry for a resolved image URL
const manifestEntry = (manifest, disc, url) => manifest?.[manifestKey(disc, url)];

// Every image a set pairing can display - deterministic per load, so memoized
const setImagesCache = {};
const setImages = (disc, set) => setImagesCache[pairKey(disc, set)] ??= enumerateSetImages(disc, set);

// Approximate size of a full set download, null while the manifest is unreachable.
// Deterministic per load (pool and manifest both fixed), so non-null results memoize
const setBytesCache = {};
async function setBytes(disc, set) {
    const key = pairKey(disc, set);
    if (setBytesCache[key] !== undefined) return setBytesCache[key];
    const manifest = await manifestFor(disc);
    if (!manifest) return null;
    return setBytesCache[key] = setImages(disc, set).reduce((sum, url) => sum + (manifestEntry(manifest, disc, url)?.[1] ?? 0), 0);
}

// Several pairings summed, null when any manifest is unreachable
const sumBytes = (pairs) => Promise.all(pairs.map(([disc, set]) => setBytes(disc, set)))
    .then(sizes => sizes.every(bytes => bytes !== null) ? sizes.reduce((sum, bytes) => sum + bytes, 0) : null);

let activeDownload = null; // {pairs, done, total} - one run at a time, view controls inert meanwhile
const staleSets = new Set(); // Saved sets whose art the current manifest supersedes

// Stop the in-flight run, aborting its live fetches (pairings already recorded stay saved)
function cancelDownload() {
    if (!activeDownload) return;
    activeDownload.cancelled = true;
    activeDownload.controller.abort();
}

// Registry-covered art (absolute URLs): the SW serves it from the set cache, so browse
// LRU stamps for it would be dead bookkeeping - rebuilt on every registry change
const savedUrls = new Set();
function reindexSavedUrls() {
    savedUrls.clear();
    for (const record of Object.values(offlineData.sets))
        for (const url of Object.keys(record.files)) savedUrls.add(absUrl(url));
}
reindexSavedUrls();

// Browse-retention LRU stamp for rendered or warmed art
function retainTouch(url) {
    if (!offlineReady) return;
    const abs = absUrl(url);
    if (savedUrls.has(abs)) return; // Downloaded art never lands in browse retention
    offlineData.lru[abs] = Date.now();
    saveOffline();
}

// Registry removal: the records, their staleness, and the derived index move together
function recordRemoved(keys) {
    saveOffline(true, data => keys.forEach(key => delete data.sets[key]));
    keys.forEach(key => staleSets.delete(key));
}

// Drop cache entries no saved record claims - cross-set borrows (8-way USPA -> FAI) survive
const reapUnclaimed = (cache, urls) => Promise.all(urls.filter(url => !savedUrls.has(absUrl(url))).map(url => cache.delete(url)));

const cachedUrls = async (cache) => new Set((await cache.keys()).map(req => req.url));

// Shell-cache sum = the app's own installed footprint, quoted by the install rows and nudge.
// Memoized only once the capture is complete, so a first visit's mid-capture undercount can't freeze
let appBytesMemo = null;
const appBytes = () => appBytesMemo !== null ? Promise.resolve(appBytesMemo) : caches.open(SHELL_CACHE)
    .then(async cache => {
        const keys = await cache.keys();
        const total = (await Promise.all(keys.map(async req => {
            const res = await cache.match(req); // May be evicted between keys() and here
            return res ? +res.headers.get('content-length') || (await res.blob()).size : 0; // Header avoids a body read
        }))).reduce((sum, n) => sum + n, 0);
        if (keys.length >= SHELL.length) appBytesMemo = total; // Freeze only a complete capture
        return total;
    })
    .catch(() => 0); // Storage may be unavailable

// Coalesce per-image progress ticks into one repaint (a full renderOfflineUI per file is thousands of DOM passes). setTimeout not rAF, so a backgrounded tab's counter still advances
let offlineUITick = 0;
function scheduleOfflineUI() {
    if (offlineUITick) return;
    offlineUITick = setTimeout(() => { offlineUITick = 0; renderOfflineUI(); }, 100);
}

// Fetch urls into a cache a chunk at a time, each landed file ticking the shared counter.
// A failure aborts the run (in-flight chunk-mates may still land, reused on retry), a cancel aborts the fetches themselves
async function fetchInto(cache, urls, init) {
    const run = activeDownload; // Captured - a late sibling fetch must not touch a nulled or superseded run
    for (let i = 0; i < urls.length; i += FETCH_LANES) {
        if (run.cancelled) throw new Error('cancelled');
        await Promise.all(urls.slice(i, i + FETCH_LANES).map(async url => {
            const res = await fetch(url, init);
            if (!res.ok) throw new Error(url);
            await cache.put(url, res);
            run.done++;
            if (run === activeDownload) scheduleOfflineUI();
        }));
    }
}

// Completion bookkeeping: the record is only ever written after a full fetch pass, so a
// partial download is never marked saved
async function recordSaved(disc, set, urls) {
    const key = pairKey(disc, set);
    const manifest = await manifestFor(disc);
    const record = {
        bytes: await setBytes(disc, set) ?? 0,
        files: Object.fromEntries(urls.map(url => [url, manifestEntry(manifest, disc, url)?.[0] ?? null])),
    };
    saveOffline(true, data => data.sets[key] = record);
    staleSets.delete(key);
    window.pairingSaved?.(); // Views keep a watched menu list current
}

// Art a saved set must refetch: the manifest hash disagrees with the record, or the bytes
// went missing behind our back (eviction). Hash-unknown art refetches only when missing
const staleUrl = (record, manifest, disc, stored) => (url) => {
    const hash = manifestEntry(manifest, disc, url)?.[0];
    return (hash && record.files[url] !== hash) || !stored.has(absUrl(url));
};

// sha256-16 of stored bytes, the manifest's hash format (tools/manifest)
const blobHash = async (blob) => [...new Uint8Array(await crypto.subtle.digest('SHA-256', await blob.arrayBuffer())).slice(0, 8)]
    .map(b => b.toString(16).padStart(2, '0')).join('');

// Fetch one pairing into the set cache and record it, ticking the shared counter. Refresh mode
// refetches what the manifest superseded then reaps pool-dropped art - fetch before reap, so an interrupted refresh never leaves the set emptier
async function fetchPairing(disc, set, stored, refresh) {
    const key = pairKey(disc, set);
    const urls = setImages(disc, set);
    const cache = await caches.open(SET_CACHE);
    const record = offlineData.sets[key];
    // No manifest = no identity to record or diff against - recording now would stamp bytes:0 and null hashes, then false-flag the whole set stale
    const manifest = await manifestFor(disc);
    if (!manifest) throw new Error('manifest unreachable');
    let needs;
    if (refresh) {
        needs = urls.filter(staleUrl(record, manifest, disc, stored));
    } else {
        // Reuse bytes an interrupted attempt already stored - hash-verified against the manifest,
        // else recordSaved would stamp a later revision's hashes onto the old bytes
        const reusable = async (url) => {
            if (!stored.has(absUrl(url))) return false;
            const hash = manifestEntry(manifest, disc, url)?.[0];
            if (!hash) return !!(await cache.match(url)); // Nothing to verify against - keep only if still present
            const res = await cache.match(url);
            return res && await blobHash(await res.blob()) === hash;
        };
        const kept = await Promise.all(urls.map(reusable));
        needs = urls.filter((url, i) => !kept[i]);
    }
    activeDownload.done += urls.length - needs.length;
    await fetchInto(cache, needs, {cache: refresh ? 'reload' : 'no-cache', signal: activeDownload.controller.signal}); // Fresh bytes, SW local copies bypassed
    urls.forEach(url => stored.add(absUrl(url)));
    await recordSaved(disc, set, urls);
    if (refresh) await reapUnclaimed(cache, Object.keys(record.files)); // The pre-refresh record's files, pool-dropped ones now unclaimed
}

// The run primitive: fetch pairings under one aggregate counter, each recorded as it completes
// so a failure or cancel mid-run keeps what landed. Refresh updates saved sets in place. Resolves to {failed, cancelled}
async function downloadPairs(pairs, refresh) {
    if (activeDownload) return {failed: 0, cancelled: true}; // One run at a time, refused here so no entry point can corrupt a live run
    if (!pairs.length) return {failed: 0, cancelled: false}; // Nothing to cover - never set an empty run the UI reads pairs[0] from
    activeDownload = {pairs, done: 0, total: pairs.reduce((sum, [disc, set]) => sum + setImages(disc, set).length, 0), controller: new AbortController()};
    renderOfflineUI();
    navigator.storage?.persist?.()?.catch(() => {}); // Durable storage is best-effort, never blocks the run
    // One scan for the whole run, each pairing extending it as it lands
    const stored = await caches.open(SET_CACHE).then(cachedUrls).catch(() => new Set()); // Storage may be unavailable
    let failed = 0;
    for (const [disc, set] of pairs) {
        if (activeDownload.cancelled) break;
        try { await fetchPairing(disc, set, stored, refresh); } catch (e) { if (!activeDownload.cancelled) failed++; }
    }
    const cancelled = !!activeDownload.cancelled;
    // Reap set-cache art no record claims (a past failed download's stragglers) - this run's own
    // stragglers stay for a retry, so skip on cancel where the user may resume at once
    if (!cancelled) {
        const runUrls = new Set(pairs.flatMap(([disc, set]) => setImages(disc, set)).map(absUrl));
        try {
            const cache = await caches.open(SET_CACHE);
            await reapUnclaimed(cache, (await cache.keys()).map(req => req.url).filter(url => !runUrls.has(url)));
        } catch (e) {} // Storage may be unavailable
    }
    pruneRetention(); // Downloaded copies supersede their browse-retention duplicates
    activeDownload = null;
    renderOfflineUI();
    return {failed, cancelled};
}

// Batch candidates: everything in the app (the current-discipline batch stays view-side)
const unsavedPairs = (pairs) => pairs.filter(([disc, set]) => !offlineData.sets[pairKey(disc, set)]);
const allPairs = () => Object.keys(DATA).filter(disc => collegiateShown() || !isCollegiate(disc)).flatMap(disc => imageSetsFor(disc).map(set => [disc, set]));

// Batch labels read "all" untouched, "remaining" once part of the scope is covered
const scopeWord = (pairs, total) => pairs.length < total.length ? 'remaining' : 'all';

// Trim browse retention: copies a downloaded set supersedes, thumbs whose full is local,
// art the manifest dropped, then the oldest entries past the cap
async function pruneRetention() {
    try {
        const cache = await caches.open(BROWSE_CACHE);
        // A downloaded copy only supersedes its browse dupe while the set cache actually still holds it (eviction can strand the registry)
        const setCache = await caches.open(SET_CACHE).then(cachedUrls).catch(() => new Set());
        const superseded = (url) => savedUrls.has(url) && setCache.has(url);
        // Only manifests already requested - the prune stays opportunistic, no new fetches
        const manifests = Object.fromEntries(await Promise.all(Object.entries(manifestPromises).map(async ([disc, p]) => [disc, await p])));
        const keys = await cachedUrls(cache);
        const diagramsRoot = absUrl('assets/diagrams/');
        const live = [];
        const victims = [];
        for (const url of keys) {
            const full = url.replace('/thumbs/', '/');
            const disc = url.slice(diagramsRoot.length).split('/')[0];
            const dropped = manifests[disc] && !manifests[disc][manifestKey(disc, url)];
            if (superseded(url) || (url !== full && (superseded(full) || keys.has(full))) || dropped) victims.push(url);
            else live.push(url);
        }
        if (live.length > RETENTION_CAP) {
            live.sort((a, b) => (offlineData.lru[a] ?? 0) - (offlineData.lru[b] ?? 0));
            victims.push(...live.splice(0, live.length - RETENTION_CAP));
        }
        await Promise.all(victims.map(url => cache.delete(url)));
        // LRU stamps for entries no longer cached are dead bookkeeping
        const survivors = new Set(live);
        for (const url of Object.keys(offlineData.lru)) if (!survivors.has(url)) delete offlineData.lru[url];
        saveOffline();
    } catch (e) {} // Storage may be unavailable
}
