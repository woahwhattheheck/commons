# Supplemental evidence component

`supplemental_receipt.py` is an additive, pure helper for the existing
`check_joint_receipt.py` reader. It is not another CLI, workflow, archive reader,
or result producer. It has no filesystem or network operations and does not
import the base reader, so the base can call it without a circular import.
Python 3.10+; standard library only.

```python
import json
from pathlib import Path
import check_joint_receipt as core
from supplemental_receipt import inspect_supplemental

path = Path("/path/to/existing-validation.zip")
base = core.inspect_archive(
    path,
    expected_sha256="1323e92edc15bfe7a767dc02c60ffb3c45a0254f802397cf8b820522094a49ab",
    expected_checkout="428b4437cbce55785c558252911a8acb826d8f59",
    expected_run_id="34166821802", expected_attempt="1",
)
members = core.read_members(path)
snapshot = json.loads(members["SOURCE-SNAPSHOT.json"], object_pairs_hook=core.unique_object)
supplement = inspect_supplemental(members, snapshot, base)
```

A caller already holding the member bytes and snapshot should pass those
objects directly rather than read the ZIP again. The helper never modifies
any input. `core_receipt` is the original three-suite result before adding
supplemental counts; do not pass an already-expanded total and count it twice.

The result has `suites`, source hashes, issues, represented-suite count and
reported method totals. `status` describes the supplemental checks only;
`core_status` is carried separately. Preserve both statuses and combine their
problems in the one reader. A supplemental `COMPLETE_PASS` with zero represented
suites is not a claim that an incomplete historical core passed.

Coverage is deliberately limited to the represented loader (at least 7
methods), empty-lot (15) and joined-wrapper (6) suites. Representation is a
known source row or log/report member. Missing logs then remain explicit;
`require_all=True` requests all three even from an older artifact. Count,
completion order, qualified/failed summaries, UTF-8, source hashes, loader
report schema, errors and declared gameplay scope are checked. CRLF logs are
supported. Log-only suites bind through the existing workflow checkout/source
snapshot; this is consistency checking, not execution attestation.

Funded-join and later suites, provider-digest/engine validation, unknown-log
handling and aggregate `COMBINED-RESULTS.json` schema belong to the enclosing
reader/producer. RECEIPT owns that reader integration; ATLAS owns the producer.
This helper does not claim those further suites as covered.

## Executed inputs and tests

Existing artifact10034414947 / run34166821802 attempt1, SHA-256
`1323e92edc15bfe7a767dc02c60ffb3c45a0254f802397cf8b820522094a49ab`:
unchanged core reader47c15bde gives51 methods; helper gives28 supplemental
methods,79 together, no helper problems. Exact checkout is in the example.
These are existing FINCH/ATLAS/WREN/INTEGRATION/GPT results, not rerun suites.

Historical artifact10033736596 / run34164624483 attempt1, SHA-256
`cb8ed67dd2749ecd69d414802c31d7b31c58cd2744675dd5c6b4e1a8a96a5d31`:
the original37 methods and core `INCOMPLETE` remain unchanged. There are zero
represented supplemental suites. No absence is relabeled as execution.

```sh
cd revenue/kaggriculture/cloud-selected-joint-checks
python3 -m unittest test_supplemental_receipt -v
```

22 self-contained tests pass, using synthetic parser fixtures only. Actual
artifact readbacks and source pins are in `SUPPLEMENTAL-VALIDATION.json`.
Original reader, tests, README and VALIDATION are unchanged. No new provider
job, game, seed, source export, default-policy change or owner-PC action.
