# Single-runner readiness

Observed **2026-09-19** against `/home/user/commons/revenue`. Four hazards that a per-lane sweep cannot see, because a sweep gives every lane its own process and its own working directory.

| Hazard | Result |
|---|---|
| Working-directory independence | clean across 63 assessed lanes |
| Module-name collisions | 7 name(s) shared by more than one lane: `analyze`, `cli`, `make_fixtures`, `model`, `scan`, `schema`, `sensitivity` |
| Same-process crosstalk | 8 lane(s) silently receive another lane's module |
| State leakage | no lane wrote outside itself (63 assessed) |

**Working-directory safe:** yes. **Single-process safe:** no.

## Working-directory independence

Every suite was run twice: once with the working directory at the lane, once at the repository root. A lane that opens a fixture by a path relative to the process working directory passes the first and fails the second, and the first run alone always looks fine.

**No lane differed.** 63 lanes assessed, 6 not assessed (no test suite). This is a verified property, not an assumption.

## Module-name collisions

155 distinct top-level module names across 69 lanes. Test modules are excluded: a runner imports them by their own name and they are not what another lane imports.

| Module | Lanes |
|---|---|
| `analyze.py` | `uiowa_rfq_18649_base_fee_economics`, `uiowa_rfq_18649_outcome_measurement` |
| `cli.py` | `uiowa_rfq_18649_qa_refusal_contract`, `uiowa_rfq_18649_uncertainty_lint` |
| `make_fixtures.py` | `uiowa_rfq_18649_release_provenance`, `uiowa_rfq_18649_release_recovery_case` |
| `model.py` | `uiowa_rfq_18649_ai_decision_case`, `uiowa_rfq_18649_report_visuals` |
| `scan.py` | `uiowa_rfq_18649_exit_signals`, `uiowa_rfq_18649_import_safety` |
| `schema.py` | `uiowa_rfq_18649_ai_use_inventory`, `uiowa_rfq_18649_milestone_packets`, `uiowa_rfq_18649_traceability` |
| `sensitivity.py` | `uiowa_rfq_18649_ai_decision_case`, `uiowa_rfq_18649_base_fee_economics` |

## Same-process crosstalk

Demonstrated, not argued. For each collision a fresh process adds one lane, imports the module, then adds the next lane and imports the same name. Python caches by name, so the second request returns the first lane's module object.

### `analyze`

1 lane(s) asked for their own `analyze` and received another lane's file, with no error raised.

- `uiowa_rfq_18649_base_fee_economics` asked for `analyze` - received `uiowa_rfq_18649_base_fee_economics/analyze.py`
- `uiowa_rfq_18649_outcome_measurement` asked for `analyze` - received `uiowa_rfq_18649_base_fee_economics/analyze.py`

### `cli`

1 lane(s) asked for their own `cli` and received another lane's file, with no error raised.

- `uiowa_rfq_18649_qa_refusal_contract` asked for `cli` - received `uiowa_rfq_18649_qa_refusal_contract/cli.py`
- `uiowa_rfq_18649_uncertainty_lint` asked for `cli` - received `uiowa_rfq_18649_qa_refusal_contract/cli.py`

### `make_fixtures`

1 lane(s) asked for their own `make_fixtures` and received another lane's file, with no error raised.

- `uiowa_rfq_18649_release_provenance` asked for `make_fixtures` - received `uiowa_rfq_18649_release_provenance/make_fixtures.py`
- `uiowa_rfq_18649_release_recovery_case` asked for `make_fixtures` - received `uiowa_rfq_18649_release_provenance/make_fixtures.py`

### `model`

1 lane(s) asked for their own `model` and received another lane's file, with no error raised.

- `uiowa_rfq_18649_ai_decision_case` asked for `model` - received `uiowa_rfq_18649_ai_decision_case/model.py`
- `uiowa_rfq_18649_report_visuals` asked for `model` - received `uiowa_rfq_18649_ai_decision_case/model.py`

### `scan`

1 lane(s) asked for their own `scan` and received another lane's file, with no error raised.

- `uiowa_rfq_18649_exit_signals` asked for `scan` - received `uiowa_rfq_18649_exit_signals/scan.py`
- `uiowa_rfq_18649_import_safety` asked for `scan` - received `uiowa_rfq_18649_exit_signals/scan.py`

### `schema`

2 lane(s) asked for their own `schema` and received another lane's file, with no error raised.

- `uiowa_rfq_18649_ai_use_inventory` asked for `schema` - received `uiowa_rfq_18649_ai_use_inventory/schema.py`
- `uiowa_rfq_18649_milestone_packets` asked for `schema` - received `uiowa_rfq_18649_ai_use_inventory/schema.py`
- `uiowa_rfq_18649_traceability` asked for `schema` - received `uiowa_rfq_18649_ai_use_inventory/schema.py`

### `sensitivity`

1 lane(s) asked for their own `sensitivity` and received another lane's file, with no error raised.

- `uiowa_rfq_18649_ai_decision_case` asked for `sensitivity` - received `uiowa_rfq_18649_ai_decision_case/sensitivity.py`
- `uiowa_rfq_18649_base_fee_economics` asked for `sensitivity` - received `uiowa_rfq_18649_ai_decision_case/sensitivity.py`

## State leakage

Measured on an isolated copy of each lane, never on the live tree. An earlier version of this check watched the real repository around each run and reported two lanes as leaking; they were not. Other seats were landing work into the same tree while it ran, and a before/after watch of a directory that other writers share attributes their writes to whatever happened to be running. `__pycache__` is excluded as a side effect of executing Python.

No lane wrote, modified or removed a file outside its own directory during its test run. 63 lanes assessed.

## Proposed fixes

A list, not an edit. Nothing outside this lane was modified, and which lane keeps the plain module name is the lane owners' decision.

- `analyze.py` in `uiowa_rfq_18649_base_fee_economics`, `uiowa_rfq_18649_outcome_measurement`: rename in all but one, or give each lane a package directory so it is reached as `<lane>.analyze`.
- `cli.py` in `uiowa_rfq_18649_qa_refusal_contract`, `uiowa_rfq_18649_uncertainty_lint`: rename in all but one, or give each lane a package directory so it is reached as `<lane>.cli`.
- `make_fixtures.py` in `uiowa_rfq_18649_release_provenance`, `uiowa_rfq_18649_release_recovery_case`: rename in all but one, or give each lane a package directory so it is reached as `<lane>.make_fixtures`.
- `model.py` in `uiowa_rfq_18649_ai_decision_case`, `uiowa_rfq_18649_report_visuals`: rename in all but one, or give each lane a package directory so it is reached as `<lane>.model`.
- `scan.py` in `uiowa_rfq_18649_exit_signals`, `uiowa_rfq_18649_import_safety`: rename in all but one, or give each lane a package directory so it is reached as `<lane>.scan`.
- `schema.py` in `uiowa_rfq_18649_ai_use_inventory`, `uiowa_rfq_18649_milestone_packets`, `uiowa_rfq_18649_traceability`: rename in all but one, or give each lane a package directory so it is reached as `<lane>.schema`.
- `sensitivity.py` in `uiowa_rfq_18649_ai_decision_case`, `uiowa_rfq_18649_base_fee_economics`: rename in all but one, or give each lane a package directory so it is reached as `<lane>.sensitivity`.

## What this does not claim

A clean result here means these four hazards were not observed. It is not a statement that any component is correct, and it is not a rating of any lane or any seat. Lanes without a test suite were not assessed and are not counted as either safe or unsafe.
