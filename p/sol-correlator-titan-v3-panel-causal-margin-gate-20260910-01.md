# SOL-CORRELATOR — TITAN V3 causal/margin panel gate repair

- Operation: `TITAN-V3-PANEL-CAUSAL-MARGIN-GATE-REPAIR-20260910-01`
- Slack claim: `1789067639.322829`
- Exact parent: PR `#11969` head
  `a4c8df714b87b412bb13c49179982b8ac2df956a`
- Branch: `sol-correlator/titan-v3-panel-causal-margin-gate-20260910-01`
- Scope: analysis classifier, adversarial contracts, and the existing panel
  workflow invocation only.
- Candidate, control, evaluator patch, game grid, seeds, opponents, canonical
  runtime/config/archive/pointers, provider, Kaggle, and submission state are
  unchanged.

## Defects closed

The parent classifier admits evidence globally rather than causally per cell.
One action-changing cell can satisfy activation while a different,
action-identical cell supplies the cash delta. Although the evaluator already
publishes a full `trace_sha256`, the parent parses it without comparing paired
cells.

The parent also ranks only candidate own cash. It can therefore advance a panel
where the candidate gains a little cash but gives the opponent much more cash,
reducing head-to-head margin or turning prior ties/wins into losses.

## Fail-closed repair

`strict_compare.py` composes the exact parent validator and adds these rules:

1. candidate-action change and full-trace change must agree in every paired
   cell;
2. equal candidate-action streams require equal full traces and both terminal
   scores/banks;
3. global mean margin delta must be nonnegative;
4. every opponent-by-seat mean margin delta must be nonnegative; and
5. no control tie or win may become a candidate loss.

The readable and JSON receipts retain per-cell trace/score-change flags,
outcomes, new-loss/lost-win markers, margin strata, and SHA-256 identities for
the inherited classifier, strict classifier, and strict contracts.

## Predecessor-killing contracts

- cross-cell activation laundering;
- action-identical terminal-score drift;
- action-identical full-trace drift;
- action drift without corresponding full-trace drift;
- positive own cash with much larger rival gain;
- a negative opponent-by-seat margin stratum masked by global upside;
- one new loss masked by positive global and stratum means;
- valid sparse, action-bound upside; and
- exact zero-activation identity plus input nonmutation.

Local syntax compilation and the nine strict logic contracts pass. The hosted
exact-parent workflow is authoritative for source integration and panel
classification. A red economic verdict remains retained evidence, not a
workflow-harness failure to hide.
