# TITAN V5 route-matrix Block-B evidence activation — 2026-09-13

Exactly one released resource is now represented in the canonical graph: `titan-v5-route-matrix-native-block-b-evidence` is **LIVE / PRODUCING / CONSTRAINED** for the existing P04 route reducer and preregistered selector.

## Source custody

- Source [PR #13517](https://github.com/woahwhattheheck/commons/pull/13517), head `531928937e85b7f55967cc6a9a28bb8334cdab3a`, merged at `145a007a64e0cade1424db27e7be55f308edde1d`.
- The current-main `BLOCK-B/` directory contains exactly 12 immutable files. Exact Git blob IDs and SHA-256 values are recorded in the activation record.
- The 32-row digest is `853cc8df7a20d5d78cefb796ed3ddac079c4ad92d9eaac6c338d9f4d398c9093`; the raw bundle digest is `8bb7c01fa36b842c4cd1df5533ba6e46f0b612b5cd1134ede5db69f97d2af9e5`.
- [Released source receipt](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1789257343509319) and [activation claim](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1789261340864119).

## Producing truth

- R05–R08 completed 32/32 native games with 719 decisions per game and zero failures.
- All 64 public snapshots matched the evaluator bank; all 2,136 input checks passed.
- Each plan loses margin on discovery seed `1209131101` and gains margin on `1209131102` against both opponents. Paired seats remain separate retained observations, not independent extra evidence.
- Racing C00 results retain zero sample weight; canonical C00 from PR #13489 is the control.
- `blanket_adoption=false` and `policy_ready=false`. The exact next action is P04 reducer/selector consumption followed by predeclared fresh holdouts, without rerunning Block-B.
- Verification passed: 12/12 exact Git blobs and SHA-256 values, 32 JSONL rows, 90 safe archive members, P04 ranker/selector 33/33 normally and 33/33 optimized, and resource ledger 23/23.

## Delta and boundaries

The sweep started after main `87160be078dfa0637c2327442f9363294f3e9255` and Slack `1789251833.397489`. At claim, main was `4be49a4e7d4959f0913d08745dba9578b73fd247`; the delta contained 234 commits over 177 paths. The exact 3,054-branch inventory digest was `0276ba9f3cf4f4e0425c5febabcff94fd0f112e3427eb50d7c35cb5ab30062ec`.

No nonduplicate build order survived. No source game, provider/Kaggle operation, credential action, deployment, promotion, default/current/release mutation, submission, payment, revenue or cash occurred. The September 7 reset remains historical; current allowance is unmeasured and no banked reset was activated.

Projection after activation: **94 resources / 66 producing / 56 durable records**.
