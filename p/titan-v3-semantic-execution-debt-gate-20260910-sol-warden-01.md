---
operation: titan-v3-semantic-execution-debt-gate-20260910-sol-warden-01
owner: SOL-WARDEN
status: SOURCE_PACKET_VALIDATED_UNPUBLISHED
scope: additive-analysis-release-gate
canonical_runtime_changed: false
kaggle_changed: false
promotion_authority: false
---

# Paired semantic-execution-debt gate

## Finding

The existing replay evidence contains a score-facing correctness signal not enforced by a matched V3 promotion gate: public episode `107130860` records 283 guaranteed-incompatible TITAN unit commands versus 19 for the reference, a +264 excess. The sealed four-replay corpus totals 323 candidate versus 45 reference strict failures (+278) and 111 dropped hand commands, while containing both candidate wins and losses. Existing action-cardinality and P07 work own the missing-hand mechanism. This operation owns only the disjoint downstream invariant: a candidate may not be selected while adding guaranteed-invalid executable unit commands.

## Delivery

Add one isolated analyzer directory and one path-scoped workflow. The gate requires exact control/candidate closure identities, complete opponent×seed×both-seat cells, unique replay bytes and episode ids, one configuration digest, and zero action-cardinality violations. It checks action `t` against observation `t-1`, retains terminal score deltas as diagnostics, and self-seals its report.

Reject a candidate when any matched cell increases total strict semantic failures or any failure signature. The signature rule prevents aggregate laundering. A positive score delta never overrides rejection. Reports expose strict-scope and unclassified non-PASS row counts so sparse language coverage is never hidden. PASS removes one correctness veto only and grants no promotion authority.

## Strict semantic scope

- FEED, CARE and COLLECT_FERTILIZER require an animal on the actor tile unless an earlier same-phase actor plausibly placed one there.
- WATER and FERTILIZE require a plant unless an earlier same-phase actor plausibly planted there.
- HARVEST requires strictly positive pre-step yield.
- Unknown and broader mechanics are not overclaimed.

## Executed validation

- Python compilation: pass.
- Standard-library contracts: 59/59 pass.
- Source receipt hashes every admitted file and rejects any unlisted executable, symlink, or non-regular node in the owned analysis directory.
- Exact historical witness: `283 / 19 / +264`, reproduced and sealed.
- Checked-in manifest template: schema-valid.
- Delivery receipt: exact file hashes and byte counts verified.

No official game, policy edit, flag enablement, canonical build, archive/pointer mutation, provider action, leaderboard claim or Kaggle upload was performed.

## Publication state

GitHub and Slack were readable during discovery but their connected write actions were not exposed in this session; Slack later returned HTTP 429 on refresh. The packet is therefore retained as an apply-ready local delivery and is not represented as posted, pushed, reviewed, merged or run in hosted CI.
