# H13 — R04 sale horizon 10: REJECT

Status: **REJECT / evidence only**. This file changes no gameplay, defaults, package bytes, evaluator, opponent, or Kaggle state.

## Hypothesis

Increase `r04_sale_horizon` from the shipped V3.1 value 8 to 10, with every other live-submission configuration key unchanged.

## Custody

- Pinned canonical archive SHA-256: `5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1` (428,158 bytes).
- V3.1 merge-base source/tree: `d5eca5b1230258ec583f8026f6a3b422ed15cde0`.
- Shipped horizon-8 archive SHA-256: `e4e5a3acfe4984c89c22c7aa841b4ddd6efe4f4cd71e507d1dabecbb6e865849` (126 files, 528,748 bytes).
- Horizon-10 archive rebuilt with `make_submission.py` from the same canonical/source: `8054f8b63debd3c67490ca05397e8e1d71635f6034765c30f1f7d9666f1055fb` (126 files, 528,741 bytes).
- The only live config delta between those archives is `r04_sale_horizon: 8 -> 10`.
- Official interpreter ref: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
- Vendored official engine source Git blobs verified by the evaluator: `kaggriculture.py 3c202c7ee921da239356789e266b694635103fc4`, `kaggriculture.json b354d06b742fe48402513792253f1a5c29366b20`, `utils.py 91c8822ee6201ba4a5a8416c7dbe34f95dd61c87`.

## Screen 1 — frozen head-to-head self-play

Seeds `2611151001..2611151008`, both candidate seats; exact opponent is shipped V3.1 horizon 8.

Result: **16/16 positive, 0 negative, 0 ties; mean +1,764.75 margin, median +1,413, range +983..+3,317**.

Per seed, seat0 / seat1 margin:

| seed | seat 0 | seat 1 |
|---:|---:|---:|
| 2611151001 | +1023 | +1023 |
| 2611151002 | +984 | +984 |
| 2611151003 | +2503 | +2503 |
| 2611151004 | +3317 | +3317 |
| 2611151005 | +983 | +983 |
| 2611151006 | +2288 | +2288 |
| 2611151007 | +1047 | +1047 |
| 2611151008 | +2167 | +1779 |

Seed `2611151001` was rerun with `--recheck-first`; trace and scores were identical. Local receipt SHA-256: `3e9f0071c59637401a99907bf991d161cb5454fb548fc6c0e42854cff9798ce5`.

## Screen 2 — adversarial self-play development panel

Seeds `101..110`, both candidate seats; exact opponent is again shipped V3.1 horizon 8.

Result: **20/20 positive; mean +1,666.6, median +1,389, range +3..+3,234**. The exact seeds `101` and `102`, used elsewhere to expose L3 self-play regressions, were strongly positive for H13: `+2032/+2032` and `+3234/+3234` respectively.

Local receipt SHA-256: `dc4fc0cd518dd9431ba84fcf9cc67eff0b24e8cce6138c1c33a091840e326051`.

## Screen 3 — official starter paired control

Against `official_starter`, frozen seeds 2611151001 and 2611151002, both seats:

- seed 1001: `delta_own=-151`, `delta_rival=0`, **delta_margin=-151** in both seats;
- seed 1002: `delta_own=-242`, `delta_rival=0`, **delta_margin=-242** in both seats.

This falsifies the interpretation that horizon 10 is a free own-score/production gain.

## Screen 4 — Arlene paired third-opponent gate

Exact opponent: bundled `reference/next-panel/vendor/arlene.py`, SHA-256 `1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`.

Frozen seeds `2611151001..2611151004`, both seats. For each cell, delta is `(h10 vs Arlene) - (h8 vs Arlene)` on the same seed/seat.

| seed | seat | delta own | delta rival | delta margin |
|---:|---:|---:|---:|---:|
| 2611151001 | 0 | -136 | +241 | **-377** |
| 2611151001 | 1 | -136 | +241 | **-377** |
| 2611151002 | 0 | -345 | +121 | **-466** |
| 2611151002 | 1 | -345 | +121 | **-466** |
| 2611151003 | 0 | -820 | +217 | **-1037** |
| 2611151003 | 1 | -820 | +217 | **-1037** |
| 2611151004 | 0 | -571 | +197 | **-768** |
| 2611151004 | 1 | -571 | +197 | **-768** |

Result: **0 positive / 8 negative / 0 ties; mean delta-margin -662, median -617, range -1037..-377**.

Every Arlene cell moves both components the wrong way: horizon 10 lowers TITAN's own score and raises Arlene's score.

## Decision

**Reject horizon 10 as a V3.1 default or promotion candidate.**

The large self-play gain is real but opponent-specific: changing the sale horizon changes shared-market interaction in a way that exploits the shipped horizon-8 opponent, while regressing absolute score against the starter and competitive margin against Arlene. Do not spend more promotion-gate budget on this unconditional parameter change unless a new conditioning hypothesis explains and isolates that opponent dependence.

This evidence intentionally leaves all production/default/package state unchanged.