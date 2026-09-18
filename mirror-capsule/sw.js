/* Source stub. Built distributions replace this file with a generated
   precache of files that actually exist in that distribution.
   A cache hit is not canonical. git HEAD remains the board.
   The unbuilt source page does not register this worker. */
self.addEventListener("install", function () {
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", function (event) {
  event.respondWith(
    fetch(event.request).catch(function () {
      return new Response("unbuilt capsule source; no generated distribution cache", {
        status: 503,
        headers: { "Content-Type": "text/plain; charset=utf-8" }
      });
    })
  );
});
