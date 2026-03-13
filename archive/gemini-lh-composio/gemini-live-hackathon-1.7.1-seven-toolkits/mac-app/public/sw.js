// Aegis Service Worker
// Minimal SW for PWA installability — caches app shell on install

const CACHE_NAME = 'aegis-v1';
const SHELL_ASSETS = ['/', '/index.html'];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // Network-first for API calls, cache-first for static assets
    const url = new URL(event.request.url);
    if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
        // Never cache local API / WS traffic
        return;
    }
    event.respondWith(
        caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
});
