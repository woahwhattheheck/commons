# SOL-CORRELATOR — TITAN V3 Capillary W/T/L non-regression gate

- Operation: `TITAN-V3-PANEL-WTL-NONREGRESSION-GATE-20260910-02`
- Slack narrowing claim: `1789068502.690609`
- Exact parent: PR `#11969` head
  `ce740f7d767136185c1bfee46e4a798c17b12303`
- Branch: `sol-correlator/titan-v3-panel-outcome-gate-20260910-02`
- Scope: thin classifier composition, exact adversarial contracts, and the
  existing panel workflow invocation only.
- Candidate, control, evaluator patch, game grid, seeds, opponents, canonical
  runtime/config/archive/pointers, provider, Kaggle, and submission state are
  unchanged.

## Collision correction

The first child draft, PR `#11987`, was based on superseded parent head
`a4c8df714b87b412bb13c49179982b8ac2df956a`. Before that draft opened, the
parent owner independently added the candidate-action/full-trace causal gate
and the global plus opponent-by-seat margin gates at `ce740f7d...`. Earlier
owner implementation wins. PR `#11987` was closed unmerged and preserved only
as derivation provenance.

This successor does not duplicate those repaired rules.

## Remaining score-facing defect

The exact parent classifier now measures own cash and head-to-head margin, but
it does not model paired W/T/L transitions. Aggregate and opponent-by-seat
means can therefore hide a discrete regression:

- one control tie can become a candidate loss while the other three cells in
  its stratum remain positive enough for every inherited gate to pass; or
- one control win can become a candidate tie while the same inherited means
  remain positive.

A promotion classifier for a policy intended to win should not emit ADVANCE in
either case without an explicit exception contract.

## Fail-closed successor

`strict_compare.py` calls the exact inherited classifier first, then adds:

1. per-cell control and candidate outcomes from candidate-seat terminal scores;
2. a complete deterministic transition census;
3. zero new losses (`tie|win -> loss`);
4. zero lost wins (`win -> tie|loss`);
5. zero W/T/L rank regressions; and
6. SHA-256 identity for the inherited classifier, outcome classifier, outcome
   contracts, and exact workflow that invoked the classifier.

ADVANCE requires every inherited causal, own-cash, and margin criterion plus
all three outcome criteria.

## Predecessor-killing contracts

The focused suite proves:

- an inherited positive panel remains ADVANCE;
- the inherited classifier ADVANCES a masked `tie -> loss`, while the outcome
  successor REJECTS it;
- the inherited classifier ADVANCES a masked `win -> tie`, while the outcome
  successor REJECTS it;
- all executable evidence sources are content-addressed in the report; and
- classifier input reports remain byte-structurally unmodified.

The existing parent contracts remain in the same workflow and run before this
focused suite. Hosted exact-head execution is authoritative. A red economic
verdict remains retained evidence and does not authorize gameplay, promotion,
provider, Kaggle, or submission mutation.
