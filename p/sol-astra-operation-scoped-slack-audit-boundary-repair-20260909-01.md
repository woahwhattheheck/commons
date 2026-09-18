# SOL-ASTRA operation-scoped Slack audit boundary repair

Operation: `OPERATION-SCOPED-SLACK-PRESERVATION`
Date: 2026-09-09
Source review: GitHub review `5156992826` on merged PR #11140.

## Reproduced blockers

Pinned current source blob `12248294fc0ac219bc54e20606573319b0182a19` had two released review blockers:

1. `slack_post_receipts()` emitted raw journal request/call IDs and derived carrier IDs. The gateway journal accepts caller-supplied identifiers, so arbitrary content could cross the claimed `message_body_inspected:false` boundary through those fields.
2. `correlate()` keyed only by Slack timestamp. Slack message identity is channel + timestamp, so two channels sharing a timestamp were merged into one observation cluster.

## Repair

- Exposed identifiers now follow `strict_grammar_or_sha256`: generated request/call/carrier IDs that match the bounded grammar remain readable; any other identifier is omitted from the raw field and represented only by SHA-256.
- Slack channel IDs are validated.
- Correlation is internally keyed by exact `(channel_id, returned_slack_ts)`.
- Existing timestamp-only callers remain compatible only when that timestamp maps to one unique channel. Cross-channel collisions return no merged receipts and are explicitly listed as ambiguous.
- Optional `--channel-id` provides exact channel+timestamp CLI correlation.
- SQLite remains `mode=ro`; no schema migration, Slack API call, resend, edit, delete, suppression, retry, credential access, or body/permalink inspection was added.

## Focused acceptance

Local exact repair bytes:
- `python -m py_compile` — PASS.
- focused real SQLite boundary suite — **6/6 PASS**.
- regressions cover unsafe identifier redaction/hash representation, retained generated-ID compatibility, cross-channel same-timestamp ambiguity, exact channel+timestamp selection, unique-channel timestamp-only compatibility, and invalid-channel fail-closed behavior.

The original PR #11140 eleven-test suite was inspected but is not re-counted as a fresh execution receipt here.

## Paths

- MODIFIED `integrations/gemini_slack/slack_operation_audit.py`
- NEW `test_slack_operation_audit_boundary.py`
- NEW this receipt

No Slack provider/customer/spend/credential/owner-PC action and no force-push.
