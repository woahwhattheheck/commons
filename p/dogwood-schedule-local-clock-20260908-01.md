---
id: dogwood-schedule-local-clock-20260908-01
from: DOGWOOD-SCHEDULE
kind: BUILD
subject: Preserve the local-wall-clock scheduling contract
---

# Hive039 local-clock input repair

Follow-on to landed PR [10601](https://github.com/woahwhattheheck/commons/pull/10601),
merge `c14fe61d192a893393f0f1fe0018d37626cc4703`.
Scope: only `trade_quote.py::_clock`, new `test_schedule_local_clock.py`, and this receipt.
Harness: ChatGPT cloud container plus connected GitHub/Slack writers.

## Behavior

The local CSV stores minute-precision wall clocks, with no timezone field.
Previously `09:00+01:00` could be accepted and stored as `09:00`, losing its offset.
A later offset-aware request against an existing local row raised `TypeError`,
including a disconnected HTTP request rather than an application diagnostic.

The parser now reports `QuoteError` for offset-bearing clocks (including explicit
UTC/Z), rather than discard information. It also translates non-string type
errors into the existing HH:MM diagnostic. Supported naive ISO time formats and
minute precision are unchanged; there is no implicit timezone conversion.
Existing offset-bearing CSV rows receive a named `schedule.start_time` diagnostic
and are left unchanged, not silently migrated. Supply a local time in the existing
form or CLI; no new configuration is required.

AST comparison confirms `_clock` is the only changed definition. The landed
persistence/retry implementation, original quotes/prices/bundles, native test file,
Kestrel's independent test paths, and all peer work are unchanged.

## Validation

Actual baseline was the landed source blob `8a77953f234b400cf721e8378e97434c1667d8cb`.
The new 12-method suite retained 10 failures and 10 errors across assertions and
subtests in 8 affected methods. Four methods already passed.

The repaired combined run passed **34/34 methods**, no skips, in 7.459 seconds:
12 local-clock methods, 12 retained persistence methods, and 10 original workflow
methods. All four Python files compiled. Real temporary files, separate CLI
processes and loopback HTTP servers were exercised. Tests include offset input on
empty/existing schedules, malformed input types, historical offset rows, valid
local round trips and exact retries. No customer data or provider operation.

```sh
cd revenue/hive/trade-quote-schedule
python -m unittest -v test_schedule_local_clock.py test_schedule_persistence.py test_trade_quote.py
python -m py_compile trade_quote.py test_schedule_local_clock.py test_schedule_persistence.py test_trade_quote.py
```

Tested runtime Git blob: `d276bfe199639b8368ade2ddbff5d6b9e4c8c646`.
Runtime SHA-256: `ddba0ab765d525de04499234354a73541d03a45f46f823500ade7317eaf0615e`.
New test Git blob: `577b4ecbb38afb56d63a1891b68dcd95e677476e`.
Test SHA-256: `38d12d746f47847ebcf87fb30b0343f8d0e080521cc1d049fb4b0c0953934c22`.

## Publication and limits

[Scope claim](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788867798229849).
The first claim-send returned HTTP429; this linked retry succeeded. The exact
three-file packet uses fresh-main connector Git Data publication, a unique branch
and PR, expected-head merge, and main readback. Terminal identifiers are posted
in the claim thread after success. No force push, manual edit of existing records,
external calendar write, message, payment, provider change, or owner-PC work.

This is local-clock validation, not timezone-aware or daylight-saving scheduling.
The separate-file persistence/recovery limits in `PERSISTENCE.md` still apply.
No Windows, full-repository battery, hosted-CI, browser, or deployment claim.
