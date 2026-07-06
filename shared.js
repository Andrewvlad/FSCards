// Chrome shared by the three views, loaded after index.js (markup stays per-page)
// Pages define the hooks: disciplineChanged, poolChanged, categoryChanged, imagesChanged, saveSession, ISSUE_PAGE + issueDetails

/** Cross-page filter state (mirrored via fscards-shared) **/
let discipline = '4-way';
let category = 'all';
let classLevel = 'open';
let indoor = false;
let tunnel = false;
let includeFusions = true;
let imageSet = 'Rhythm';
let invert = true;
let theme = document.documentElement.dataset.theme;

// Adopt stored filters (the shared store, or a page's stored run)
function applySharedFilters(src) {
    discipline = src.discipline in DATA ? src.discipline : '4-way'; // Disciplines fall back (in case of rename)
    if (isCollegiate(discipline) && !collegiateShown()) discipline = '4-way'; // Collegiate hidden -> never the active mode
    category   = src.category ?? 'all';
    classLevel = src.classLevel ?? 'open';
    indoor     = src.indoor ?? false;
    tunnel     = src.tunnel ?? false;
    includeFusions = src.includeFusions ?? true;
    imageSet   = src.imageSet ?? 'Rhythm';
    invert     = src.invert ?? true;
}

function matchesCategory(card) {
    switch (category) {
        case 'blocks':
        case 'randoms':
            return isBlock(card.key) === (category === 'blocks');
        case 'all':
        default:
            return true;
    }
}

function showToast(message, long = false) {
    const toast = document.createElement('output');
    toast.role = 'status';
    toast.className = long ? 'toast long' : 'toast';
    toast.textContent = message;
    toast.addEventListener('animationend', e => e.animationName === 'hideToast' && toast.remove());
    document.body.appendChild(toast);
}

/** Diagram loading (low-res thumb first, full-res swapped in behind it) **/
// Full-res URLs confirmed local (warmed ok, or already swapped in) - rendered without a thumb flash
const loadedFulls = new Set();

// Full already local - showing the thumb would only flash
const fullReady = (src) => loadedFulls.has(src);

// Thumbnail: render the low-res thumb first only when the full isn't cached yet, else skip the flash
const lazySrc = (src) => src.endsWith('.svg')
    ? `src="${src}" onload="diagramLoaded(this)" onerror="diagramLoaded(this)"` // vector sets have no thumb
    : fullReady(src)
    ? `src="${src}" onload="diagramLoaded(this)" onerror="diagramLoaded(this)"` // full already local - no thumb, no flash
    : `src="${thumbFor(src)}" data-full="${src}" onload="swapToFullImage(this)" onerror="swapToFullImage(this)"`;

// Card loading indicator: 'thumb' spins until an image paints, 'full' bars along the bottom while the full loads behind the thumb
function setLoadState(img, state) {
    const content = img.closest('.cardContent');
    if (!content) return; // carousel clones / gallery tiles have none
    content.classList.toggle('thumbLoading', state === 'thumb');
    content.classList.toggle('fullLoading', state === 'full');
}

// A direct (cached or vector) image, or the swapped-in full, both mean done
function diagramLoaded(img) {
    setLoadState(img, null);
}

function swapToFullImage(img) {
    const full = img.dataset.full;
    if (!full) return; // already upgraded (swapping src re-fires onload)
    setLoadState(img, 'full'); // thumb painted - bar while the full loads
    const f = new Image();
    f.onload = () => { img.src = full; delete img.dataset.full; loadedFulls.add(full); setLoadState(img, null); };
    f.onerror = () => setLoadState(img, null);
    f.src = full;
}

/** Image-set source button **/
const sourceIcon = (vb, d) => `<svg viewBox="${vb}" fill="currentColor" fill-rule="evenodd" aria-hidden="true"><path d="${d}"/></svg>`;
const IMAGE_SET_SOURCES = {
    Rhythm: {url: 'https://rhythmskydiving.com/',      label: 'SDC Rhythm XP',                      icon: sourceIcon('4 -15.4 204.8 169.4', 'M32.0 0.0L71.0 53.0 75.0 61.0 5.0 83.0 4.0 80.0 8.0 76.0 41.0 50.0 29.0 7.0 32.0 0.0ZM71.0 6.0L76.0 6.0 114.0 31.0 117.0 31.0 152.0 7.0 158.0 7.0 115.0 66.0 71.0 6.0ZM166.0 11.0L168.0 14.0 156.0 60.0 191.0 88.0 193.0 93.0 123.0 70.0 166.0 11.0ZM109.0 80.0L109.0 154.0 105.0 149.0 91.0 110.0 88.0 107.0 46.0 106.0 39.0 103.0 109.0 80.0ZM120.0 80.0L190.0 103.0 188.0 105.0 181.0 106.0 140.0 108.0 125.0 148.0 120.0 154.0 120.0 80.0Z')},
    USPA:   {url: 'https://www.uspa.org/scm',          label: "USPA Skydiver's Competition Manual", icon: sourceIcon('0 0 257 260', 'M112.0 0.0L119.0 0.0 107.0 1.0 90.0 6.0 77.0 12.0 68.0 18.0 53.0 33.0 46.0 45.0 44.0 52.0 48.0 55.0 50.0 53.0 53.0 43.0 57.0 36.0 63.0 28.0 72.0 20.0 93.0 8.0 108.0 4.0 96.0 8.0 85.0 14.0 78.0 19.0 66.0 31.0 61.0 39.0 58.0 47.0 58.0 51.0 62.0 54.0 68.0 37.0 72.0 31.0 83.0 20.0 97.0 11.0 112.0 5.0 96.0 15.0 84.0 27.0 80.0 33.0 74.0 47.0 74.0 51.0 78.0 53.0 80.0 51.0 80.0 46.0 82.0 40.0 90.0 26.0 101.0 15.0 119.0 4.0 107.0 15.0 99.0 26.0 95.0 34.0 91.0 49.0 96.0 53.0 99.0 37.0 106.0 22.0 111.0 15.0 123.0 3.0 124.0 5.0 127.0 1.0 129.0 2.0 136.0 17.0 139.0 31.0 140.0 50.0 141.0 51.0 145.0 49.0 144.0 35.0 139.0 17.0 132.0 3.0 144.0 15.0 149.0 22.0 155.0 34.0 159.0 53.0 163.0 50.0 163.0 44.0 160.0 34.0 152.0 20.0 136.0 4.0 154.0 15.0 165.0 26.0 173.0 40.0 175.0 51.0 177.0 53.0 181.0 51.0 181.0 48.0 179.0 41.0 171.0 27.0 159.0 15.0 143.0 5.0 158.0 11.0 172.0 20.0 183.0 31.0 187.0 37.0 193.0 54.0 197.0 51.0 197.0 47.0 194.0 39.0 189.0 31.0 177.0 19.0 170.0 14.0 159.0 8.0 147.0 4.0 162.0 8.0 183.0 20.0 196.0 33.0 202.0 43.0 205.0 53.0 207.0 55.0 211.0 52.0 209.0 45.0 202.0 33.0 187.0 18.0 178.0 12.0 165.0 6.0 152.0 2.0 136.0 0.0 143.0 0.0 166.0 5.0 178.0 10.0 191.0 18.0 208.0 35.0 218.0 53.0 218.0 59.0 216.0 64.0 168.0 151.0 169.0 153.0 171.0 153.0 171.0 188.0 172.0 189.0 181.0 175.0 186.0 162.0 191.0 140.0 195.0 113.0 226.0 72.0 237.0 54.0 244.0 40.0 247.0 31.0 249.0 29.0 249.0 41.0 246.0 52.0 249.0 55.0 249.0 64.0 246.0 75.0 247.0 76.0 252.0 69.0 253.0 80.0 252.0 81.0 252.0 86.0 249.0 93.0 250.0 96.0 253.0 92.0 253.0 90.0 255.0 89.0 255.0 105.0 253.0 109.0 253.0 111.0 254.0 112.0 255.0 111.0 255.0 125.0 249.0 139.0 250.0 140.0 255.0 134.0 255.0 141.0 251.0 153.0 248.0 157.0 249.0 159.0 252.0 156.0 252.0 163.0 247.0 175.0 248.0 177.0 247.0 184.0 241.0 198.0 233.0 207.0 235.0 208.0 233.0 214.0 222.0 226.0 215.0 230.0 217.0 231.0 215.0 235.0 209.0 240.0 201.0 244.0 190.0 246.0 189.0 247.0 190.0 248.0 193.0 248.0 180.0 255.0 172.0 257.0 154.0 257.0 139.0 253.0 131.0 258.0 125.0 258.0 116.0 253.0 101.0 257.0 83.0 257.0 70.0 253.0 62.0 248.0 65.0 248.0 66.0 247.0 65.0 246.0 54.0 244.0 43.0 238.0 38.0 232.0 38.0 231.0 39.0 232.0 42.0 231.0 32.0 225.0 25.0 218.0 20.0 210.0 20.0 208.0 22.0 207.0 14.0 198.0 8.0 183.0 7.0 178.0 8.0 175.0 3.0 162.0 3.0 156.0 5.0 158.0 6.0 155.0 3.0 150.0 0.0 140.0 0.0 134.0 5.0 140.0 6.0 139.0 1.0 128.0 0.0 123.0 0.0 111.0 1.0 112.0 2.0 111.0 0.0 104.0 0.0 89.0 1.0 89.0 3.0 94.0 5.0 96.0 6.0 95.0 2.0 81.0 2.0 71.0 3.0 69.0 7.0 75.0 8.0 76.0 9.0 75.0 6.0 64.0 6.0 55.0 9.0 52.0 6.0 40.0 6.0 29.0 8.0 31.0 12.0 42.0 24.0 64.0 61.0 115.0 63.0 134.0 70.0 165.0 78.0 182.0 83.0 189.0 84.0 188.0 84.0 154.0 87.0 151.0 38.0 62.0 37.0 53.0 41.0 44.0 47.0 35.0 64.0 18.0 73.0 12.0 89.0 5.0 112.0 0.0ZM128.0 152.0L135.0 156.0 145.0 159.0 165.0 160.0 164.0 161.0 165.0 162.0 165.0 181.0 91.0 181.0 91.0 160.0 110.0 159.0 120.0 156.0 128.0 152.0ZM91.0 186.0L99.0 186.0 99.0 224.0 93.0 208.0 92.0 198.0 91.0 197.0 91.0 186.0ZM104.0 186.0L112.0 186.0 112.0 241.0 109.0 239.0 104.0 232.0 104.0 186.0ZM117.0 186.0L125.0 186.0 125.0 250.0 117.0 245.0 117.0 186.0ZM130.0 186.0L138.0 186.0 138.0 246.0 130.0 251.0 130.0 186.0ZM143.0 186.0L151.0 186.0 151.0 233.0 144.0 241.0 143.0 241.0 143.0 186.0ZM156.0 186.0L164.0 186.0 163.0 205.0 156.0 225.0 156.0 186.0ZM198.0 246.0L202.0 248.0 202.0 252.0 200.0 254.0 197.0 254.0 195.0 252.0 195.0 248.0 198.0 246.0ZM143.0 2.0L152.0 3.0 165.0 7.0 178.0 13.0 187.0 19.0 201.0 33.0 208.0 45.0 210.0 52.0 207.0 54.0 206.0 53.0 203.0 43.0 197.0 33.0 183.0 19.0 162.0 7.0 150.0 3.0 146.0 4.0 159.0 9.0 170.0 15.0 177.0 20.0 188.0 31.0 193.0 39.0 196.0 47.0 196.0 51.0 193.0 53.0 192.0 47.0 188.0 37.0 184.0 31.0 172.0 19.0 158.0 10.0 143.0 4.0 142.0 5.0 144.0 7.0 149.0 9.0 159.0 16.0 170.0 27.0 179.0 44.0 180.0 51.0 177.0 52.0 174.0 40.0 169.0 30.0 154.0 14.0 138.0 4.0 143.0 2.0ZM120.0 4.0L121.0 4.0 107.0 19.0 99.0 34.0 97.0 41.0 96.0 52.0 92.0 49.0 96.0 34.0 104.0 20.0 120.0 4.0ZM134.0 4.0L147.0 15.0 155.0 26.0 159.0 34.0 162.0 44.0 162.0 50.0 159.0 52.0 158.0 41.0 156.0 37.0 156.0 34.0 150.0 22.0 145.0 15.0 134.0 4.0ZM122.0 7.0L116.0 25.0 114.0 50.0 113.0 50.0 111.0 49.0 113.0 30.0 117.0 17.0 122.0 7.0ZM8.0 37.0L19.0 60.0 29.0 77.0 56.0 115.0 60.0 146.0 67.0 172.0 74.0 186.0 85.0 201.0 87.0 214.0 95.0 232.0 100.0 239.0 112.0 250.0 111.0 252.0 96.0 255.0 81.0 254.0 70.0 250.0 81.0 248.0 84.0 246.0 83.0 245.0 64.0 244.0 48.0 238.0 45.0 235.0 51.0 236.0 60.0 234.0 57.0 232.0 52.0 232.0 43.0 229.0 31.0 221.0 26.0 214.0 36.0 218.0 43.0 218.0 44.0 219.0 47.0 218.0 45.0 216.0 39.0 215.0 27.0 208.0 19.0 200.0 12.0 188.0 12.0 186.0 22.0 194.0 33.0 200.0 43.0 203.0 46.0 202.0 33.0 196.0 23.0 189.0 13.0 179.0 6.0 165.0 7.0 164.0 20.0 176.0 30.0 183.0 38.0 187.0 41.0 186.0 27.0 177.0 14.0 164.0 8.0 155.0 4.0 146.0 4.0 144.0 5.0 144.0 32.0 168.0 37.0 171.0 39.0 170.0 32.0 165.0 18.0 151.0 9.0 139.0 3.0 125.0 3.0 122.0 20.0 141.0 34.0 153.0 36.0 152.0 19.0 135.0 9.0 120.0 3.0 106.0 2.0 97.0 18.0 118.0 31.0 131.0 33.0 130.0 21.0 116.0 13.0 104.0 7.0 91.0 5.0 83.0 5.0 76.0 26.0 109.0 40.0 124.0 42.0 123.0 36.0 117.0 21.0 95.0 12.0 76.0 9.0 66.0 9.0 62.0 21.0 81.0 47.0 116.0 48.0 133.0 53.0 157.0 51.0 154.0 50.0 149.0 48.0 148.0 47.0 149.0 47.0 160.0 45.0 157.0 44.0 158.0 44.0 171.0 46.0 175.0 46.0 176.0 45.0 175.0 44.0 176.0 44.0 184.0 47.0 190.0 47.0 191.0 46.0 190.0 45.0 191.0 47.0 199.0 56.0 211.0 53.0 210.0 52.0 212.0 63.0 223.0 68.0 226.0 64.0 225.0 61.0 226.0 70.0 235.0 86.0 244.0 99.0 248.0 104.0 249.0 106.0 248.0 101.0 243.0 84.0 239.0 68.0 230.0 67.0 229.0 89.0 236.0 94.0 237.0 96.0 236.0 92.0 231.0 79.0 228.0 62.0 219.0 58.0 215.0 78.0 225.0 87.0 228.0 91.0 227.0 89.0 224.0 77.0 221.0 65.0 215.0 50.0 200.0 49.0 196.0 66.0 210.0 83.0 219.0 86.0 220.0 87.0 219.0 86.0 213.0 74.0 198.0 63.0 175.0 54.0 140.0 51.0 113.0 33.0 91.0 19.0 70.0 10.0 51.0 8.0 37.0ZM247.0 38.0L247.0 43.0 244.0 54.0 236.0 70.0 225.0 87.0 204.0 113.0 202.0 135.0 192.0 175.0 180.0 200.0 169.0 213.0 168.0 219.0 169.0 220.0 172.0 219.0 184.0 213.0 200.0 202.0 206.0 196.0 206.0 198.0 200.0 207.0 193.0 213.0 183.0 219.0 166.0 224.0 164.0 228.0 165.0 229.0 177.0 225.0 196.0 216.0 193.0 219.0 181.0 226.0 166.0 231.0 163.0 231.0 159.0 236.0 162.0 237.0 188.0 229.0 187.0 230.0 171.0 239.0 154.0 243.0 149.0 248.0 151.0 249.0 169.0 244.0 185.0 235.0 194.0 226.0 191.0 225.0 186.0 227.0 191.0 224.0 203.0 212.0 202.0 210.0 199.0 211.0 204.0 206.0 209.0 197.0 210.0 191.0 209.0 190.0 208.0 191.0 208.0 190.0 211.0 184.0 211.0 178.0 212.0 177.0 210.0 175.0 211.0 158.0 210.0 157.0 208.0 160.0 208.0 149.0 207.0 148.0 205.0 149.0 205.0 152.0 202.0 158.0 207.0 134.0 209.0 114.0 234.0 81.0 246.0 62.0 245.0 71.0 238.0 88.0 226.0 108.0 213.0 124.0 214.0 125.0 229.0 109.0 250.0 77.0 249.0 88.0 241.0 106.0 231.0 120.0 221.0 131.0 223.0 132.0 238.0 117.0 253.0 97.0 252.0 106.0 245.0 122.0 240.0 128.0 239.0 131.0 232.0 140.0 219.0 152.0 221.0 153.0 232.0 144.0 253.0 121.0 252.0 126.0 246.0 139.0 237.0 151.0 223.0 165.0 216.0 170.0 218.0 171.0 227.0 165.0 251.0 143.0 251.0 146.0 246.0 157.0 241.0 164.0 228.0 177.0 214.0 186.0 217.0 187.0 227.0 182.0 248.0 164.0 249.0 165.0 246.0 173.0 237.0 185.0 222.0 196.0 209.0 202.0 212.0 203.0 222.0 200.0 230.0 196.0 243.0 186.0 243.0 188.0 237.0 199.0 227.0 209.0 216.0 215.0 210.0 216.0 208.0 218.0 209.0 219.0 219.0 218.0 229.0 214.0 223.0 222.0 210.0 230.0 203.0 232.0 198.0 232.0 195.0 234.0 204.0 236.0 210.0 235.0 207.0 238.0 191.0 244.0 173.0 245.0 172.0 246.0 174.0 248.0 185.0 250.0 174.0 254.0 159.0 255.0 144.0 252.0 143.0 251.0 156.0 238.0 163.0 227.0 169.0 211.0 170.0 202.0 178.0 191.0 188.0 172.0 192.0 160.0 196.0 141.0 199.0 115.0 228.0 74.0 247.0 38.0ZM127.0 50.0L132.0 51.0 135.0 54.0 131.0 146.0 129.0 145.0 124.0 146.0 123.0 115.0 122.0 114.0 122.0 92.0 121.0 91.0 121.0 69.0 120.0 68.0 120.0 54.0 123.0 51.0 127.0 50.0ZM107.0 51.0L112.0 52.0 115.0 55.0 115.0 63.0 116.0 64.0 116.0 77.0 117.0 78.0 117.0 91.0 118.0 92.0 120.0 133.0 121.0 134.0 121.0 148.0 116.0 150.0 112.0 122.0 111.0 121.0 111.0 115.0 109.0 108.0 108.0 95.0 106.0 88.0 106.0 82.0 104.0 75.0 104.0 69.0 102.0 62.0 102.0 54.0 107.0 51.0ZM146.0 51.0L151.0 52.0 153.0 54.0 153.0 62.0 151.0 69.0 151.0 75.0 149.0 82.0 148.0 95.0 146.0 102.0 145.0 115.0 144.0 116.0 139.0 150.0 134.0 148.0 134.0 135.0 135.0 134.0 135.0 121.0 136.0 120.0 140.0 55.0 143.0 52.0 146.0 51.0ZM88.0 52.0L94.0 53.0 96.0 55.0 97.0 59.0 102.0 84.0 102.0 89.0 104.0 95.0 104.0 100.0 106.0 106.0 106.0 111.0 108.0 117.0 108.0 122.0 110.0 128.0 110.0 133.0 112.0 139.0 112.0 144.0 114.0 150.0 110.0 152.0 108.0 150.0 108.0 147.0 106.0 143.0 102.0 124.0 98.0 113.0 84.0 57.0 85.0 54.0 88.0 52.0ZM163.0 52.0L169.0 53.0 171.0 58.0 146.0 152.0 142.0 151.0 142.0 145.0 144.0 139.0 144.0 134.0 146.0 128.0 146.0 123.0 148.0 117.0 148.0 112.0 150.0 106.0 150.0 101.0 152.0 95.0 157.0 63.0 159.0 55.0 163.0 52.0ZM72.0 53.0L77.0 54.0 79.0 56.0 81.0 62.0 96.0 118.0 98.0 121.0 98.0 124.0 106.0 149.0 105.0 153.0 102.0 153.0 101.0 151.0 78.0 83.0 68.0 58.0 68.0 56.0 72.0 53.0ZM180.0 53.0L185.0 54.0 187.0 56.0 187.0 58.0 177.0 83.0 154.0 151.0 153.0 153.0 150.0 153.0 149.0 149.0 151.0 145.0 157.0 121.0 162.0 108.0 175.0 59.0 176.0 56.0 180.0 53.0ZM56.0 54.0L60.0 54.0 64.0 59.0 100.0 153.0 96.0 153.0 93.0 148.0 84.0 125.0 55.0 61.0 54.0 56.0 56.0 54.0ZM195.0 54.0L199.0 54.0 201.0 56.0 201.0 59.0 197.0 66.0 184.0 98.0 178.0 109.0 162.0 148.0 159.0 153.0 155.0 153.0 162.0 137.0 163.0 132.0 170.0 116.0 191.0 59.0 195.0 54.0ZM42.0 55.0L48.0 56.0 93.0 153.0 89.0 152.0 77.0 127.0 64.0 104.0 63.0 100.0 61.0 98.0 41.0 59.0 42.0 55.0ZM209.0 55.0L213.0 55.0 214.0 59.0 191.0 104.0 189.0 106.0 189.0 108.0 179.0 125.0 166.0 152.0 162.0 153.0 178.0 119.0 178.0 117.0 202.0 68.0 202.0 66.0 206.0 58.0 209.0 55.0ZM128.0 148.0L135.0 152.0 144.0 155.0 157.0 156.0 158.0 157.0 167.0 156.0 168.0 157.0 168.0 198.0 164.0 216.0 158.0 229.0 151.0 239.0 144.0 246.0 130.0 255.0 123.0 254.0 115.0 249.0 106.0 241.0 99.0 232.0 92.0 218.0 87.0 196.0 87.0 157.0 88.0 156.0 93.0 156.0 94.0 157.0 107.0 156.0 118.0 153.0 128.0 148.0ZM206.0 155.0L205.0 164.0 202.0 173.0 203.0 174.0 205.0 172.0 209.0 163.0 208.0 172.0 202.0 185.0 194.0 196.0 195.0 197.0 209.0 181.0 204.0 193.0 194.0 203.0 177.0 212.0 188.0 197.0 195.0 182.0 199.0 168.0 206.0 155.0ZM49.0 156.0L56.0 168.0 60.0 182.0 67.0 197.0 78.0 212.0 64.0 205.0 50.0 191.0 47.0 185.0 47.0 182.0 59.0 196.0 61.0 195.0 55.0 188.0 47.0 172.0 46.0 164.0 50.0 172.0 52.0 174.0 53.0 173.0 50.0 164.0 49.0 156.0Z')},
    Axis:   {url: 'https://www.axisflightschool.com/', label: 'AXIS Flight School',                 icon: sourceIcon('0 0 200 87', 'M149.0 0.0L199.0 0.0 159.0 86.0 110.0 86.0 102.0 70.0 131.0 69.0 151.0 27.0 150.0 25.0 45.0 86.0 1.0 86.0 149.0 0.0Z')},
    FAI:    {url: 'https://www.fai.org/page/competition-rules-section-5', label: 'FAI Skydiving Competition Rules', icon: sourceIcon('0 0 200 213.8', 'M47.2 0.0 L112.3 37.8 L120.0 44.1 L121.4 48.6 L121.1 64.6 L123.0 79.2 L126.3 89.7 L129.9 96.3 L133.0 99.3 L138.2 101.5 L149.2 101.8 L167.2 99.0 L175.4 99.0 L179.3 100.1 L181.5 101.8 L185.1 102.1 L189.2 103.7 L191.7 106.2 L193.1 110.3 L192.3 113.9 L190.9 113.7 L189.8 111.7 L182.9 111.7 L169.4 117.5 L160.8 122.5 L156.4 128.8 L151.7 133.0 L148.4 134.6 L139.0 137.4 L127.7 145.4 L114.5 149.2 L116.4 150.3 L113.9 155.3 L112.8 159.7 L112.6 165.8 L113.7 170.2 L116.1 158.9 L118.9 153.1 L121.1 150.3 L128.0 149.5 L126.1 158.1 L122.8 163.0 L120.6 168.8 L119.4 174.1 L119.7 175.7 L123.0 179.0 L130.8 184.0 L134.1 188.4 L134.9 194.5 L138.2 197.0 L136.8 199.7 L146.8 209.7 L141.5 209.7 L139.3 206.1 L135.2 201.9 L134.1 203.0 L139.6 209.7 L130.2 211.0 L122.2 213.8 L121.7 213.5 L123.9 209.4 L123.6 208.8 L121.4 210.2 L119.4 213.2 L118.6 209.7 L117.2 209.9 L117.5 211.9 L115.0 209.4 L113.7 209.4 L115.3 212.4 L101.0 206.6 L102.6 199.7 L99.6 197.5 L98.2 197.8 L96.6 194.2 L100.1 195.6 L105.4 193.9 L109.0 189.2 L108.1 188.4 L105.4 188.1 L95.4 188.4 L95.4 185.9 L96.3 185.4 L105.4 184.8 L105.9 181.8 L103.4 179.0 L101.8 179.0 L101.2 181.2 L98.8 180.1 L96.8 182.1 L95.2 181.8 L94.1 179.3 L89.9 180.4 L88.3 180.4 L87.2 179.6 L87.2 177.9 L88.3 176.0 L86.1 176.3 L85.0 175.7 L85.0 174.9 L87.4 168.8 L87.4 164.1 L90.2 160.3 L74.8 163.6 L70.3 168.3 L62.3 174.3 L47.7 184.6 L43.0 187.0 L36.7 186.8 L33.9 185.7 L33.1 183.2 L34.5 181.2 L32.8 180.1 L32.8 178.2 L37.8 172.7 L34.2 171.3 L33.4 169.9 L42.5 162.5 L37.2 162.8 L36.7 161.1 L37.8 159.2 L41.4 157.0 L68.1 146.5 L70.1 142.9 L82.2 131.0 L83.6 127.2 L83.0 121.4 L80.0 115.0 L74.5 107.9 L68.1 101.5 L61.2 95.7 L51.6 89.1 L47.7 87.4 L41.7 87.2 L49.1 78.9 L44.4 79.7 L36.4 79.4 L43.0 72.3 L42.8 71.7 L39.2 72.8 L33.9 72.8 L25.1 71.4 L44.7 62.9 L32.0 64.3 L23.2 64.3 L12.4 63.2 L11.9 62.9 L12.4 62.6 L35.3 53.8 L14.3 51.3 L6.3 48.8 L3.0 46.6 L37.8 41.7 L17.9 36.1 L0.0 29.8 L41.1 33.1 L43.9 32.8 L34.8 30.3 L25.4 26.5 L11.3 19.0 L4.1 14.1 L58.5 25.4 L38.3 14.3 L29.2 8.0 L23.4 2.8 L73.1 24.3 L73.7 24.0 L56.3 11.6 L50.2 5.5 L47.2 0.3Z M138.8 32.0 L149.2 42.5 L165.2 54.1 L165.8 53.8 L153.1 41.4 L149.5 36.1 L149.5 35.0 L155.6 39.7 L165.5 45.8 L178.2 52.1 L193.7 57.9 L197.8 60.1 L200.0 62.9 L199.4 65.1 L198.1 66.5 L187.9 73.7 L178.2 83.0 L168.3 95.7 L152.0 97.9 L143.2 97.9 L136.6 97.1 L132.4 92.7 L132.1 92.1 L133.2 90.5 L138.5 85.8 L145.7 83.0 L151.4 79.4 L145.7 77.2 L144.3 75.9 L144.0 74.2 L148.7 74.5 L155.3 72.6 L146.5 69.2 L143.7 66.5 L143.2 63.4 L157.2 67.3 L158.1 67.0 L150.1 61.8 L145.1 57.1 L143.2 54.1 L142.6 50.2 L155.6 57.4 L162.2 60.4 L162.8 60.1 L150.6 50.2 L144.3 43.6 L139.9 37.0 L138.8 32.3Z')},
};

// Point the floating source button at the active image set's site (hidden if the set has no known source)
function updateSourceButton() {
    const link = document.getElementById('sourceLink');
    const source = IMAGE_SET_SOURCES[activeImageSet(discipline, imageSet)];
    link.classList.toggle('hidden', !source);
    if (!source) return;
    link.href = source.url;
    link.title = 'Diagram source: ' + source.label;
    link.setAttribute('aria-label', 'Diagram source: ' + source.label);
    link.innerHTML = source.icon;
}

// Show dark-mode diagrams unless the user opted out of inversion
function updateDiagramMode() {
    const mode = diagramMode(discipline, imageSet);
    const inverting = theme === 'dark' && mode === 'dark';
    document.documentElement.dataset.diagram = inverting && !invert ? 'light' : mode;
    // Opt-out toggle only shown while inversion would apply
    document.getElementById('invertSetting').classList.toggle('hidden', !inverting);
}

/** Settings panel **/
const indoorToggle = document.getElementById('indoorToggle');
const tunnelToggle = document.getElementById('tunnelToggle');
const fusionsToggle = document.getElementById('fusionsToggle');
const themeToggle = document.getElementById('themeToggle');
const invertToggle = document.getElementById('invertToggle');

function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    panel.classList.toggle('hidden');
    document.getElementById('settingsToggle').classList.toggle('active');
    document.body.style.setProperty('--panelH', `${panel.offsetHeight}px`); // Body grows by panel height so arena never resizes
}

// Track panel rewraps while open (window resizes, settings re-renders)
new ResizeObserver(([entry]) => {
    document.body.style.setProperty('--panelH', `${entry.borderBoxSize[0].blockSize}px`);
}).observe(document.getElementById('settingsPanel'));

function selectCategory(button) {
    selectSegment('categorySegment', button);
    category = button.dataset.category;
    categoryChanged();
}

function selectClass(button) {
    selectSegment('classSegment', button);
    classLevel = button.dataset.class;
    updateCategoryUI();
    poolChanged();
}

function selectImageSet(button) {
    selectSegment('imageSetSegment', button);
    imageSet = button.dataset.imageset;
    updateDisciplineUI();
    imagesChanged();
}

function selectIndoor(checkbox) {
    indoor = checkbox.checked;
    imagesChanged();
    if (indoor && activeImageSet(discipline, imageSet) === 'USPA') {
        showToast('USPA does not publish an indoor set (USIS), so borrowing from FAI', true)
    }
}

function selectTunnel(checkbox) {
    tunnel = checkbox.checked;
    poolChanged();
}

function selectFusions(checkbox) {
    includeFusions = checkbox.checked;
    poolChanged();
}

function selectTheme(checkbox) {
    theme = checkbox.checked ? 'light' : 'dark';
    document.documentElement.dataset.theme = theme;
    updateDiagramMode(); // Inversion and its opt-out toggle follow the theme
    try { localStorage.setItem('fscards-theme', theme); } catch (e) {} // Storage may be unavailable
}

function selectInvert(checkbox) {
    invert = checkbox.checked;
    updateDiagramMode();
    saveSession();
}

function selectSegment(groupId, button) {
    document.querySelectorAll(`#${groupId} button`)
        .forEach(otherButton => otherButton.classList.remove('active'));
    button.classList.add('active');
}

// Chrome-wide settings sync, called from each page's own syncSettingsUI
function syncChromeUI() {
    document.querySelectorAll('#modeBar button[data-mode]').forEach(button =>
        button.classList.toggle('active', button.dataset.mode === discipline));
    modeSelect.value = discipline;
    document.querySelectorAll('#categorySegment button').forEach(button =>
        button.classList.toggle('active', button.dataset.category === category));

    indoorToggle.checked = indoor;
    tunnelToggle.checked = tunnel;
    fusionsToggle.checked = includeFusions;
    themeToggle.checked = theme === 'light';
    invertToggle.checked = invert;

    updateDisciplineUI();
}

// Place info-tooltip bubbles within the viewport (otherwise they overflow off-screen on mobile)
function positionTip(tip) {
    const bubble = tip.querySelector('.tipBubble');
    const r = tip.getBoundingClientRect();
    const edge = 16, gap = 8;
    const w = bubble.offsetWidth, h = bubble.offsetHeight;
    bubble.style.left = Math.max(edge, Math.min(r.left + r.width / 2 - w / 2, innerWidth - w - edge)) + 'px';
    bubble.style.top = (r.top - h - gap >= edge ? r.top - h - gap : r.bottom + gap) + 'px';
}
document.querySelectorAll('.infoTip').forEach(tip => {
    tip.addEventListener('mouseenter', () => positionTip(tip));
    tip.addEventListener('focus', () => positionTip(tip));
});

/** Mode bar **/
const modeButtons = document.querySelectorAll('#modeBar button[data-mode]');
// The collapsed-state dropdown: in the stats bar on cards/quiz, inline in the mode bar on the gallery
const modeSelect = document.getElementById('statsModeSelect') ?? document.getElementById('modeSelect');

const collegiateOn = collegiateShown();
for (const button of modeButtons) {
    // Drop whole-collegiate disciplines from the bar + dropdown unless revealed on the landing page
    if (!collegiateOn && isCollegiate(button.dataset.mode)) {
        button.hidden = true;
        continue;
    }
    button.addEventListener('click', () => {
        if (button.classList.contains('active')) return;

        modeButtons.forEach(otherButton => otherButton.classList.remove('active'));
        button.classList.add('active');

        discipline = button.dataset.mode;
        modeSelect.value = discipline;
        disciplineChanged();
    });

    // Mirror each mode into the collapsed-state dropdown
    modeSelect.add(new Option(button.textContent, button.dataset.mode));
}
modeSelect.value = discipline;

// Selecting from the dropdown routes through the matching pill's click handler
modeSelect.addEventListener('change', () =>
    [...modeButtons].find(button => button.dataset.mode === modeSelect.value)?.click());

// Swap whenever the modes can't fit on one line
const modeBar = document.getElementById('modeBar');
const COLLAPSE_BELOW_HEIGHT = 900; // Collapse the mode bar into the dropdown below this viewport height (px)
function fitModeBar() {
    modeBar.classList.remove('collapsed'); // measure with the modes expanded
    const overflowing = modeBar.scrollWidth > modeBar.clientWidth + 1;
    modeBar.classList.toggle('collapsed', overflowing || innerHeight < COLLAPSE_BELOW_HEIGHT);
}
fitModeBar();
new ResizeObserver(fitModeBar).observe(document.body);
document.fonts.ready.then(fitModeBar);

function updateDisciplineUI() {
    renderImageSetButtons();
    renderClassButtons();
    window.renderAnswerButtons?.(); // Quiz-own settings group (answer types track the discipline)

    // 8-way is the only discipline with different indoor pools
    document.getElementById('indoorSetting').classList
        .toggle('hidden', discipline !== '8-way');

    // 4-way is the only discipline with a 12-foot tunnel pool restriction
    document.getElementById('tunnelSetting').classList
        .toggle('hidden', !tunnelFor(discipline));

    // Only CP Freestyle has fusions
    document.getElementById('fusionsSetting').classList
        .toggle('hidden', !fusionsFor(discipline));

    updateCategoryUI();
}

// The category filter only exists when the class-scoped pool carries both kinds
function updateCategoryUI() {
    document.getElementById('categoryGroup').classList
        .toggle('hidden', !categorized(poolSettings()));
}

function renderClassButtons() {
    const classes = classesFor(discipline);
    if (classes.length && !classes.some(c => c.key === classLevel))
        classLevel = (classes.find(c => c.key === 'open') ?? classes[classes.length - 1]).key;

    // Only worth showing when there's an actual choice between classes
    document.getElementById('classGroup').classList
        .toggle('hidden', classes.length <= 1);

    document.getElementById('classSegment').innerHTML = classes.map(c =>
        `<button type="button" data-class="${c.key}" class="pill${c.key === classLevel ? ' active' : ''}" onclick="selectClass(this)">${c.label}</button>`
    ).join('');
}

function renderImageSetButtons() {
    const sets = imageSetsFor(discipline);
    const active = activeImageSet(discipline, imageSet); // the set actually shown (default USPA)

    // Only worth showing when there's an actual choice between sets
    document.getElementById('imageSetGroup')
        .classList.toggle('hidden', sets.length <= 1);

    document.getElementById('imageSetSegment').innerHTML = sets.map(set =>
        `<button type="button" data-imageset="${set}" class="pill${set === active ? ' active' : ''}" onclick="selectImageSet(this)">${set}</button>`
    ).join('');

    updateSourceButton();
    updateDiagramMode();
}

/** View switch (the logo doubles as a menu) **/
const viewSwitch = document.getElementById('viewSwitch');
const viewMenu = viewSwitch.querySelector('.viewMenu');
const logo = viewSwitch.querySelector('summary');
document.addEventListener('click', e => {
    if (viewSwitch.open && !viewSwitch.contains(e.target)) viewSwitch.open = false;
});
document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && viewSwitch.open) viewSwitch.open = false;
});

// Set the view dropdown width to match the logo
viewSwitch.addEventListener('toggle', () => {
    if (viewSwitch.open) viewMenu.style.width = `${logo.getBoundingClientRect().width}px`;
});

/** Report issue: GitHub's new-issue page prefilled with the current app state **/
function buildIssueUrl() {
    const body = [
        '**Describe the issue:**', '', '', '---',

        '_Replication info (auto-populated):_',
        '- Page: ' + ISSUE_PAGE,
        '- Discipline: ' + discipline,
        '- Class: ' + classLevel,
        '- Diagram set: ' + imageSet,
        `- 12ft tunnel: ${tunnel}`,
        `- 8-way tunnel: ${indoor}`,
        `- Include fusions: ${includeFusions}`,
        `- Invert colors: ${invert}`,
        ...issueDetails(),
        '\n',

        '_Device info (auto-populated):_',
        `- Light mode: ${themeToggle.checked}`,
        '- Viewport: ' + innerWidth + '×' + innerHeight,
        '- Screen: ' + screen.width + '×' + screen.height + ' @' + devicePixelRatio + 'x',
        '- User agent: ' + navigator.userAgent,

    ].filter(Boolean).join('\n');
    return 'https://github.com/Andrewvlad/FSCards/issues/new?' + new URLSearchParams({body}).toString();
}
