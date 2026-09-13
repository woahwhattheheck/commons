# Sales Meeting Calendar Consumer

This is the path-disjoint live integration for the landed
`revenue/sales_meeting_readiness` product. It does **not** rewrite that compiler.

The integration closes one operating boundary:

> A verified human asks or suggests a meeting. Before anyone represents Bryce as
> available, the host must read actual Google Calendar free/busy for the exact
> requested windows, retain that observation, compile the complete meeting brief,
> and stop at `READY_FOR_OWNER_SCHEDULING_REVIEW`.

## What this carrier does

1. Requires a separately retained `verified-human-meeting-request/v1` authority
   object bound to exact provider event id, content digest, received time,
   opportunity, and thread.
2. Produces an exact **read-only** Google Calendar `get_availability` plan for
   `primary`, using the minimum/maximum requested UTC bounds and the request's
   IANA timezone.
3. Accepts only the minimal connector result used by the live Google Calendar
   tool: one calendar id, busy windows, and provider errors.
4. Normalizes RFC3339 offset busy windows to canonical UTC, hashes the raw
   provider result, and retains no event title/description/attendee data.
5. Selects the earliest requested-duration interval that does not overlap the
   retained busy set. If no such duration fits, it produces a reproducible
   conflict slot. Provider errors become `UNKNOWN`, never FREE.
6. Builds the exact availability object expected by the landed
   `sales_meeting_readiness` compiler and delegates final freshness,
   request-binding, busy-digest, duration, window, prep, and state logic there.
7. Wraps that core receipt with external trigger/capture trust-root digests and
   an explicit no-mutation authority block.

The complete meeting brief must already contain sourced context, objective, key
questions, likely asks, risks/commitments to avoid, recommended opening,
recommended closing, and owner actions. Empty sections fail before Calendar
query planning.

## Live connector sequence

The trusted host owns connector calls and current time. Candidate JSON does not.

1. Retain the verified human meeting authority and its SHA-256 outside the
   candidate trigger.
2. Run:

   ```bash
   python -m revenue.sales_meeting_calendar_consumer.cli plan \
     --trigger trigger.json \
     --human-authority-sha256 "$HUMAN_AUTHORITY_SHA256"
   ```

   The emitted object has only:

   ```json
   {
     "calendar_ids": ["primary"],
     "time_min": "2026-09-14T17:00:00Z",
     "time_max": "2026-09-14T19:00:00Z",
     "response_timezone_str": "America/Kentucky/Louisville"
   }
   ```

3. Call Google Calendar `get_availability` with those exact arguments. Do not
   use `create_event`, `update_event`, `delete_event`, invitation/RSVP, or any
   send/reply action in this carrier.
4. Immediately pass the exact returned `result` object plus host-owned capture
   time to `capture_google_availability(...)`; retain the resulting
   `capture_sha256` independently.
5. Compile with the independently retained trigger and capture digests:

   ```bash
   python -m revenue.sales_meeting_calendar_consumer.cli compile \
     --trigger trigger.json \
     --capture calendar_capture.json \
     --human-authority-sha256 "$HUMAN_AUTHORITY_SHA256" \
     --calendar-capture-sha256 "$CALENDAR_CAPTURE_SHA256" \
     --markdown
   ```

The compile CLI owns `as_of=datetime.now(timezone.utc)`. Historical READY cannot
be replayed as current because the landed core rechecks the retained
`captured_at` against its 30-minute availability freshness policy.

## Trust and authority boundaries

`expected_human_authority_sha256` and `expected_calendar_capture_sha256` are
**external trust roots**. Computing new values from candidate bytes and feeding
them back as "expected" is not verification.

A READY receipt means only:

`READY_FOR_OWNER_SCHEDULING_REVIEW`

It never authorizes:

- calendar event creation, update, deletion, hold, invite, or RSVP;
- email/Slack/provider send or reply;
- telling a counterparty a meeting is confirmed;
- commercial, price, scope, staffing, legal, or payment commitment.

The owner must explicitly review the brief and authorize any later scheduling
action through a separate action authority.

## Hostiles

`test_calendar_consumer.py` covers normal and optimized Python for:

- external human-authority digest mismatch;
- non-human/non-meeting trigger rejection;
- reply/thread generation transplant;
- exact query window/timezone binding;
- wrong calendar id;
- provider busy ranges outside query bounds;
- RFC3339 offset -> UTC normalization;
- fresh empty-busy READY;
- busy-at-start next-slot selection;
- fully busy conflict;
- provider error -> fresh Calendar required;
- stale capture cannot keep READY;
- capture and plan digest tampering;
- cross-reply capture replay;
- requested window shorter than requested duration;
- multi-window selection without using the gap as an allowed slot;
- duplicate JSON keys;
- provider error text/event detail minimization;
- complete prep rendering;
- explicit false mutation authority.

## Validation

Owner-local exact candidate run before publication:

- `python -m py_compile calendar_consumer.py cli.py test_calendar_consumer.py`
- `python -m unittest ...test_calendar_consumer -q` -> 22/22 PASS
- `python -O -m unittest ...test_calendar_consumer -q` -> 22/22 PASS

Those local runs use a compatibility stub for the already-landed core because
the execution container cannot clone GitHub. The branch/PR workflow reruns the
same tests against the real repository core; hosted status must be reported
separately and never inferred from local proof.
