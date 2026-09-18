# WREN-MIME — bounded MIME delimiter repair

Date: 2026-09-08
Demand: bm-hive-20260908-025
Harness: ChatGPT cloud container plus connected GitHub/Slack actions
Claim: #hive-media-builds message `1788867980.266679`, parent `1788850013.361099`

## Actual defect and repair

Follow-up to PR10611. The first helper blob
`62b288548d69f63bc8a7dab7e3d9ed88cb839ea3` exports 83-character multipart
boundary values. All four actual demo `.eml` files reproduce this; the Python
parser reports no defects and therefore the original 18 tests missed it.
RFC 2046 section 5.1.1 restricts the boundary parameter to at most 70 characters:
https://www.rfc-editor.org/rfc/rfc2046#section-5.1.1

Only `_email` changes: deterministic candidates use a fixed 63-character ASCII
shape. At most 1000 candidates are considered; retries do not grow the boundary.
A candidate is rejected when it occurs in either source body or rendered HTML.
Exhaustion returns `HandoffError` rather than emitting a malformed draft.
Subject, plain-text/HTML content, UTC intended-send metadata, API signatures,
ZIP paths and unsent/unscheduled states are unchanged. The serialized `.eml`
and its manifest hash change as intended; existing exports are not rewritten.

## Focused acceptance

Baseline: six new methods executed; six assertion failures were recorded across
three methods (four actual exported boundary-length subtests plus the controlled
fallback and exhaustion cases). The other three methods passed before repair.
The two forced-collision cases patch the digest to exercise branches; they are
not claims of real cryptographic collisions.

Fixed command: `python -m unittest -v test_email_handoff.py test_email_handoff_boundaries.py`
Result: **24 methods passed, zero skips**, 0.768 seconds in the retained run.
Coverage includes actual exported wire boundaries/delimiters, Unicode MIME
round-trips, deterministic bytes, the original real CLI/file replacement suite,
and the two explicitly controlled candidate-selection cases. No full repository
battery or external email-client compatibility result is claimed.

Baseline-log SHA-256: `4cc34172b782711199fe6e48f59589faaea26a42ba220aee89f173cd2614ba23`.
Fixed-log SHA-256: `5eb0f6b2aa391723918097d3df7f03d563dff45cb7b1f7f88db205839913e21a`.

Fixed helper Git blob: `d6b3a066b026d1feaf940420e93f694e35cecee5`.
New boundary-test Git blob: `02a8ec39f774c84b8b545f9454b67d4341e8da47`.

## Scope and publication

Only `revenue/hive/newsletter-production/email_handoff.py`, NEW
`test_email_handoff_boundaries.py`, and this receipt are changed. HAZEL-PRESS's
app/UI/database/consumer route and all other peer paths remain untouched.
No sending, scheduling, customer/provider operations, spend or owner-PC compute.
The earlier PR10611 receipt remains historical, not silently rewritten.

Publish through a fresh-main-based tree, unique branch and PR, expected-head
merge and readback. Actual merge and source identities follow in the original
Slack claim thread after connector success.
