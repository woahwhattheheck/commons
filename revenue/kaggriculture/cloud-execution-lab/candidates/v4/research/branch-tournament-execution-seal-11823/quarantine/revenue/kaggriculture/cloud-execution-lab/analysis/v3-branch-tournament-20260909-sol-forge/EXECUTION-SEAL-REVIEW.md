# SOL-LOCKSTEP execution-closure review

Parent PR: `#11769`  
Parent head reviewed: `4e197fd76c76f2b098781b6be2f1f80a704533ce`  
Decoded parent runner SHA-256: `fbc96845e3777b3f823a6d08e9f84c3a379cb6820123aad35e6d93fbd6ddd08a`  
Sealed runner source SHA-256: `b3e7b15e642d79be2e11399e35aebc7a0b001dfcfdd992e1b43c334b0c740cc6`

## Blocking predecessor

The parent verifies every candidate archive before play, but materializes all candidates
before executing the first one and never re-verifies those runtime trees. Candidate code
runs as the same operating-system user as the evaluator. A candidate can therefore alter
a later candidate's imported module while leaving that later candidate's entry file
unchanged.

The pinned evaluator fingerprints the entry file in its report. The tournament validator
compares that entry digest but does not re-hash the imported runtime tree. This permits a
valid-looking report and an `ADVANCE` decision for behavior produced by bytes different
from the candidate's declared archive closure.

## Exact local reproduction

A synthetic baseline imported under the real `execute_candidate()` path rewrote
`challenger/bundle/dep.py` from:

- before: `d773119a6b6cf3f2b837a8e472eebd9b2f6611327573079ff77aca108da74e1f`
- after: `842184da7f4d8b0d97f30ac5fd7f4fb644605cb5373a56b6ae411a9abb824e02`

The challenger entry file remained byte-identical. Both evaluator reports passed the
parent integrity validator. The altered challenger was ranked `ADVANCE`, selected as
champion, and reported a fabricated `+100.0` paired margin delta under its original
closure receipt.

## Repair

The child adds an execution seal around every candidate process. Immediately before and
after each execution it independently walks and hashes:

1. every materialized candidate runtime tree;
2. the evaluator and loader;
3. the pinned engine file set;
4. every repository opponent closure.

Links and special files are rejected. File-set, byte-count, or tree-digest drift raises
`TournamentError` before ranking or evidence publication. The check uses the existing
predeclared runtime-tree and opponent-tree identities, so it does not introduce a second
source of truth.

## Contracts

`test_execution_seal.py` contains three focused contracts:

- mutation of a future candidate dependency fails closed after the mutating process;
- evaluator/loader mutation fails closed;
- an unchanged closure returns the underlying execution unchanged.

Local exact-source result:

```text
python -B -m unittest -v test_execution_seal.py
Ran 3 tests in 0.010s
OK

python -B -m py_compile \
  tournament_contracts.py tournament_evidence.py \
  titan_branch_tournament.py test_execution_seal.py
PASS
```

## Boundary

This repair closes persistent cross-candidate and shared-asset drift inside one tournament
run. Arbitrary same-UID code that mutates and restores bytes between the pre/post seals is
still outside a hash-only guard; the evaluator's existing instruction to run candidate
code inside an isolated container remains mandatory for hostile-code execution.
