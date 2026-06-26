const CACHE_NAME = 'sixyao-v4';
const STATIC_ASSETS = [
  '/static/style.css',
  '/static/manifest.json',
  '/static/gua/0.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);

  // Static assets: cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(cached => {
        if (cached) return cached;
        return fetch(event.request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // HTML pages: network-first (always get fresh content)
  if (event.request.destination === 'document') {
    event.respondWith(
      fetch(event.request).then(response => {
        return response;
      }).catch(() => {
        return caches.match(event.request);
      })
    );
    return;
  }

  // Other requests: network-first with cache fallback
  event.respondWith(
    fetch(event.request).then(response => {
      return response;
    }).catch(() => {
      return caches.match(event.request);
    })
  );
});
