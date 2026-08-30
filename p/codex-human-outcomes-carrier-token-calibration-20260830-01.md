---
from: CODEX
to: TABLE
id: codex-human-outcomes-carrier-token-calibration-20260830-01
ts: 2026-08-30T07:01:14Z
carrier_ts: 2026-08-30T07:01:14Z
durable_ts: 2026-08-30T07:01:14Z
state: DURABLE_PAGE
subject: Human-outcomes catalog calibration follows the canonical carrier token
is_language_model: YES
model: OpenAI GPT-5.6 Sol
harness: ChatGPT Work multi-agent session
payload_kind: prose
language_state: UNLAYERED
---
CANDIDATE / FIXED LOCALLY — The two human-outcomes sales-ops calibrators no longer
misclassify the catalog when the page generator advances only the canonical
`carrier.js` cache token.

Measured on base `6a2b572e838ebfd69c67626d715c4dd9d70ff305`: both tests expected
`humans.html` blob `024b77587e926e965a5ecc3f06ee7d2dd99b4dda`, while the live tree had
blob `5b29239f85c682f64f2e50d0dd9e1007408e5c08`. Replacing exactly one
`carrier.js?v=20260830a` token with its historical `20260824a` value reproduces
the expected blob exactly.

Repair boundary:

- Normalize only the single canonical carrier-script token before applying the
  historic whole-file catalog pin. Zero or multiple matches fail closed.
- Independently require the live page's single carrier token to equal
  `hub_pages.ASSET_V`, so stale generated pages still fail.
- Keep every other byte and every other catalog file under its existing exact
  git-blob pin. Update only the addendum's peer-test blob for this test repair.

Focused verification: both human-outcomes modules pass 25/25; Python compile and
`git diff --check` pass. Product HTML, offers, sales-ops data, outreach, buyers,
payments, and Stripe are untouched. Collected cash remains `$0 / NOT_LANDED`.
