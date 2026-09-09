# Creator Desk

A runnable resource library and voluntary follow-up drafting workspace for Hive demand `bm-hive-20260908-037`. Python 3.10+ and SQLite from the standard library are sufficient for the application. No external service or model is called.

## Run in an existing cloud environment

From the Commons repository root:

```sh
python3 revenue/hive/creator-toolkit/app.py --db /tmp/creator-desk-demo.sqlite3 --port 8768
```

Open `http://127.0.0.1:8768/` in a browser that can reach that environment. `/tmp` is appropriate for a disposable demonstration only. For retained workspace data, choose an existing persistent private cloud directory for `--db`; do not commit that SQLite file or put live member records in the source repository. No new paid infrastructure is required or provisioned by this application.

The resource library, delivery view and creator workspace are three tabs of the same app. Add a file or HTTP(S) link in **Creator workspace**, optionally attach a user-authored sequence, then use **Resource library** to request it. The demo button inserts an explicitly fictional resource once. An `example.invalid` address suffices for a demonstration; no mail is sent.

## Completed workflow

Resources retain their original bytes, file name and SHA-256. A member requests a resource and receives a durable delivery reference. Repeating that resource request for the same normalized email address returns the existing reference rather than creating a second delivery or restarting a sequence. Files can be downloaded again; this is one durable delivery record, not a restriction on redownloading.

An unchecked opt-in box schedules no messages for that request and does not change an existing preference. An affirmative choice records the displayed consent wording and schedules that resource's optional sequence. A repeat resource request never changes consent. The separate **My deliveries** controls are the way to change an existing preference.

Stopping follow-ups cancels all queued drafts in one transaction. Enabling the preference again leaves cancelled drafts cancelled; it does not reschedule old requests. A future request for a different resource may explicitly opt into its sequence. Stale preference edits return a conflict so an older browser does not overwrite a newer choice.

Sequence offsets are integer minutes from the original opted-in request, with at most 20 steps. Each step contains `delay_minutes`, `subject` and `body`. Queued subjects, bodies and due times are snapshots; editing a resource does not change already queued messages. File bytes and external destinations are immutable. To replace an asset, archive its resource and add a new one. Archiving hides it from the library while preserving prior deliveries.

The member can submit a request for the creator, and the creator can resolve it in the workspace. Members can export their current record, delivery references and consent history as JSON. The browser remembers only a reconnect reference when local storage is available; the actual records live in SQLite.

## Follow-up handoff, not automatic sending

The outbox shows queued, cancelled and externally recorded entries. A due queued item can be downloaded as an `.eml` draft. Export rechecks its state, due time and current member preference. The file includes `X-Unsent: 1`, a stable workspace reference and an opt-out instruction; no sender is fabricated and no SMTP connection is made.

The operator supplies the sender and uses their existing mail workflow. Immediately before an external send, check the current preference again. An already downloaded file cannot be recalled by this app, and replies requesting unsubscribe are not automatically ingested. Apply those replies through **My deliveries**. After an actual external delivery, its reference can be recorded. The resulting `recorded` state is an operator statement, not independent provider verification. Exporting or recording a draft does not send mail.

Native community-platform installation, supported provider event ingestion, automatic email delivery, billing, customer acceptance and a hosted multi-community service remain separate work. This first version does not claim those integrations or a sale.

## Shared-workspace boundary

This is one shared, trusted workspace with open creator controls, not a member-identity or tenant-isolation system. A member reference is reconnect metadata, not verified identity. Users who can reach the workspace can use its controls and inspect its operator data. Run demonstrations with fictional data and keep live member data within a trusted environment. The default listener is loopback. The UI calls out this operating model; the implementation adds no login or account requirement.

Application limits are 8 MiB per original file, 12 MiB per HTTP request, 20 sequence steps and bounded text fields. SQLite records, resource bytes and operation results persist until the operator manages the database. No automatic retention or deletion schedule is represented as implemented.

## HTTP integration surface

`GET /api/catalog` returns visible resources and the consent wording. `GET /api/member?id=...` returns the selected record, deliveries and consent history. `GET /api/dashboard` returns all resources, the outbox, inquiries and counts. `GET /api/delivery?id=...` returns delivery metadata; `GET /download?id=...` returns original file bytes; `GET /draft.eml?id=...` exports a due draft without changing its state.

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

Actions are `resource.create`, `resource.update`, `request`, `preferences`, `inquiry`, `inquiry.close` and `outbox.record`. Their executable contracts are in `Store.mutate` and the focused tests. The browser exercises those same routes; it is not a second storage implementation.

Reuse an operation ID and identical payload when retrying a request whose result is uncertain. Reusing it with different content returns HTTP 409. Successful retries return the original response snapshot without reapplying the mutation; read the current GET endpoint afterward when current state matters. Resource updates and preference changes additionally require `expected_revision`. New request IDs for an already-delivered member/resource also coalesce, including concurrent callers. Queues are created transactionally with the original delivery, not by a separate polling worker.

## Validation

```sh
cd revenue/hive/creator-toolkit
python3 -B -m unittest -v test_toolkit
```

The 29 tests exercise actual temporary SQLite files, original binary bytes, database reopen, concurrency, retry conflicts, consent transitions, preserved sequence snapshots, `.eml` parsing, and a real threaded HTTP server. Tests use only fictional addresses and synthetic delivery references. They perform no external sends.

`check_browser.py` is an optional Playwright/Chromium acceptance script, separate from the dependency-free application. With those tools already present in the cloud environment:

```sh
CREATOR_DESK_TEST_OUTPUT=/tmp/creator-desk-browser python3 check_browser.py
```

It runs 13 embedded-browser checks and connects the UI to the real HTTP/SQLite app through an explicitly declared Python bridge. Browser storage is a declared in-memory adapter. It covers forms, preference changes, draft and delivery link resolution, inquiry resolution, metadata editing, and 390px/320px layouts. No backend fixture replaces the app.

The provided cloud Chromium returned `ERR_BLOCKED_BY_ADMINISTRATOR` on native navigation. Native page navigation, native browser downloads and native local-storage persistence were therefore not accepted by this run. Real HTTP byte downloads and database persistence are covered separately. This limitation is not a claim that a native browser deployment has passed.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

