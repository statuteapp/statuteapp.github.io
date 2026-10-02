// Statute service worker: app shell cached, feed network-first with cache fallback.
const SHELL = "statute-shell-v1";
const FEED = "statute-feed-v1";
const SHELL_FILES = ["./", "./index.html", "./manifest.webmanifest"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => ![SHELL, FEED].includes(k)).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.pathname.endsWith("/items.json")) {
    // Feed: try network, fall back to last good copy. The app shows "last checked" from the file's generated_at.
    e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(FEED).then(c => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request)));
    return;
  }
  if (e.request.mode === "navigate" || SHELL_FILES.some(f => url.pathname.endsWith(f.replace("./", "/")))) {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  }
});
