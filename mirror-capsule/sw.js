/* mirror-capsule service worker. Caches owned capsule files only.
   A cache hit is not canonical. git HEAD remains the board. */
const CACHE = "commons-mirror-capsule-v1";
const OWNED = [
  "./",
  "../mirror-capsule.html",
  "./OPEN.md",
  "./schema.json",
  "./selection.json",
  "./claim_boundary.json",
  "./reader.js",
  "./sw.js",
  "./index.json",
  "./manifest.json"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(OWNED).catch(function () {
        return cache.addAll(OWNED.filter(function (url) {
          return url.indexOf("manifest.json") === -1 && url.indexOf("index.json") === -1;
        }));
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", function (event) {
  event.respondWith(
    caches.match(event.request).then(function (hit) {
      if (hit) return hit;
      return fetch(event.request).then(function (res) {
        return res;
      }).catch(function () {
        return new Response("capsule offline miss; git HEAD remains canonical", {
          status: 503,
          headers: { "Content-Type": "text/plain; charset=utf-8" }
        });
      });
    })
  );
});
