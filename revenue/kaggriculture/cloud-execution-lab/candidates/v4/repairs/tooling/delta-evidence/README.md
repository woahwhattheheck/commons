# Seat-aware evidence reporter recovery

Canonical home: `main`, under `candidates/v4`, as declared by `CANONICAL.json`.
This is one measurement-tooling recovery, not an alternate V4 or a gameplay key.
PR #12646 was retargeted to this canonical workspace after its initial old-line target was retired.

## Contents and provenance

The two top-level Python files are the recovered reporter and its focused suite.
The `donor/` files preserve the exact #12402 input bytes from commit
`bc3de14fff86079e70659fd3c2ea42ffd2101b97` before semantic repair.

| File | Git blob | Bytes |
|---|---|---:|
| `donor/v31_delta_distribution_report.py` | `e64975e8d9ef58551f9581c86068ead3d0e1f254` | 21605 |
| `donor/test_v31_delta_distribution_report.py` | `e626da18d85c717c273b49d87abbcc9d4856cce8` | 8501 |
| `v31_delta_distribution_report.py` | `a37f0be3eb7db79d6e7162cee3b7e472e2afab6a` | 22886 |
| `test_v31_delta_distribution_report.py` | `8d8ab4e2851c88a9eb53cdc1d973b726a129b4be` | 14177 |

The historical filenames are retained for source/API compatibility. No imports
into production, package materialization, evaluator implementation, runtime flags,
workflow, archive, provider or Kaggle state are changed by this pack.

## Contract

Each cell is keyed by opponent, seed and candidate seat. Nested generic `scores`
are player-ordered `[seat0, seat1]`; explicit `own`/`rival` are candidate-relative.
The tool recomputes the competitive-margin change from both players' scores;
it never trusts a supplied headline delta. It reports outcome transitions,
new losses, lost wins and seat/opponent/activation strata. Measurement alone is
not an economic-promotion verdict; explicit policy options are separate.

The V4 recovery retains all nine original tests and adds fifteen regressions for:

- mixed separate-arm and paired-cell root layouts, which previously silently
  selected one evidence set even when another contradicted it;
- oversized integer conversion and nonfinite derived margins/deltas/statistics;
- malformed direct-API rows and incomplete separate-arm documents;
- seat-swap equivalence, preserved supported paired-container aliases, and
  CLI success/policy/data-error distinctions.

The repaired bad-data paths return CLI status 2, emit no report and do not
replace an existing output file. Extremely large intermediate sums are rejected
conservatively even when a different arithmetic implementation could represent
the final mean. Other malformed JSON inputs are outside the tested coverage.

## Executed checks

Run from this directory:

```sh
python -m py_compile v31_delta_distribution_report.py test_v31_delta_distribution_report.py
python -m unittest -v test_v31_delta_distribution_report
python -O -m unittest -v test_v31_delta_distribution_report
python v31_delta_distribution_report.py /path/to/paired-evidence.json
```

Exact historical donor blob verification passed. The donor's original suite
passed 9/9 in normal and optimized Python. The recovered suite passed **24/24
normal and 24/24 optimized** in the local execution environment; both published
Git blob IDs equal the tested local bytes. These are local source-level receipts,
not hosted CI, complete-game benchmarks, runtime integration or promotion claims.

A deterministic local differential run (random seed 12646) compared 2,000 valid
evidence documents across both seats, both root layouts, varied opponents and
activation strata. All 2,000 normalized reports exactly matched the donor.
The fifteen added boundary tests are red against the unmodified donor
(unittest reported 8 failures and 5 errors), and green against the repaired source.

Source SHA-256: `8d674f10f420b43a0723c33eb7b125559c23e6306b9aa0153c24912dde3665b7`.
Test SHA-256: `7ab4c8636c8f4aa041582ddd973405437a7e824b4eadf788d03e383fa0fc25b9`.
