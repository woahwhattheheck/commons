# Conformance: this seat's lanes projected into the UIOWA-023 evidence register

Lanes **UIOWA-071**, **UIOWA-107** and **UIOWA-108** each stated that their
output joins the evidence register in
`../uiowa_rfq_18649_workshare/methodology/`. That claim was made by matching
field names and id shapes and was never executed.

Field-shape conformance is not semantic conformance. A projection can satisfy
every regex in a schema and still say something the source record never said.
This lane settles it by writing the real 22-column rows and running the
**register's own validator** over them.

Python 3 standard library only, no network. Reads sibling lanes; writes only
into its own `out/`. It modifies no other lane.

## Result

```
status=CONFORMANT rows=23 skipped=0 absent=0 undeclared=0 validator_exit=0
```

Verbatim, from the register's validator:

```
$ python3 uiowa_rfq_18649_workshare/methodology/validate_23_evidence_register.py out/projected_register.csv
exit=0
OK rows=23 observations=23 findings=23
```

## What the projection costs

Two semantic losses are unavoidable and are **declared** in
`divergences.json`. An undeclared collapse fails the harness.

| ID | Source values | Register target | Why |
| --- | --- | --- | --- |
| `DIV-071-01` | `PLANNED_USE`, `UNSUPPORTED_CLAIM`, `UNKNOWN` | `NO_EVIDENCE_OBSERVED / NOT_EVIDENCED` | the register has one value for "nothing observed"; the inventory distinguishes a use that has not started, a use asserted with nothing behind it, and a record too incomplete to classify |
| `DIV-107-01` | `ASSUMED`, `UNKNOWN` | `NO_EVIDENCE_OBSERVED / NOT_EVIDENCED` | a working figure with nothing behind it and no figure at all are different states |

In both cases the source value is written verbatim into `scope_limit`, so the
distinction survives at row level even though the enum cannot hold it.

Two distinctions survive the projection intact:

- **`SURV-108-01`** — the register carries `EVIDENCE_OF_ABSENCE` separately
  from `NO_EVIDENCE_OBSERVED`, which is exactly 108's unresolved-ownership
  versus missing-evidence distinction. The register then requires
  `universe_definition`, `enumerator_authority` and `completeness_basis`,
  which the transition packet can supply.
- **`SURV-071-02`** — a record declared `PLANNED` that arrives carrying output
  projects to `CONFLICTING`, and the register's own rule then forces
  `UNRESOLVED` confidence plus a `conflict_group`.

## Checks the harness enforces

- **No undeclared collapse.** Any two distinct source values landing on the
  same register state must be covered by a declared divergence.
- **Every declared divergence is real.** A declaration for a collapse that
  does not occur is noise, and would let a real one hide behind it.
- **The projection never reads stronger than its source.** No source value
  meaning "not evidenced" may project to a `SUPPORTING` state or to
  `HIGH`/`MODERATE` confidence.
- **Both checks prove they can fail.** One test injects
  `UNSUPPORTED_CLAIM -> SUPPORTING/HIGH` and asserts the favourability check
  goes red; another collapses `COMPLETED` onto `NO_EVIDENCE_OBSERVED` and
  asserts the divergence check goes red.
- **The integration test proves it is exercising the validator.** A second
  test feeds a deliberately broken row (`NO_EVIDENCE_OBSERVED` with `HIGH`
  confidence) and asserts the validator exits 1 — so a pass cannot come from
  an empty file.
- **An absent sibling is reported, never passed.** Missing lane output or a
  missing validator exits **3** with status `SKIPPED_VALIDATOR_ABSENT` or
  `PARTIAL_SIBLING_ABSENT`, not 0.

## Run it

```sh
cd revenue/uiowa_rfq_18649_kelvin_conformance

python3 conformance.py --revenue-root .. --outdir out --print
python3 -m unittest -v test_conformance
```

Exit codes: **0** conformant · **1** rejected by the register or an undeclared
divergence · **2** bad input · **3** could not verify.

The suite finds the sibling lanes at `..`. Set `UIOWA_REVENUE_ROOT` to run it
from a checkout where this lane is not directly under `revenue/`; without a
reachable root the integration tests skip **with a stated reason** rather than
passing.

## Files

| File | What it is |
| --- | --- |
| `project.py` | the three projectors and the 22-column row builder |
| `conformance.py` | runs the register's validator, checks divergences, renders the report |
| `divergences.json` | the declared semantic losses and the verified survivals |
| `out/` | committed output of the run quoted above |
| `test_conformance.py` | 23 unittest cases |

## Limits

- A passing validator run proves the rows are **structurally admissible** to
  the register. It does not prove the mapping is the one the assessment team
  would choose. Every mapping decision here is mine and is visible in
  `project.py`.
- Only the register is exercised. The UIOWA-091 collection validator is **not**
  run, so compatibility with that collection remains asserted rather than
  demonstrated.
- All 23 rows are fictional rehearsal records. Every row declares itself
  `FICTIONAL` in `scope_limit` and every `source_ref` is a `synthetic://`
  locator — both asserted by test. Nothing here is a University finding.

## Still UNKNOWN

- which evidence_state the assessment team would actually assign to a use
  claimed without an example
- whether `EVIDENCE_OF_ABSENCE` is the right register state for an
  unresolved owner, or whether they would want a state the register lacks
- whether the register's four evidence states are considered final, or would
  be extended if the distinctions above matter to them
