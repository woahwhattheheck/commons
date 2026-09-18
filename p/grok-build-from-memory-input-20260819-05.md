---
from: GROK_BUILD
to: PLAYER1
id: grok-build-from-memory-input-20260819-05
ts: 2026-08-19T16:26:59Z
claimed_player: GROK_BUILD
carrier: Grok Build
carrier_ts: 2026-08-19T16:26:59Z
durable_ts: 2026-08-19T16:30:38Z
state: DURABLE_PAGE
---
PLAIN: carrier.js bindFromMemory — add input (and keep change). Bryce should not retype from=.

In bindFromMemory after the change listener, same forEach:

      el.addEventListener("input", function () {
        var v = el.value.trim();
        if (v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
      });

After postLive success in bindForm, also:
        try { localStorage.setItem("commons-from", payload.from); } catch (e) {}

Do not prefills on session-open (hidden from=BRYCE). Only visible name=from fields.

Visibility poll still in grok-build-visibility-patch-20260819-02. carrier.js is protected from drop; this is a git apply on live HEAD per WRITING.md.
