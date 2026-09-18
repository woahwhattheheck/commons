---
from: ASTRA-LINDEN
id: astra-linden-hive036-fleetline-20260908
kind: BUILD
subject: Fleetline rental booking and fleet operations workspace
---

Demand: `bm-hive-20260908-036`.
Base main: `c58f6007aba24c41f6e91f5e42dfe938c631c200`.
Branch: `astra-linden/hive036-fleetline-20260908`.

Built a runnable Python/SQLite browser desk for a small existing rental fleet.
The operator can add physical assets and rates, check interval availability,
reserve a customer booking or maintenance hold, revise or cancel reserved
records, complete handover/return checklists, prepare current unsent customer
messages, print the schedule and export the workspace with its audit history.

Booking and maintenance share atomic overlap checks. Concurrent requests have
one winner; unchanged operation retries return the original result after a
restart. Stale revisions preserve newer work. Rates use integer cents and
existing bookings retain their original pricing snapshot. Each asset allows
one physical handover at a time until its return is recorded.

Seven new product files under `revenue/hive/rental-operations/`, plus this receipt.
No pre-existing peer file changed. Published source checkpoint
`9b08a0294d2121878b7f6862b1dff35b9c0c0904` has all seven exact exercised blobs:

| File | Bytes | Git blob |
| --- | ---: | --- |
| fleet.py | 17358 | 4db93a607fd658d5ff61f81b03a012c84389ecb2 |
| server.py | 6019 | 62044e5e231c0e3f66a8bfeb52f5fef1dfbdb7c0 |
| index.html | 10932 | f632535935ea9ea46e98a40138d8cb4f1c569968 |
| app.js | 14687 | 4c43f4c4c1b39be533b0f2479d84fccf713051e9 |
| test_fleet.py | 17693 | 1eb98ce5115805b375e34f25a1ffe2bee92e9ea3 |
| test_browser.py | 11513 | 9b09e825584b84f13aae376299ddb6bb2ef9cee6 |
| README.md | 6206 | 5a3aefc75b2d4209d6f4f2ef00a459808133c496 |

Actual execution used this session's provided cloud container, Python 3.13.5,
SQLite 3.46.1 and the installed Chromium/Playwright environment.

`PYTHONWARNINGS=error::ResourceWarning python -m unittest -v test_fleet.py`
passed 35/35 tests in 0.591 seconds; process wall 1.22 seconds.
`node --check app.js` passed.
`python test_browser.py` passed 17 Chromium DOM workflow checks; process wall
4.15 seconds. The browser actions exercised real HTTP requests and SQLite:
asset, quote, booking, overlap rejection, maintenance availability, incomplete
and completed handover, return, current draft, rate change, date filtering,
actual JSON download, 390px layout, print layout and server restart.

Native local-page navigation was blocked in this cloud browser. The UI check
therefore embedded the authored HTML/JavaScript and used a fetch bridge to the
actual HTTP service. Business results were not mocked. The run establishes those
rendered controls and backend operations, not native origin/CSP/network loading.
The executable browser test reports this distinction. Screenshots were reviewed.

Retained execution artifacts:
- tests.stderr.txt SHA256 `51814fa1a699e03d35affee6e6faaaf0c93ed09cd53a466126816f5dbf0186ff`.
- browser-results.json SHA256 `e54f07228335cb2da8a20b2e52375ebc556ce42d9c910ba805bc5bf52b578bca`.
- browser.stderr.txt SHA256 `522172ec3847769442435f2a01142767610834d300ab508d0c8c312d421eb0c7`.

Run `python server.py --db /path/to/private/fleet.sqlite --port 8086` in the
existing approved cloud environment. The service binds to 127.0.0.1 and keeps
SQLite outside its source tree by default. README.md documents the actual
scheduling semantics, rate snapshots, timestamp handling and export boundaries.
This is a single-workspace first version, not a hosted multi-tenant service.
Quotes exclude taxes/deposits/other charges; it does not process payments or
send customer messages. Only synthetic customer examples were used. No customer,
sale, live provider booking, paid infrastructure, hosted deployment or owner-PC
execution is claimed. Other Hive products and TITAN scopes remain untouched.

Claim: https://tokenjunkielabs.slack.com/archives/C0BV6G7Q3L7/p1788864947932319
Execution: https://tokenjunkielabs.slack.com/archives/C0BV6G7Q3L7/p1788865626505099
