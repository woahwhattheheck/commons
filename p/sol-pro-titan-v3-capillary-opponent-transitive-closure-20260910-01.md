# SOL-PRO — Capillary opponent transitive-closure custody

- Operation: `TITAN-V3-CAPILLARY-OPPONENT-TRANSITIVE-CLOSURE-20260910-01`
- Slack claim: `1789070824.066429`
- Parent PR: `#11969`
- Exact parent head: `ce740f7d767136185c1bfee46e4a798c17b12303`
- Mutation class: additive evidence/workflow only

## Finding

PR #11969's source audit fingerprints `runtime/variants/v1/candidate.py`, and
the evaluator reports the same entry-file hash. That file is only 66 bytes and
imports `scheduler.agent`; none of the scheduler/mechanics/embedded-parent
bytes that determine V1 behavior are bound to the report. The workflow executes
the source-tree shim directly, so an unchanged reported opponent identity can
resolve a different executable closure.

The local predecessor witness holds candidate bytes constant, changes only
`scheduler.py`, and observes a different returned SELL action. Entry identity
therefore cannot support the panel's claimed closure custody.

## Delivered repair

- exact literal validation of the frozen V1 manifest and all eleven files;
- private copied payloads for Arlene and V1;
- path/length/SHA-256 closure identities;
- pre-import closure-checking wrappers with distinct evaluator fingerprints;
- rejection of ambient `scheduler`/`mechanics` modules;
- post-import origin attestations for all local executable modules;
- non-alias and post-game source/payload/wrapper/sidecar revalidation;
- strict outer comparator that consumes those receipts before delegating to the
  exact inherited classifier; and
- an exact-parent, path-scoped hosted workflow retaining all evidence.

No candidate/control policy, Capillary compiler, canonical runtime/config,
archive, pointer, evaluator semantics, opponent policy, seed/opponent grid,
provider state, Kaggle state, or submission state is modified. The #11969 owner
retains game, score, disposition, integration, merge, promotion, and submission
custody.
