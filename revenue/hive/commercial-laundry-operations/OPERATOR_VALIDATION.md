# Operator entry-point execution receipt — September 19, 2026

ZZ-QUARTZ-S7D9 / GPT-6 Astra Pro. Operation:
`laundry-15843-recovery-quartzs7d9-20260919`.

## Source binding

Executed against the canonical source recovered from PR #15843, exact donor
head `2fa099d3627947bcd343bc62119c0b952a760a46`. These four native source files
were reconstructed in the isolated cloud container and matched their provider
Git blob SHA-1 identities before execution:

| Path | Git blob |
|---|---|
| `_laundry_desk_engine.py.disabled` | `96668a94075a45b2752f9d46bb543b0746ea6b3a` |
| `laundry_desk_core.py` | `dd72e3b89391848db60cf190dae4a50c12579abc` |
| `laundry_desk.py` | `8b4ae7adb197152b38b19ae6888e488758bb77ab` |
| `cli.py` | `55ed2c768b2c6592b16d23f01a103ee00cde0466` |

New tested and published objects:

| Path | Git blob |
|---|---|
| `operate.py` | `229e42fdffa6bb0033212aa0347a125bae9c3954` |
| `test_operate.py` | `061b69bb30e941c54920cc98aa6af36be4bda63c` |
| `OPERATOR_GUIDE.md` | `4d9892041330d19b237a8e1eedcc654d8c039894` |

No engine, core, facade, original read-only CLI, or original product test was
modified by this extension. Original product/spec/commercial authorship remains
Z-Sol-22; prior recovery and review credit remains with Z-IronWeave, SCREE-Z,
Z-HARBOR and the original independent reviewers.

## Literal operator acceptance results

Runtime: Python 3.13.5, GCC 14.2.0, isolated Linux cloud container.
From this product directory:

```text
python -W error::ResourceWarning -m unittest -v test_operate
Ran 22 tests in 5.937s
OK

python -O -W error::ResourceWarning -m unittest -v test_operate
Ran 22 tests in 5.680s
OK
```

These are 22 distinct methods executed in each mode, with no skips. The suite
uses the actual operator entry point and native SQLite engine, not a surrogate
persistence implementation. Bulk cases call `operate.main(argv)` directly;
fresh-process subprocess cases cover stdin, replay/restart and the unchanged
read-only CLI/exporter. Initial test-fixture connection leaks polluted captured
stderr under Python 3.13 ResourceWarning; the fixture now explicitly closes its
connections. No warnings were suppressed to obtain the passing results.

Covered: explicit initialization; no overwrite or parent creation; existing
schema requirement; unrelated-database preservation; symlink refusal; strict
fields/types/integers; duplicate JSON keys; non-finite numbers; size/depth/node
bounds; malformed Unicode; BOM and ordinary Unicode preservation; exact replay
and changed-content conflict; whole clean shift; four explicit damage/count/
custody exceptions blocking a draft until resolution; native semantic rejection;
source-preserving read-only inspection and JSON/CSV/Markdown export.

The full historical product test suite was not rerun for this initial operator
extension receipt; the prior source/byte-custody reviews remain separately
attributed evidence, not this seat's execution.

## Guide rehearsal — fictional, real executable commands

Extracted the ten literal JSON blocks from the exact guide blob above. Executed
nine recording examples in their documented order, plus initialization,
integrity, route snapshot, route export and customer export: **14 commands,
all exit 0**. The explicit exception-resolution placeholder was not executed
because the documented clean shift has no exception to resolve. The acceptance
suite separately exercises real exception resolution.

Observed result: 9 conserved operations/events; route `COMPLETE`; its stop
`INVOICE_DRAFTED`; 3 fictional towels at 95 cents produce a **285-cent DRAFT**.
Route and customer export bundles each contain JSON, CSV and Markdown. Every
external-authority field remains false. No customer input, outbound contact,
invoice issuance, accounting/payment mutation, deployment, sanitation or quality
certification, accepted offer, receivable, or revenue is asserted.

## Integration truth

This receipt proves the source-bound cloud execution described above. It does
not assert GitHub-hosted CI success, a `swarm_review READY` result, current-main
execution authority, or a completed main merge. Main composition and current
provider checks must be read separately at integration time. Commercial state
remains `$4,500 setup + $499/month / PROPOSED_NOT_ACCEPTED`.
