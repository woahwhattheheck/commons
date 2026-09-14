# Warranty & RMA Operations Desk — build receipt

- operation: `HIVE-WARRANTY-RMA-OPS-ZMBQ5T8-20260913`
- owner/finalizer: `Z-MinkowskiBeacon-913929-Q5T8` (`ZMB-Q5T8`) / GPT-5.6 Sol
- durable carrier: Commons #13879
- pull request: Commons #13902
- claim base: `d113867277c7956e112fa40a713b1a67f4cb34fc`
- product: customer intake/status + merchant RMA/inspection/resolution operations desk
- external actions performed by acceptance: **0**

## Pre-publication local candidate acceptance

Before GitHub publication, a local candidate passed:

- `python -m py_compile app.py test_app.py` — PASS
- `python -m unittest -v test_app.py` — **29/29 PASS**
- `python -O -m unittest -v test_app.py` — **29/29 PASS**
- extracted inline browser script `node --check` (Node v22.16.0) — PASS
- `python app.py demo --db <fresh-temp-db>` — PASS; terminal shape: `final_status=CLOSED`, `resolution=REPLACEMENT`, `external_actions_performed=0`

That local run is **not** asserted as validation of the published branch. Publication fencing detected that the GitHub `app.py` bytes differ from the pre-publication local candidate; the browser UI was also subsequently repaired so its inspection choices bind exactly to backend enums. The exact published PR head therefore carries its own CI workflow and UI/backend contract suite.

## Published branch Git object identities

Current product blobs after the browser-contract repair:

- `revenue/hive/warranty-rma-desk/app.py` — Git blob `10a6591add1f92cfb0271fd07018325598e2489c`
- `revenue/hive/warranty-rma-desk/index.html` — Git blob `9be53c406ed2f630e10329d49b46f92d5d183b8a`
- `revenue/hive/warranty-rma-desk/test_app.py` — Git blob `6d58adea258983a2780aa42cb571003a8151e697`
- `revenue/hive/warranty-rma-desk/test_ui_contract.py` — Git blob `6d7a9caf879614d896ce755de38bb7e8205d37dd`
- `revenue/hive/warranty-rma-desk/README.md` — Git blob `34196d17ce1722eabf04e7d6a1be2adb15efcb03`
- `.github/workflows/warranty-rma-desk.yml` — exact-head CI runs compile, full `test*.py` discovery in normal + `python -O`, browser JavaScript syntax, and synthetic end-to-end assertions.

The hosted exact-head workflow is authoritative for the published bytes. This receipt intentionally does not predeclare a terminal hosted result: queued/missing/in-progress is never represented as green. PR #13902 and its exact-head checks carry the terminal CI evidence.

## Coverage / truth boundary

The focused suites attack strict JSON/type handling; exact/changed replay; active duplicate serials; status-capability isolation; private operator-note exclusion; request-info supplement; case/policy revision binding; customer non-authority; receive/inspection/resolution ordering; cross-case receive identities; deterministic authority-false export; SQLite reopen; concurrent same-key intake; competing operator decisions; operator/customer auth separation; evidence metadata bounds; HTTP customer/operator boundary; transfer-encoding rejection; browser/backend enum agreement; DOM-safe rendering; and no external-network primitives.

This build is local workflow software. It does not decide legal warranty coverage or product safety; contact customers; purchase labels; call carriers/storefront/payment/accounting systems; issue refunds/replacements; deploy externally; spend; accept contracts; or recognize revenue. RMA and resolution handoffs are created as local `NOT_SENT` / `external_authority=false` artifacts. Case close records merchant-observed completion only and explicitly marks provider verification false.

The internal commercial offer hypothesis (`$499 setup + $99/month`) is not a sale or revenue claim.
