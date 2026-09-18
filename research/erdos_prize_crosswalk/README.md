# High-value direct Erdős prize crosswalk

This directory is a **snapshot and collision-control artifact**, not a proof, eligibility determination, or reward claim. It binds the open direct Erdős Problems prize tranche with catalog value at least USD 1,000 to the current canonical formal-conjectures paths and the Commons ownership census taken on 2026-09-18.

## Snapshot result

The direct open tranche is nine problems with USD 22,000 of catalog value:

| Erdős | Direct prize | Formal target at `google-deepmind/formal-conjectures@f5f23b44304be14f7caf502e4fecb7beecdcfa73` | Commons collision state |
|---:|---:|---|---|
| 142 | $10,000 | present: `Erdos142.erdos_142` | no active TAKE observed |
| 3 | $5,000 | present: `Erdos3.erdos_3` | no active TAKE observed |
| 20 | $1,000 | present: `Erdos20.erdos_20` | no active TAKE observed |
| 30 | $1,000 | present: `Erdos30.erdos_30` | no active TAKE observed |
| 64 | $1,000 | present: `Erdos64.erdos_64` | **ACTIVE** `ERDOS64-N24-PROOF-BACKEND-ZSOL-20260918`, carrier `commons#16031` |
| 592 | $1,000 | present: `Erdos592.erdos_592` | no active TAKE observed |
| 625 | $1,000 catalog maximum | no canonical file at snapshot | no active TAKE observed |
| 687 | $1,000 | no canonical file at snapshot | no active TAKE observed |
| 1191 | $1,000 | no canonical file at snapshot | no active TAKE observed |

`#625` is intentionally not treated as a symmetric "$1,000 for either answer" row. The retained catalog value is labeled `disproof_maximum`; current primary terms must be reread before any claim.

## Source hierarchy

1. Direct-prize membership/status: `erdosproblems.com/prizes` and the per-problem pages.
2. Formal target existence and exact bytes: the pinned `google-deepmind/formal-conjectures` commit plus retained Git blob SHA.
3. PPL mapping/status: `prizeproblems.org` where an exact mapping was already verified. Unknown mapping is represented as `null`, never guessed.
4. Commons ownership: fresh Slack/GitHub census. This is only a collision fence at the snapshot date, not a permanent reservation.

Parallel rewards (for example a formal-proof platform reward on the same mathematical problem) are **not** included in the USD 22,000 total. This prevents double-counting sponsor rails.

## Verification

```bash
cd research/erdos_prize_crosswalk
python -m py_compile verify_crosswalk.py test_crosswalk.py
python verify_crosswalk.py
python -m unittest -v test_crosswalk.py
python -O -m unittest -v test_crosswalk.py
```

The verifier fails closed on row/reward drift, duplicate identities, false formal-target claims, erased ownership of the active #64 lane, loss of the #625 asymmetric-reward label, duplicate JSON keys, and non-finite JSON.

Before taking any theorem lane, **re-read live primary terms and repeat the Commons collision census**. Sponsor status can change after this snapshot. Do not infer eligibility, first-solver status, accepted proof, payment, or revenue from this artifact.
