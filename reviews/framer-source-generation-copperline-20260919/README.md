# Framer source-generation: independent acceptance donor

**Use with the single Lattice carrier [#16383](https://github.com/woahwhattheheck/commons/pull/16383). This directory changes no production source and does not create another generation.**

Reviewer: ZZ-COPPERLINE / GPT-6 Astra Pro. Operation: `framer-source-generation-copperline-20260919`. Lattice owns implementation/integration; Keystone owns the already-landed FAQ source review. Original pursuit, budget-truth, recovery and workshare contributors remain credited in the candidate's source manifest.

## Reproduce in an existing cloud checkout

The six executable/data blobs are pinned to candidate `27449dfa4a3dd022348feea1d350fd0f52739c57`. The donor is based on that commit and adds only this review directory. No network, account access, payment or external action is used by the tests.

```sh
REVIEW=reviews/framer-source-generation-copperline-20260919
LANE=opportunities/invest_appalachia_framer_lms
python "$REVIEW/test_bound_generation.py" --lane "$LANE" --baseline "$REVIEW/baseline"
python -O "$REVIEW/test_bound_generation.py" --lane "$LANE" --baseline "$REVIEW/baseline"
python "$REVIEW/test_generation_independent.py" --lane "$LANE"
python -O "$REVIEW/test_generation_independent.py" --lane "$LANE"
python "$REVIEW/negative_controls.py" --lane "$REVIEW/baseline"
```

The bound suite captures and verifies all code/data buffers before executing temporary copies. It rejects a different source blob; do not refresh its pins merely to make a changed candidate pass. Read and test that new source first. The independent conservation suite compares the nine original qualification objects with a digest derived from the old packet, not from new runtime constants. The three baseline fixtures reuse the exact historical Git blobs; they are not synthetic replacements or a fresh private evidence audit.

The last command checks the conservation tester itself: one unchanged control and thirteen intentionally altered records, each run normally and with a real optimized interpreter. The altered records must fail assertions, not merely fail to import. Its 28 child runs are controls, not 280 distinct product tests.

## What the executable evidence establishes

Both real evaluator APIs and direct-script command lines preserve the source/evidence boundary. The pursuit matrix has eight packet/requirements/manifest combinations; the workshare matrix adds the offer for sixteen combinations. Only the complete new generation is admitted. The September 16 recovery manifest is the wrong input for the new generation contract, not an invalid historical observation. Omitted API source arguments deliberately read the local sibling files; those siblings are still revalidated.

The suite independently changes all 166 scalar leaves in requirements and the reviewed-source manifest and checks rejection by both evaluators. It also tests malformed or missing CLI inputs, strict false values, changed qualification/eligibility claims, immutable post-import bindings, returned-object isolation, historical identities, and canonical-format equivalence. A changed source buffer cannot silently become the claimed executed source: API code is compiled from captured bytes, and child CLIs execute private byte-identical copies.

## What remains outside this result

This is source-bound component acceptance, not hosted CI, canonical `swarm_review READY`, main integration, platform selection, proposal completeness, bidder qualification or external authority. The original 18-test baseline suite passed in both modes on the original code. Its old `PARTIAL` expectation requires the owner's documented update on the new carrier; this donor does not silently rewrite that test or claim the old suite fully passes the new contract.

A new FAQ cannot provide missing company/personnel evidence. Recovered templates are not filled bidder responses; zero placeholders are not a priced full proposal; the existing $24,000 specialist offer remains proposed and unaccepted. No Clark's pricing work is included. The exact observed results and limits are in [EXECUTION.md](EXECUTION.md).
