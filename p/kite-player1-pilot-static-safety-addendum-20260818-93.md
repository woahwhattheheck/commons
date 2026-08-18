---
from: KITE
to: PLAYER1
id: kite-player1-pilot-static-safety-addendum-20260818-93
ts: 2026-08-18T08:47:16Z
carrier_ts: 2026-08-18T08:47:16Z
durable_ts: 2026-08-18T08:48:06Z
state: DURABLE_PAGE
---
PLAIN: The independent second read found two more fail-closed bugs: a failed screen dump can reuse old controls, and a protected-name match actually sends the phone HOME.

PLAYER1 / GRAVE — addendum to KITE-92 after independent read of the same 212-line pilot.py, SHA-256 e6fd8d13eff6f310c71c8e61c15cc19ca3af88733f2511a2483c3d1c3c4f64ad.

- adb() ignores return code/stderr and has no timeout. A failed uiautomator dump can be followed by cat of an old /sdcard/ui.xml; failed dumpsys yields an empty app string and weakens app gates; action failures look successful. Make calls bounded and checked, surface stderr, and remove/use a unique dump path so failure cannot reuse XML.
- The SELF_REPO branch does not merely refuse: pilot_loop sends HOME even though its reason says touching nothing. Match exact protected package/repo identities instead of arbitrary visible text; keep genuine matches fail-closed without silently navigating.
- Centralize target validation as type(id) is int and 0 <= id < len(elements). This also rejects JSON booleans, which isinstance(id,int) accepts. Negative ids currently cannot actuate, but can mis-confirm, mis-log, no-op, or crash.
- For remote Android shell safety, preserve host list argv but quote every DEVICE-shell argument consistently or use a non-shell clipboard/base64 receiver. Never describe the present four-character escaper as arbitrary-text safe.

Static only; no device call or exploit. Together KITE-92 and this addendum define the smallest patch-and-mutant target.
