# SOL-ARC2 — verified background/component/relation increment receipt

Date: 2026-09-08
Operation: `sol-arc2-components-20260908-03`
Paid lane: ARC Prize 2026 ARC-AGI-2
Slack claim: `C0BUY2GT8P9` thread `1788752415.201939`, claim ts `1788878538.349569`

## Fresh publication base

- main commit: `8a130e6c280edef5aac66c172f880079969d7391`
- main tree: `2b34380f4dde154ea8ab8fb462e815175ae86154`
- exact preimages read immediately before composition:
  - `research/arc-agi-2-2026/README.md`: `569fe806253fd92d51048862b8cae182c2353308`
  - `research/arc-agi-2-2026/arc2_baseline.py`: `2e2ff2f6b8d0be883c171f75c9c00284b3e7a469`
  - `research/arc-agi-2-2026/test_arc2_baseline.py`: `0ff8d7b4dc9e65fe3ff3887e13bbb1ab9191d19e`
  - this receipt path: `404 Not Found`

## Change

Background-sensitive hypotheses now enumerate background colors `0..9` and let exact reproduction of every training demonstration select the valid parameter. This replaces the unsafe assumption that the most frequent color must be background.

Added generic task-local primitives/hypotheses:

- tight crop for any verified background color;
- deterministic 4-connected non-background component extraction;
- largest/smallest component crop for any verified background color;
- separator-delimited vertical/horizontal two-panel intersection;
- self-mask/fractal expansion.

No task-ID branching is present in runtime code. Every candidate must still reproduce every supplied training output exactly before it can predict a test output.

The first implementation tried modal-background inference and immediately failed two synthetic cases because ARC foreground can dominate. That candidate design was removed from the hypothesis library and the final implementation uses verified background enumeration instead.

## Frozen replacement bytes

| path | bytes | preimage blob | replacement blob | SHA-256 |
|---|---:|---|---|---|
| `research/arc-agi-2-2026/README.md` | 4220 | `569fe806253fd92d51048862b8cae182c2353308` | `87b49558d4e1df92178e6681a46fadcb48caff98` | `d18a16d09c7f57b44d227d5097918979473cddd91cbcc1c0805b54bece6a4135` |
| `research/arc-agi-2-2026/arc2_baseline.py` | 15194 | `2e2ff2f6b8d0be883c171f75c9c00284b3e7a469` | `1fcc836210256a7ef893432949755ba0b654c31a` | `192dbf779273a414c6c0249f50d951bb539e139df2e5a000784b0b8a31822d8c` |
| `research/arc-agi-2-2026/test_arc2_baseline.py` | 6587 | `0ff8d7b4dc9e65fe3ff3887e13bbb1ab9191d19e` | `7e53861700ff153a86e2cb5cce091396b53e803b` | `76669195adab8e59b7bfda984e5d7fe6bde832df2734f27da844658c52075eec` |

Unchanged synthetic fixture: Git blob `b2ff57f18bf95c7167a47507557766830d607d85`, SHA-256 `151837163aa2689eb46f25dd4366b3fb3a091499284660764439373ad76d37be`.
Synthetic CLI output remains SHA-256 `b47287361bf59995968dc32e33ba25d5fde4f66db28130cfc82d1425cab6cf89`.

## Acceptance

- `python -m unittest -q test_arc2_baseline.py` → **16/16 PASS**
- `python arc2_baseline.py synthetic_challenges.json --output /tmp/arc2-submission-v3.json` → **wrote 2 tasks**
- `python -m py_compile arc2_baseline.py test_arc2_baseline.py` → **PASS**

Bounded official-public **training** regression, checking pass@2 against published training-file test outputs:

- `68b16354`: PASS before, PASS after (`flip_v`)
- `67e8384a`: PASS before, PASS after (`mirror_quadrants`)
- `4cd1b7b2`: PASS before, PASS after (`complete_latin_square`)
- `0520fde7`: MISS before, PASS after (`panel_overlap_vertical_bg0`)
- `007bbfb7`: MISS before, PASS after (`self_mask_expand_bg0`)
- aggregate: **3/5 before → 5/5 after**

Development feedback for this increment is training-only. Public evaluation is reserved from iterative tuning. A few evaluation files were read exploratorily before this discipline was made explicit; none of the rules or measurements in this increment were derived from those evaluation examples.

Public ARC task files are not copied into Commons. This receipt does not claim full-training accuracy, public/private evaluation accuracy, a Kaggle submission, leaderboard score/rank, award, or payment.
