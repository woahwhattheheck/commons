# Capacity-aware roadmap feasibility (UIOWA-116)

Connect resource ranges to roadmap feasibility: a real dependency engine plus role-capacity
arithmetic, so "this plan fits" is computed rather than asserted.

The completion bar is *"results preserve prerequisite order and show unmet capacity explicitly;
relative plans make no personal availability commitments."* All three are checkable properties,
so all three are checked.

## Run it

```bash
cd revenue/uiowa_rfq_18649_capacity_feasibility

# dependency + capacity checks (exit 1 if anything is an error)
python3 capacity_roadmap.py check --items data/roadmap-items.json \
                                  --capacity data/capacity-assumptions.json

# regenerate the ASCII roadmap, report and both planning tables
python3 capacity_roadmap.py plan  --items data/roadmap-items.json \
                                  --capacity data/capacity-assumptions.json \
                                  --outdir examples

python3 capacity_roadmap.py rules        # the rule table, self-documenting
python3 -m unittest -v test_capacity_roadmap
```

Python 3 standard library only. No installs, no network, no clock, no RNG — two operators get
byte-identical output, and a test asserts it.

## What is in here

| Path | What it is |
|---|---|
| `capacity_roadmap.py` | The engine: dependency graph, static checks, two planners, ASCII/Markdown/CSV renderers, CLI. |
| `data/roadmap-items.json` | Nine synthetic roadmap items with prerequisites and low/likely/high effort by role. |
| `data/capacity-assumptions.json` | Editable role capacity per phase, and the three scenarios. |
| `examples/roadmap-ascii.txt` | Dependency graph + all three scenarios as ASCII. 78 columns, no colour. |
| `examples/feasibility-report.md` | Checks, scenario comparison, and the unmet-capacity tables. |
| `examples/roadmap-planning-table.csv` | One row per item per scenario: level, prerequisites, proposed vs scheduled, why it moved. |
| `examples/capacity-by-role-phase.csv` | Demand vs capacity per role per phase, both views, all scenarios. |
| `test_capacity_roadmap.py` | 51 tests, `unittest`. |

Everything in `examples/` is generated. Change an estimate or a capacity number and re-run `plan`.

## A dependency engine, not a table that looks like one

- **Topological ordering** (Kahn, id-sorted at each step, so the order does not depend on how the
  file was written — asserted by a test that reverses the input).
- **Cycle detection** by DFS colouring. A cycle is reported as its exact path (`A -> B -> A`) and
  **scheduling is refused**, rather than emitting a confident order that cannot exist.
- **Phase-ordering violations.** `D005_PREREQ_AFTER_DEPENDENT` catches a prerequisite proposed in a
  *later* window than the item that depends on it. This is the defect a hand-built roadmap table
  hides best, and three tests cover it: the direct case, the transitive case, and the case that
  must **not** fire (a prerequisite in the *same* window is normal sequencing inside 90 days).
- **Parallelism is derived from reachability, not from vibes.** Two items are reported as
  parallelizable only when neither can reach the other in the graph. Sharing a dependency level is
  necessary but not sufficient, and a test builds a four-node graph where two same-level items are
  *not* independent to prove the difference is real.
- **Tracks** are the weakly connected components: chains of work that never touch. In the fixture,
  `RM-03 + RM-04` (alert routing) is completely independent of the seven-item approval/restoration
  chain, so it can be given to a different owner without coordination.

## Unmet capacity is shown, not absorbed

Two views are produced for every scenario, and the first one is the point:

1. **Plan as proposed** — items sit exactly where the roadmap put them, and the shortfalls are
   printed. A scheduler that slides work until it fits will *always* report a feasible plan; the
   shortfall that made it slide is the finding leadership actually needs.
2. **Capacity-feasible resequencing** — the scheduler walks topological order, never places work
   earlier than proposed (the proposed phase is a deliberate choice, not a floor to optimise away),
   and pushes an item later only when a role it needs has no room. Every move is reported with its
   reason: `prerequisite order` or `role capacity`.

Work that fits in no phase lands in **`BEYOND_HORIZON`** and is listed. It is never dropped off the
end of the plan.

### A bug this caught in its own first run

The first run reported the constrained scenario as `resequenced=FEASIBLE` while pushing **all nine
items** beyond the horizon. Beyond-horizon items stop contributing demand, so the per-phase capacity
table read perfectly clean — the exact absorption this lane exists to prevent, in the tool itself.
Fixed: a plan carrying beyond-horizon work is `INFEASIBLE` regardless of what the capacity table
says, and `test_a_plan_with_beyond_horizon_work_is_never_feasible` holds the line.

## UNKNOWN effort is not zero effort

`RM-06` (run a restoration exercise) genuinely cannot be estimated until `RM-05` supplies dataset
sizes and a restore target. Its `infra_operations` effort is `UNKNOWN`, and that propagates:

- the item **still schedules**, so the sequence stays coherent — it is not dropped for being
  unestimated;
- its phase reads `UNKNOWN (+1 unestimated)` and the verdict for that phase is **UNKNOWN, never
  FEASIBLE** — a phase whose cost nobody has estimated has not been shown to fit;
- `shortfall` and `headroom` are both `None` there, because neither is knowable.

`test_unknown_and_zero_produce_different_outcomes` runs the same fixture twice — once with
`UNKNOWN`, once with a literal `0` — and asserts the verdicts differ (`UNKNOWN` vs `FEASIBLE`). A
zero is a claim that the work is free. An absent estimate is not that claim.

## No personal availability commitments

Enforced at the loader, not requested in prose:

- capacity is stated per **role**; a capacity record carrying `person`, `name`, `email`, `assignee`
  or any other person-like key is **rejected on load**, at any nesting depth;
- role ids must be role-shaped (`iam_service_owner`), so `"Jane Smith"` is refused as a role;
- **no calendar dates anywhere.** Phases are relative windows only, and
  `test_no_generated_output_contains_a_calendar_date` greps every generated file for date-shaped
  strings and fails if one appears.

## What the three scenarios actually show

Computed by the tool, not asserted here — run `plan` and read it back:

```
constrained  proposed=INFEASIBLE resequenced=INFEASIBLE moved=3 beyond_horizon=1
expected     proposed=INFEASIBLE resequenced=UNKNOWN    moved=1 beyond_horizon=0
invested     proposed=UNKNOWN    resequenced=UNKNOWN    moved=0 beyond_horizon=0
```

That is the answer to "how do alternative resource ranges change the proposed sequence":

- **invested** (low estimates, capacity x1.4) — the proposed sequence holds; nothing moves.
- **expected** (likely, x1.0) — pipeline engineering is over-subscribed in 0-90 by 4 hours, so
  `RM-02` moves to 90-180. One move fixes it; the plan is then limited only by the UNKNOWN.
- **constrained** (high, x0.75) — three items move and `RM-09` does not fit inside the horizon at
  all. The honest read is that this programme does not complete in 180 days at this allocation.

Both a real strength and a real gap, from one fixture.

## Readable without colour

The ASCII view uses marks: `=` within capacity, `!` over capacity, `|` the capacity line, `.`
unused. A legend is printed at the top of every scenario.

```
|   0-90    pipeline_engineer        140.0   144.0  SHORT by 4.0 h           |
|                                  [===========================|!]           |
```

Every line is exactly 78 characters and pure ASCII; a test asserts the width, the ASCII-only
property, and the absence of terminal colour escapes.

## CSV provenance

Every CSV this lane writes carries a provenance statement as line 1:

```
# PROVENANCE: SYNTHETIC. FICTION. ...
```

A CSV is the most portable artifact here and the one most likely to be opened away from this
README. The statement is taken from the source data's `meta.provenance`, or implied from a
`meta.fiction_notice`; a source that declares neither produces
`PROVENANCE NOT DECLARED IN SOURCE`, never a guess in either direction — the requirement is a
provenance statement, not a fiction label, and a real measurement must not be stamped synthetic.

The banner is a `#` line, so a reader that takes line 1 as the header will misparse. The
documented contract is `read_csv_rows(path)`, which returns `(statement, rows)` and strips leading
`#` metadata lines. A test asserts the naive read misparses and the contract does not.

## What is real and what is draft

**Real and working now:** the graph algorithms, all fifteen rules, both planners, the renderers,
the CLI, the determinism guarantee and the 51 tests. Run them; the output is the evidence.

**Draft:** the scheduling model's granularity. Items are **atomic** — an item is done inside one
phase and is not split across two. Effort is charged to the phase the item lands in. Both are
reasonable for a 90-day planning window and both are visible in the code rather than buried; a
finer model would need real task decomposition that does not exist yet.

**Fiction, and labelled fiction:** every item, estimate, prerequisite and capacity number.
Northgate State University does not exist. **None of this is a University of Iowa finding,
recommendation, or plan, and nothing here should ever be presented as one.**

## University inputs that stay UNKNOWN

This lane has had no contact with the University and holds no University data.

- The real recommendation set and its prerequisites. Items carry a `rec` field so they link back,
  but the links are synthetic.
- The real phase assignments. `proposed_phase` mirrors the shape the phased-roadmap lane
  (UIOWA-085) emits; **this lane checks a proposed sequence, it does not author one.**
- Real effort ranges. `effort` mirrors the shape the effort estimator (UIOWA-086) and the
  opportunity portfolio (UIOWA-072, `portfolio.json`, unit-tagged ledgers kept separate) emit.
  Swap the file; no code changes.
- Real role capacity. Every number in `capacity-assumptions.json` is `ASSUMED` and editable. What
  share of a role's time is actually available to this programme is unknown and is not guessed.
- Whether restoration effort (`RM-06`) can be estimated at all before the dataset inventory exists.
  It stays UNKNOWN on purpose.

## Scope limits

No maturity score, no rating, no certification or compliance verdict, no peer percentile, no
individual performance scoring, and no named individual anywhere. Phases are relative windows; no
date is committed. The tool reports whether a proposed sequence fits stated assumptions — the
assumptions, and the decision, stay with the people who own the work.
