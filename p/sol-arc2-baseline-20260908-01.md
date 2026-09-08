# SOL-ARC2 — ARC-AGI-2 deterministic baseline receipt

Date: 2026-09-08
Operation: `sol-arc2-baseline-20260908-01`
Paid lane: ARC Prize 2026 ARC-AGI-2
Slack claim: `C0BUY2GT8P9` thread `1788752415.201939`, claim ts `1788878538.349569`

## Publication base

- fresh main commit: `612f40f5472a5269ed3af2f608ea80138037b53c`
- fresh main tree: `95fa9fac7f9b8e73d58cdc21fa813b9d8d340b20`
- exact destination audit: every owned path below returned `404 Not Found` on that base before composition

## Owned paths

- `research/arc-agi-2-2026/README.md`
- `research/arc-agi-2-2026/arc2_baseline.py`
- `research/arc-agi-2-2026/test_arc2_baseline.py`
- `research/arc-agi-2-2026/synthetic_challenges.json`
- `p/sol-arc2-baseline-20260908-01.md`

## Frozen product bytes

| path | bytes | Git blob | SHA-256 |
|---|---:|---|---|
| `README.md` | 2215 | `503f54f0e05d668e50d26a3c887673534611ebae` | `d009aa7a430724f956e573f25b0d3bee119f18e0d4ad2919da2d9d70d8165aec` |
| `arc2_baseline.py` | 8660 | `780bc8b017a4bac6b62ef4c2582c32127abfbda7` | `4ceea2f294bf4a906ee8d1b034a3841494d31539e8731f7140b157025251244f` |
| `test_arc2_baseline.py` | 3493 | `45cb902b53105bab89418b805c6292940c378ae8` | `dc375ed042df6e2337cb79157bb5a04bdf9a7579b8ad730348dbf81acfbb2356` |
| `synthetic_challenges.json` | 355 | `b2ff57f18bf95c7167a47507557766830d607d85` | `151837163aa2689eb46f25dd4366b3fb3a091499284660764439373ad76d37be` |

Synthetic CLI output SHA-256: `b47287361bf59995968dc32e33ba25d5fde4f66db28130cfc82d1425cab6cf89`.

## Acceptance

- `python -m unittest -v test_arc2_baseline.py` → **10/10 PASS**
- `python arc2_baseline.py synthetic_challenges.json --output /tmp/arc2-submission.json` → **wrote 2 tasks**
- `python -m py_compile arc2_baseline.py test_arc2_baseline.py` → **PASS**

The first focused run exposed an over-permissive ranking bug: an arbitrary recolor hypothesis could outrank a simpler geometric rule. The implementation was corrected to rank fewer changed-color mappings before transform order, then the full suite was rerun to 10/10 PASS.

## Competition contract pinned for this build

Official current entry surface: https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/overview

Official sponsor page: https://arcprize.org/competitions/2026/arc-agi-2

This scaffold emits `submission.json` with all challenge task IDs, ordered test outputs, and `attempt_1` / `attempt_2` predictions. It is dependency-free and designed for the no-internet notebook environment. No competition dataset was uploaded to this session or committed here; no leaderboard score, rank, submission, registration, award, or payment is claimed by this receipt.
