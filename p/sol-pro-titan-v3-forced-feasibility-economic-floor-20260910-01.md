# SOL-PRO — TITAN V3 forced-feasibility economic-floor receipt

- Operation:
  `titan-v3-forced-feasibility-economic-floor-20260910-sol-pro-01`
- Starting main:
  `ed65812449a2cd021b0635a60ff9171957f3e386`
- Audited scheduler Git blob:
  `a483b24dd72b580d7d8811636b54d2d44f391575`
- Branch:
  `sol-pro/titan-v3-forced-feasibility-economic-floor-20260910-01`
- Canonical scheduler mutation: **none**
- Runtime/config/archive/pointer mutation: **none**
- Game-bank/provider/Kaggle/submission mutation: **none**

## Proven predecessor

The exact current scheduler admits a physically feasible `WOOL` sale at step
`576` because its delayed step-`577` reference fails a supplied capacity
predicate. With inventory `10058` and eight `YARN_STORE` shops, the delayed
reference earns `$102`, the immediate plan earns `$5`, and all four modeled
scenario deltas are `-97`. The plan is nevertheless marked
`forced_feasibility=true`. At the caller, Boolean-first ranking lets that row
outrank every ordinary positive candidate.

A second predecessor requires no market arithmetic: a zero-gain forced row sorts
ahead of a positive ordinary row solely because `True > False`.

## Repair theorem

For the exact source blob named above:

- reference-feasible optimization remains strict `worst_relative_gain > 0`;
- reference-infeasible alternatives must satisfy
  `worst_relative_gain >= 0` and `worst_own_gain >= 0`;
- physical feasibility is recorded independently from economic admission;
- a forced row is caller-eligible only at nonnegative relative and own floors;
- candidate rank is `(worst_relative_gain, forced_annotation)`, never
  `(forced_annotation, worst_relative_gain)`.

This removes a proven negative tail without asserting that physical overflow has
zero cost. The current callback provides only a Boolean and cannot identify the
discarded product, exact quantity, execution chronology, or avoided-loss value.
A stronger forced repair must supply that missing certificate explicitly.

## Acceptance boundary

The path-scoped workflow must check out the exact PR head, hash-bind the audited
scheduler blob, compile the carrier and tests, execute the complete contract
suite, run the carrier as a CLI, validate its strict JSON receipt, compile the
materialized scheduler, and leave the repository byte-clean.

The result is a source-safe donor for T08 integration. Gameplay promotion still
requires composition with the disabled-SpatialTempo identity repair and a
fresh, paired score panel under the swarm's release gate.
