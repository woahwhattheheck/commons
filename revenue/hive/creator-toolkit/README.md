# Creator Desk

A runnable resource library and voluntary follow-up drafting workspace for Hive demand `bm-hive-20260908-037`. Python 3.10+ and SQLite from the standard library are sufficient for the application. No external service or model is called.

## Run in an existing cloud environment

Creator Desk separates member-facing flows from operator controls with one per-workspace capability. Existing workspaces keep all resources, deliveries, consent history and inquiries, but must initialize this boundary once before the upgraded server will start.

From the Commons repository root:

```sh
python3 revenue/hive/creator-toolkit/operator_auth.py \
  --db /path/to/persistent/creator-desk.sqlite3 init
# Save the one-time key privately. The database stores only its SHA-256 digest.

python3 revenue/hive/creator-toolkit/app.py \
  --db /path/to/persistent/creator-desk.sqlite3 --port 8768
```

Open `http://127.0.0.1:8768/` in a browser that can reach that environment. `/tmp` is appropriate for disposable demonstrations only. For retained workspace data, choose an existing persistent private cloud directory for `--db`; do not commit that SQLite file or put live member records in the source repository. No new paid infrastructure is required or provisioned by this application.

The resource library, delivery view and creator workspace are three tabs of the same app. Members can browse the public catalog, request a resource, reconnect to their own delivery record, change their follow-up preference and submit a creator request without the operator key. Opening **Creator workspace** prompts for the private operator capability before loading operator data or enabling creator mutations. The browser stores that key separately from the member reconnect reference and never puts it in a URL.

If the operator key is lost, local filesystem authority can rotate it without changing member or resource records:

```sh
python3 revenue/hive/creator-toolkit/operator_auth.py \
  --db /path/to/persistent/creator-desk.sqlite3 rotate
```

Rotation immediately invalidates the previous key. Normal server startup never prints or stores plaintext capability material.

## Completed workflow

Resources retain their original bytes, file name and SHA-256. A member requests a resource and receives a durable delivery reference. Repeating that resource request for the same normalized email address returns the existing reference rather than creating a second delivery or restarting a sequence. Files can be downloaded again; this is one durable delivery record, not a restriction on redownloading.

An unchecked opt-in box schedules no messages for that request and does not change an existing preference. An affirmative choice records the displayed consent wording and schedules that resource's optional sequence. A repeat resource request never changes consent. The separate **My deliveries** controls are the way to change an existing preference.

Stopping follow-ups cancels all queued drafts in one transaction. Enabling the preference again leaves cancelled drafts cancelled; it does not reschedule old requests. A future request for a different resource may explicitly opt into its sequence. Stale preference edits return a conflict so an older browser does not overwrite a newer choice.

Sequence offsets are integer minutes from the original opted-in request, with at most 20 steps. Each step contains `delay_minutes`, `subject` and `body`. Queued subjects, bodies and due times are snapshots; editing a resource does not change already queued messages. File bytes and external destinations are immutable. To replace an asset, archive its resource and add a new one. Archiving hides it from the library while preserving prior deliveries.

The member can submit a request for the creator, and the creator can resolve it after unlocking operator controls. Members can export their current record, delivery references and consent history as JSON. The browser remembers only a reconnect reference plus, on an operator browser, the separately namespaced operator capability; the authoritative records live in SQLite.

## Follow-up handoff, not automatic sending

The operator outbox shows queued, cancelled and externally recorded entries. A due queued item can be downloaded as an `.eml` draft only through an authenticated operator request. Export rechecks its state, due time and current member preference. The file includes `X-Unsent: 1`, a stable workspace reference and an opt-out instruction; no sender is fabricated and no SMTP connection is made.

The operator supplies the sender and uses their existing mail workflow. Immediately before an external send, check the current preference again. An already downloaded file cannot be recalled by this app, and replies requesting unsubscribe are not automatically ingested. Apply those replies through **My deliveries**. After an actual external delivery, its reference can be recorded through the operator boundary. The resulting `recorded` state is an operator statement, not independent provider verification. Exporting or recording a draft does not send mail.

Native community-platform installation, supported provider event ingestion, automatic email delivery, billing, customer acceptance and a hosted multi-community service remain separate work. This version does not claim those integrations or a sale.

## Operator capability boundary

The server stores only a SHA-256 digest in the `creator_security` table and verifies bearer candidates with `hmac.compare_digest`. The plaintext key is emitted only by the explicit local `init` or `rotate` command. It is not present in the member link, catalog, member state, dashboard JSON, `.eml` content, normal server logs or workspace snapshots as plaintext. A copied/restored SQLite workspace carries the digest, so the same key continues to unlock it unless the operator intentionally rotates.

Operator-only HTTP surfaces are:

- `GET /api/operator` — validate the current capability;
- `GET /api/dashboard` — resources, outbox, inquiries and operator counts;
- `GET /workspace.sqlite3` — checked online SQLite snapshot;
- `GET /draft.eml?id=...` — due follow-up draft export;
- `POST /api/change` actions `resource.create`, `resource.update`, `inquiry.close` and `outbox.record`.

They require `Authorization: Bearer <operator-key>`. Missing, malformed, oversized and incorrect capabilities receive the same HTTP 403 error. No capability is accepted in a query string.

Public-to-the-listener surfaces remain the catalog, member reconnect, delivery lookup/download and member mutation actions `request`, `preferences` and `inquiry`. A member reference is reconnect metadata, not verified identity. This boundary prevents ordinary members from using creator/operator controls, but it is not a user-account system, a tenant-isolation layer or an authorization system between individual members. Keep live member data within the intended community environment and use TLS/appropriate network controls before exposing the listener beyond a trusted local route.

Application limits are 8 MiB per original file, 12 MiB per HTTP request, 20 sequence steps and bounded text fields. SQLite records, resource bytes and operation results persist until the operator manages the database. No automatic retention or deletion schedule is represented as implemented.

## HTTP integration surface

`GET /api/catalog` returns visible resources and the consent wording. `GET /api/member?id=...` returns the selected record, deliveries and consent history. `GET /api/delivery?id=...` returns delivery metadata; `GET /download?id=...` returns original file bytes. Operator endpoints are listed above.

`POST /api/change` accepts `application/json`:

```json
{
  "action": "request",
  "operation_id": "stable-client-operation-reference",
  "payload": {
    "resource_id": "resource-id-from-catalog",
    "email": "reader@example.invalid",
    "name": "Fictional reader",
    "opt_in": false
  }
}
```

Actions are `resource.create`, `resource.update`, `request`, `preferences`, `inquiry`, `inquiry.close` and `outbox.record`. Their executable contracts are in `Store.mutate` and the focused tests. The browser exercises those same routes; it is not a second storage implementation. Operator actions require the bearer capability described above.

Reuse an operation ID and identical payload when retrying a request whose result is uncertain. Reusing it with different content returns HTTP 409. Successful retries return the original response snapshot without reapplying the mutation; read the current GET endpoint afterward when current state matters. Resource updates and preference changes additionally require `expected_revision`. New request IDs for an already-delivered member/resource also coalesce, including concurrent callers. Queues are created transactionally with the original delivery, not by a separate polling worker.

## Validation

```sh
cd revenue/hive/creator-toolkit
python3 -B -m unittest -v test_toolkit test_operator_auth
python3 -O -B -m unittest -v test_toolkit test_operator_auth
```

Those 38 tests exercise actual temporary SQLite files, original binary bytes, database reopen, concurrency, retry conflicts, consent transitions, preserved sequence snapshots, `.eml` parsing, a real threaded HTTP server, operator initialization/rotation, hostile capability rejection, unauthorized operator-route denial, public member flows, and legacy workspace preservation. Tests use only fictional addresses and synthetic delivery references. They perform no external sends.

`check_browser.py` is an optional Playwright/Chromium acceptance script, separate from the dependency-free application. With those tools already present in the cloud environment:

```sh
CREATOR_DESK_TEST_OUTPUT=/tmp/creator-desk-browser python3 check_browser.py
```

Its historical 13 checks exercise the original resource/member/workspace UI through an explicitly declared Python bridge. The production HTTP server additionally injects `operator_auth.js` before the existing page script so creator-tab unlock and protected browser downloads use authenticated HTTP requests without changing the underlying member workflow. The focused HTTP suite verifies that injected boundary and its server contract.

The provided cloud Chromium previously returned `ERR_BLOCKED_BY_ADMINISTRATOR` on native navigation. Native page navigation and native browser storage persistence were therefore not claimed by that historical run. Real HTTP byte downloads and database persistence are covered separately. This limitation is not a claim that a native browser deployment has passed.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
