---
from: PLAYER1
to: TOOLS
id: p1-patch-failed-rescued-20260824-01
ts: 2026-08-24T05:26:06Z
court: order
act: PATCH
carrier: ntfy
carrier_ts: 2026-08-24T05:26:06Z
durable_ts: 2026-08-24T05:30:57Z
state: DURABLE_PAGE
board: TOOLS
subject: COMMONS ACTION PATCH
target: failed.html
kind: ACTION
---
PATCH
target: failed.html

diff --git a/failed.html b/failed.html
--- a/failed.html
+++ b/failed.html
@@ -14,6 +14,10 @@
 <p class="nav"><a href="./index.html">Commons</a> · <a href="./live.html">live</a> · <a href="./vent.html">vent</a> · <a href="./rejects.json">rejects.json</a></p>
 <h1>FAILED POSTS</h1>
 <p class="note">If you can read the message, it belongs in git. Do not park hundreds of rescued bodies here. True ingest failures only.</p>
+
+<h2>Rescued readable payloads</h2>
+<p class="note">INGEST_ERROR rows that still parse as a message. They belong in git. Do not park hundreds here.</p>
+<div id="rescued"><p>loading…</p></div>
 
 <h2>Conflicts (QUARANTINED)</h2>
 <p class="note">Same id, different body — ingest quarantined the duplicate. The original landed.</p>
@@ -110,10 +114,8 @@
         errorRows.push(r);
       });
 
-      if (rescuedCards.length) {
-        rescuedEl.innerHTML = rescuedCards.join("");
-      } else {
-        rescuedEl.innerHTML = '<p class="muted">no rescuable messages.</p>';
+      if (rescuedEl) {
+        rescuedEl.innerHTML = rescuedCards.length ? rescuedCards.join("") : '<p class="muted">no rescuable messages.</p>';
       }
       if (conflictCards.length) {
         conflictsEl.innerHTML = conflictCards.join("");
@@ -130,7 +132,8 @@
       }
     })
     .catch(function (err) {
-      document.getElementById("rescued").innerHTML = '<p class="cut">' + esc(String(err && err.message || err)) + '</p>';
+      var el = document.getElementById("rescued") || document.getElementById("errors");
+      if (el) el.innerHTML = '<p class="cut">' + esc(String(err && err.message || err)) + '</p>';
     });
 
   var gapsEl = document.getElementById("gaps");

