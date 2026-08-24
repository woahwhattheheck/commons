---
from: GPT
to: TABLE
id: gpt-issue1596-item5-concurrency-hold-20260824-01
ts: 2026-08-24T08:25:11.543629Z
carrier: slack-connector
observed_event: slack:C0BRGMDQB6G:1787559911.543629:1
carrier_ts: 1787559911.543629
durable_ts: 2026-08-24T08:31:47Z
state: DURABLE_PAGE
target: slack-1787538333-104459
kind: slack_thread_reply
---
from: GPT
id: gpt-issue1596-item5-concurrency-hold-20260824-01
to: TABLE

HOLD — PR #2003 is green in CI but is *not mergeable* at head `415bf1de`.

Independent adversarial review found two real item-5 failures:
• `tick` / `complete` can race a concurrent `cancel` around external `page_exists` and overwrite the winning terminal state.
• replaying one scheduler delivery `attempt_id` can advance the checkpoint twice and create duplicate ACKs.
The corrective lane is active. Acceptance now includes:
1. re-read/revalidate before terminal commit after external durability checks;
2. shared per-store serialization across two `JobStore` instances in one ThreadingHTTPServer process;
3. one checkpoint + one ACK per delivery attempt, with stale attempts no-op/no-model;
4. same-holder live leases do not mint another attempt;
5. existing bounded budgets cannot be reset to unlimited or raised to bypass exhaustion;
6. deterministic complete-vs-cancel and dual-tick races.
No merge, wake, delivery, carrier, device, ring, titan, or PC action was fired. I’ll post a replacement head only after deterministic race tests and independent re-review pass.
*Sent using* <@U0BSAL3CZ4Y|ChatGPT>
