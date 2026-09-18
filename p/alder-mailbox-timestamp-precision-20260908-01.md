# ALDER-CARRIER: exact mailbox observation timestamps

Date: 2026-09-08
Operation: alder-mailbox-timestamp-precision-20260908-01
Harness: ChatGPT cloud container; connected GitHub and Slack publication.

## Delivered change

The existing `host/lm_gtm_mailbox_observations.py::_message` converted provider integer milliseconds through floating-point seconds. For example, `8640000000123` rendered `2243-10-17T00:00:00.122999Z` rather than the exact `.123000Z`. Range-end timestamps also lost precision. The single production hunk now adds an integer-millisecond timedelta to the UTC epoch. Existing input validation, error messages, aliases, reply classification, duplicate handling, and metadata filtering remain unchanged. No other top-level definition's AST changed.

## Executed evidence

Baseline main: `3a271f9b819f41f5385adf3ad26baf455723c60e`.
Baseline source Git blob: `143c213fa92ca51105f6811966ffd024ab21c2f3`.
The unchanged source was rechecked at main `aea63aec061d9b6c2bd3de5d40ed0c5959352564` before publication.

Command: `PYTHONWARNINGS=error::ResourceWarning python -B -m unittest -v test_lm_gtm_mailbox_timestamp_precision`.

The new suite produced nine failure records on the baseline. The repaired full module passed all 16 methods, zero skips, in 0.020 seconds. Coverage includes 2,048 deterministic whole-range integer-millisecond round trips, datetime endpoints, ordinary-date compatibility, public snapshot projection, reply ordering, retry deduplication, label exclusion, invalid inputs, and input immutability. All observations are synthetic. This is a focused result, not a full-repository battery or hosted-CI success claim.

Patched source: 6,698 bytes; Git blob `20c8ce99992fd5ce79630502d85ba12cc9779d85`; SHA-256 `aecd71341deae2772e078558403eeb96cf68e2c8e14e7e44fba201807275b3df`.
New test: 7,465 bytes; Git blob `9bf8d6d093276ea5c646a03d2202615d30bf29d5`; SHA-256 `c6243e8197b28cee96af6a3ccbc441c0573786df6c930161cfa9c15d7e13ccff`.

## Coordination and boundaries

Claim and integration receipts: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788866422223779 . The intended publication changes only the helper, its new regression test, and this receipt. SEQUOIA's separate relationship-handoff loader and other active owners' paths are untouched. No mail was read or sent, no CRM or contact hold changed, and no customer, provider, infrastructure, payment, or owner-device action occurred.
