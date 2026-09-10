# TITAN V3 Capillary opponent transitive-closure binding

Operation: `titan-v3-capillary-opponent-transitive-closure-20260910-sol-pro-01`

Exact parent panel: PR #11969 head `ce740f7d767136185c1bfee46e4a798c17b12303`.

## Blocker

The parent panel audits each opponent with `identity(path)`, and its classifier
requires the evaluator report to repeat that entry-file SHA-256. That is enough
for the self-contained Arlene source but not for frozen V1:

```python
# 66 bytes
from scheduler import agent
```

The workflow gives the evaluator the repository path to that shim. Its behavior
therefore depends on `scheduler.py`, `mechanics.py`, the embedded Arlene parent,
and receipt math even though the report records only the unchanged 66-byte
entry hash. Two trees can satisfy the parent opponent fingerprint while
returning different actions.

`test_same_entry_hash_different_scheduler_emits_different_action` is the exact
predecessor killer: both synthetic arms have the same candidate bytes and
candidate SHA-256, but distinct scheduler closures return different SELL lots.

## Repair

`bind_opponents.py` validates the published V1 `FREEZE.json` byte-for-byte and
requires its exact eleven-file inventory. It then:

1. copies frozen V1 and Arlene into separate, private, regular-file-only payloads;
2. computes a path/length/SHA-256 closure over every copied file;
3. generates label-specific wrappers whose bytes embed the expected closure;
4. has each wrapper re-inventory the payload before import;
5. rejects an already-loaded `scheduler` or `mechanics` module;
6. imports from only the private payload and attests the exact origins of
   `scheduler`, `mechanics`, `scheduler.parent`, and
   `scheduler.receipt_math`;
7. emits source, payload, wrapper, sidecar, and import-probe receipts; and
8. rehashes and reprobes all of those surfaces after both game arms complete.

`strict_compare.py` source-pins the exact inherited comparator, requires the
build and post-panel receipts, checks the copied bytes against the literal
freeze identities again, substitutes only the wrapper identities into a private
copy of the parent audit, and then delegates to the unchanged inherited score
classifier. The parent entry-only reports are a deterministic rejection case.

## Hosted carrier

The additive workflow:

- requires this branch to be a descendant of the exact parent head and permits
  only this operation's seven new paths;
- runs the parent classifier contracts plus all closure-binding contracts;
- invokes the unchanged parent audit and pre-interpreter candidate-action
  evaluator materializer;
- executes the unchanged control and Capillary arms against the bound wrappers;
- reverifies source, private payloads, wrappers, sidecars, and import origins;
- classifies only through `strict_compare.py`; and
- retains all raw panels and custody receipts regardless of verdict.

A green run establishes executable-opponent custody for this exact panel. It
does not itself establish Capillary strength, authorize a fresh-main port, or
change any runtime, archive, pointer, provider, leaderboard, or Kaggle state.
