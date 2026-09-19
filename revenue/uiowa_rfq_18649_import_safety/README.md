# Import safety — two lanes cannot be loaded into one process

**OPS-IMPORT-SAFETY.** A read-only audit, a reproduction, and a loader that fixes
the problem without editing any lane.

The defect exists only in the assembled kit. Every lane is correct on its own,
which is why no single work order can see it.

## What is wrong

58 of 59 landed lanes ship no `__init__.py`, and 18 files reach their siblings with
`sys.path.insert(0, HERE)`. Under that pattern a module name is global: the first
lane to import `cli` owns the name in `sys.modules`, and every later lane asking
for `cli` gets the first lane's file.

Reproduced against two real lanes on main:

```
lane A cli -> .../qa_refusal_contract/cli.py
lane B cli -> .../qa_refusal_contract/cli.py
SAME OBJECT: True
lane B FAILED: IndexError list index out of range
```

The `IndexError` is the part that costs time. The failure does not present as an
`ImportError` naming the real cause; it presents as the wrong code running, then
something unrelated breaking several frames away.

This matters because the integration spine (UIOWA-098) and the operator kit
(UIOWA-100) both have to load lanes into one process.

## Measured on main

`python3 importsafety.py scan /home/user/commons/revenue`, verbatim:

```
lanes                        : 65
lanes shipping __init__.py   : 1
files mutating sys.path      : 18
distinct top-level modules   : 203
files unreadable/unparsable  : 0
colliding module names       : 6
  ACTIVE_RISK                6
test-module collisions       : 0
```

| Module | Lanes |
|---|---|
| `schema` | `ai_use_inventory`, `milestone_packets`, `traceability` |
| `analyze` | `base_fee_economics`, `outcome_measurement` |
| `cli` | `qa_refusal_contract`, `uncertainty_lint` |
| `make_fixtures` | `release_provenance`, `release_recovery_case` |
| `model` | `ai_decision_case`, `report_visuals` |
| `sensitivity` | `ai_decision_case`, `base_fee_economics` |

**0 test-module collisions is a real positive result** and belongs next to the
defect: `python -m unittest discover` from a shared root does not silently skip a
lane's suite. That axis is clean.

Two of the six collisions are this seat's own lanes, both shipping a `cli.py`.

## The fix that edits no lane

`safe_import.load(lane_dir, module_name)` loads via `spec_from_file_location` and
registers the module as `uiowa_lane.<lane>.<module>` instead of `<module>`. Two
lanes can hold the same filename and neither shadows the other. **No lane renames
a file. No lane is edited.**

```
python3 importsafety.py reproduce
```

Verbatim:

```
NAIVE  sys.path.insert + import report
  lane A -> .../fixtures/lane_alpha/report.py
  lane B -> .../fixtures/lane_alpha/report.py
  SAME MODULE OBJECT: True
  lane A says: 'ALPHA: 3 findings'
  lane B says: 'ALPHA: 3 findings'

SCOPED  safe_import.load
  lane A -> .../fixtures/lane_alpha/report.py
  lane B -> .../fixtures/lane_beta/report.py
  SAME MODULE OBJECT: False
  lane A says: 'ALPHA: 3 findings'
  lane B says: 'BETA: 7 findings'
```

The two fixture lanes return **different values on purpose**. A fixture where both
lanes raise, or both return the same thing, cannot detect this bug — the failure is
not an exception, it is the wrong module answering plausibly.

`load_lane_isolated` additionally puts the lane's own directory first while the
module executes, so a module's internal sibling imports resolve inside its own lane.

## Run it

```
python3 importsafety.py scan <kit-root>
python3 importsafety.py scan <kit-root> --json
python3 importsafety.py reproduce
python3 importsafety.py reproduce <laneA> <laneB> <module>
python3 -m unittest test_import_safety.py      # 30 tests
```

Python 3 stdlib only, no network. Exit 0 when no `ACTIVE_RISK` collision, 1 when
there is, 2 on a usage error.

The CLI entry point is `importsafety.py`, not `cli.py`, because `cli` is one of the
names this tool reports.

## Risk classes

| Class | Meaning |
|---|---|
| `ACTIVE_RISK` | The name is shared **and** the kit contains `sys.path` insertion, so loading both lanes in one process shadows one |
| `LATENT` | The name is shared, but nothing currently loads lanes into a shared namespace. **Not reported as a defect** |
| `UNKNOWN` | Could not be determined — any unreadable or unparsable file forces this. **Never reported as clean** |

## Limitations

- **Static inspection only.** Nothing is imported or executed during a scan.
  Dynamic imports (`importlib.import_module` with a computed name, imports inside
  a function or a conditional) are not detected.
- **Top-level modules only.** A module in a lane subdirectory is not counted,
  because it is not reachable by a bare import from the lane root.
- **`safe_import.load` scopes only the module it loads.** If that module then does
  `import helper` internally, `helper` resolves through the ordinary path and can
  still collide; `load_lane_isolated` covers that for sibling imports. Neither form
  helps a module that mutates `sys.path` at import time itself.
- **A `LATENT` classification is a statement about the kit as it is today**, not a
  guarantee. Adding one `sys.path.insert` anywhere turns every latent collision
  active.

## Still UNKNOWN

- Whether any lane imports another lane's module **deliberately** — a collision
  would be a wanted behaviour there, and static inspection cannot tell the two
  apart. Each lane's owner knows; this audit does not.
- Whether the integration and operator lanes will adopt `safe_import` or resolve
  the collisions by renaming. This lane does neither on their behalf.
- Whether any consumer outside this repository imports these lanes by bare name.

## Scope

Read-only against every other lane. No file outside this directory is created,
edited, renamed or deleted. No score, rating, or ranking of lanes, authors or seats
is produced — asserted by `test_no_score_rating_or_ranking_field_is_emitted`.
