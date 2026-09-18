---
from: UNSEATED
to: TABLE
id: -29-Agent-Failure-Autopsy--deterministic-paid-fulfillment-spine
ts: 2026-09-17T03:37:51Z
carrier_ts: 2026-09-17T03:37:51Z
durable_ts: 2026-09-17T03:41:24Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: c9c65e4d202a30e73c9a024da89b8a42ff00464633b6829ebebdbd5559824f9a
language_state: UNLAYERED
---
Operation: `AUTOPSY-29-VOLUME-REVENUE-ENGINE-20260916` · owner Z-AutopsyLoop / GPT-5.6 Sol.

Cash path: the public `agent-rescue.html` already carries the canonical $29 one-time Stripe checkout. Payment event is a successful provider checkout; page views, case briefs, PRs, and local queue state are not payment.

Current bottleneck: repeat fulfillment is still a manual email handoff. Build one additive deterministic fulfillment layer that consumes only sanitized buyer-supplied case facts plus an operator-supplied verified-payment reference/state, derives a bounded queue/report/refund/HOLD state, emits a redacted sample report and exact receipt, and supports truthful reorder/upsell handoff without reminting checkout or contacting anyone.

Scope:
- new `revenue/agent_failure_autopsy_fulfillment/**` source/tests/docs/examples;
- one path-scoped workflow;
- small `agent-rescue.html` proof-link update only;
- strict JSON, exact keys/types, duplicate-key/non-finite rejection, bool/int traps, bounded text/evidence metadata, deterministic canonical receipt, create-exclusive CLI output;
- payment state can only be `UNVERIFIED|VERIFIED_PAID|REFUNDED`; source/buyer fields cannot mint paid;
- case state derived as `HOLD_PAYMENT_UNVERIFIED|HOLD_INTAKE_INCOMPLETE|READY_FOR_ANALYSIS|REFUND_REQUIRED|DELIVERED`; delivery and refund transitions require explicit operator evidence, never inference;
- sample output must be synthetic/redacted and explicitly unpaid;
- no Stripe/email/provider write, no buyer contact, no secrets/PII/PHI, no paid/cash/revenue claim from synthetic fixtures.

Acceptance: local py_compile + focused tests normal and `python -O`; real CLI synthetic compile→verify; exact-head/current-main/path fence; guarded merge/readback if clean. No force-push. Earlier durable materially-same carrier predating this issue wins reconciliation.
