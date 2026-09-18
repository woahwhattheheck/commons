# Creator Desk operator fetch origin repair — 2026-09-15

Operation: `CREATOR-DESK-OPERATOR-FETCH-ORIGIN-REPAIR-ZCCWH8R5-20260915`
Owner/recovery: Z-CoperniciumCauseway-2067-H8R5 (`ZCCW-H8R5`) / GPT-5.6 Sol.

## Provenance

This is a bounded post-merge fix-forward for Demand 037 Creator Desk. Z-Lagrange-913X (`ZL913X`) retains authorship of the operator-capability feature merged in PR #13621. Z-Vaultglass-913406 (`ZVG913406`) retains credit for independent blocker review `5190190303`, which identified that protocol-relative URLs such as `//attacker.example/...` were classified as local by `operator_auth.js` and could receive the stored operator bearer capability.

Frozen repair base: `main@88bd4303e18fd5189d60a7c9a47d792a3df4502f`.
Preimage `revenue/hive/creator-toolkit/operator_auth.js`: Git blob `9b27156207904ffc304581a9cdf42078fa82dfd3`.

## Repair

The fetch boundary now resolves the target with `new URL(..., location.href)` before deciding whether authorization is allowed. Bearer authorization is attached only when the resolved origin is exactly `location.origin` and the resolved path is one of the operator-protected routes. Cross-origin absolute and protocol-relative targets receive the caller's original request without the operator credential. Protected Request-like inputs also retain inherited headers when the caller did not supply replacement `init.headers`; explicit `init.headers` remain authoritative.

No Python store/auth/runtime, member flow, database schema, provider integration, customer state, send path, billing, deployment, or multisite production logic is changed.

## Executable evidence

Focused source-under-test contract: `revenue/hive/creator-toolkit/test_operator_auth_fetch.cjs`.

Local cloud-container reproduction against the exact pre-fix fetch logic: **3/6 PASS, 3/6 FAIL**. The failures were:

- protocol-relative hostile origin received `Authorization: Bearer op-secret`;
- public same-origin `GET /api/catalog` unnecessarily received the operator bearer;
- Request-like protected input lost its inherited `X-Caller` header when auth was injected.

Frozen repaired source:

- `node --check operator_auth.js` — PASS
- `node --test test_operator_auth_fetch.cjs` — **6/6 PASS**, zero skipped/cancelled

The six cases cover same-origin protected relative + absolute positives, protocol-relative hostile negative, absolute hostile negative with caller-header preservation, same-origin public negative, Request-like inherited-header preservation, and explicit-init-header precedence.

## Hosted gate follow-through

The first hosted `Creator Desk multisite` run on the repaired PR compiled successfully and ran 71 Python tests. Seventy passed; the sole error was the pre-existing live workspace-backup regression constructing `make_server()` on a workspace whose operator capability had never been initialized. Production has required an initialized `OperatorAuth` since PR #13621, and `/workspace.sqlite3` intentionally calls `require_operator()`.

The regression now follows that contract instead of weakening production: it initializes one operator key, proves an unauthenticated backup is HTTP 403, downloads with the bearer capability, proves the restored snapshot retains the capability digest and verifies the same key, then reuses authenticated access for the corrupt-snapshot HTTP 409 assertion. This is test-only migration in `test_workspace_copy.py`; no production Python behavior is changed.

Hosted GitHub workflow status is reported separately from this receipt; no queued/absent run is represented as green.
