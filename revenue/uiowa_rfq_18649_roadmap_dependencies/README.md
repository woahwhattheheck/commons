# UIOWA-115 — Roadmap dependency consistency check

A graph check over recommendation prerequisites, shared dependencies and
proposed phases. It finds **cycles**, **missing prerequisite references** and
**phase inversions**, and names the **exact edge to repair** in each case.

Built for work order **UIOWA-115** (seat `OP5-JUNIPER`). Python 3 standard
library only, no network, deterministic output.

---

## Two decisions do most of the work

**1. It never emits a linear order.**

Asked to check a roadmap, the obvious move is to return a topological sort. That
output is *correct*, and it is *destructive*: it silently converts "these five
groups can go at once" into "do R-04, then R-05, then R-06, then R-09, then
R-11", and a planner reading it schedules a year of work that the dependency
graph says takes four months.

So this tool reports dependency **levels**. If A is a prerequisite of B then
`level(B) > level(A)`, therefore two items at the same level have no path
between them in either direction and are **provably** independent. Parallelism
is the output rather than a casualty of it. `test_the_checker_emits_no_linear_execution_order`
asserts that no `topological_order` / `execution_order` / `sequence` field exists
to be misread, and `test_items_in_a_parallel_group_have_no_path_between_them`
re-derives reachability from the emitted edges and proves the claim for every
reported group.

**2. An unresolvable reference is never read as satisfied.**

A prerequisite pointing at an item nobody defined, an item with no phase, a
`prerequisites` field that is not a list — each of these makes the surrounding
feasibility `UNKNOWN`. Dropping what you cannot resolve turns a broken plan into
a clean-looking one, which is the most expensive possible output of a checker.

That is why there are four severities, not two:

| severity | meaning |
|---|---|
| `error` | Must reach zero. The roadmap contains a contradiction. |
| `unknown` | The roadmap does not contain enough information to decide. **Not a pass and not a failure**, and no repair the tool can apply will clear it. |
| `open_question` | Defensible, but someone should confirm it. |
| `info` | True and useful; nothing is wrong. |

A repaired roadmap can then honestly read *zero errors, two unknowns still
requiring human input* instead of being rounded up to "passed".

---

## Run it

```bash
cd revenue/uiowa_rfq_18649_roadmap_dependencies

# a coherent roadmap
python3 depcheck.py --outdir out_consistent

# a deliberately broken one, plus the repair rehearsal
python3 depcheck.py --roadmap fixtures/roadmap_inconsistent.json \
                    --outdir out_inconsistent --rehearse-repairs

# malformed input
python3 depcheck.py --roadmap fixtures/hostile_roadmap.json --outdir out_hostile

# tests
python3 -m unittest -v test_depcheck
```

Exit code is `1` when there are errors, `0` otherwise. `--fanin-threshold N`
(default 3) sets when a shared prerequisite is called a chokepoint.

### Outputs

| File | What it is |
|---|---|
| `dependency_report.md` | Readable diagnostics, the parallel-work table, and a **Mermaid graph that GitHub renders inline** — no Graphviz needed to see the picture. |
| `graph.dot` | The same graph for Graphviz, with cycle edges in red. |
| `graph.json` | Nodes, edges, levels, earliest feasible phase, parallel groups, every finding with its repairs, and a `content_digest`. |
| `findings.csv` | One row per finding, carrying the exact `prerequisite_id` → `dependent_id` edge. |
| `proposed_roadmap.json` | *(`--rehearse-repairs`)* the input with the mechanically safe repairs applied — **a proposal, clearly labelled, written to a new file; the input is never modified.** |
| `rehearsal_report.md` | *(`--rehearse-repairs`)* before/after counts, what was applied, and what still needs a planner. |

---

## What the checks actually find

### The coherent roadmap (`fixtures/roadmap_consistent.json`)

```
roadmap RM-CONSISTENT-v1: 11 items, 10 edges
  errors=0  unknown=0  open_questions=1  info=8
  parallel in 0-90     level 0: R-01, R-02, R-03
  parallel in 90-180   level 1: R-04, R-05, R-06, R-09, R-11
  parallel in 180+     level 2: R-07, R-08, R-10
```

Zero errors, and it still says two useful things. The one open question is a
**chokepoint**: `R-03` (agree a shared change-record format) is a prerequisite
for three separate groups' work. If it slips, all three slip — worth knowing
before the phase starts, and invisible in a list view. The eight informational
findings are **slack**: every 90-180 and 180+ item could start a phase earlier
as far as dependencies are concerned. That is float, not a fault — phases carry
capacity, budget and external timing that the graph knows nothing about — so it
is reported as information and never as a problem.

### The broken roadmap (`fixtures/roadmap_inconsistent.json`)

```
roadmap RM-INCONSISTENT-v1: 13 items, 10 edges
  errors=4  unknown=3  open_questions=1  info=7
  ERROR dependency_cycle       X-06, X-07, X-08
  ERROR missing_prerequisite   X-99 -> X-04
  ERROR phase_inversion        X-02 -> X-03
  ERROR self_dependency        X-05 -> X-05
  rehearsal: errors 4 -> 0, unknown 3 -> 2 (a planner must clear the rest)
```

Each error names its edge and its repairs, marked by who may apply them:

```
**`phase_inversion`** — edge `X-02` → `X-03`
Item 'X-03' sits in '0-90' but requires 'X-02', which cannot complete before '90-180'.
- (applyable)       Move 'X-03' to '90-180' - the earliest phase consistent with its prerequisites.
- (needs a planner) Or move 'X-02' to '0-90' or earlier, if that work can genuinely start sooner.
```

**Cycles use Tarjan's SCC, not a DFS back-edge scan.** A back-edge scan names the
one edge the traversal happened to close the loop on, which is an accident of
iteration order. A planner needs *every* edge in the entangled set, because any
one of them is a valid cut and only a human knows which dependency is the wrong
one. The report offers all three cuts for `X-06 → X-07 → X-08` and refuses to
recommend one.

**Inversions cascade.** `earliest_feasible_phase` is computed up the whole
prerequisite chain, so an item whose *prerequisite is itself mis-phased* is still
caught. `test_inversion_cascades_through_a_misplaced_prerequisite` builds exactly
that case: `C` looks fine against `B`'s stated phase and is not fine, because `B`
cannot happen until 180+. A checker comparing only against a direct
prerequisite's stated phase misses it.

**The two surviving unknowns are the point.** `X-09` has no phase; the checker
will not place it. `X-10` depends on `X-09`, so whether `X-10` is ordered
correctly is genuinely undecidable — and "we couldn't tell" is reported as its
own state, not folded into "fine".

### Malformed input (`fixtures/hostile_roadmap.json`)

Six named errors — an item with no id, a duplicate id, `prerequisites` supplied
as a string, a prerequisite entry that is a number, a phase the phase list never
defines, and two phases sharing an order value (so "earlier than" is ambiguous
between them). Four unknowns follow from them. Nothing is defaulted: a blank
phase is `UNASSIGNED`, never the first phase.

---

## Tests

```
Ran 47 tests in 0.036s

OK
```

**A real bug the suite caught, reported rather than quietly patched.** The first
full run crashed with `IndexError: list index out of range` on a roadmap whose
phase list was empty or entirely invalid: every item resolved to earliest-phase
index `0`, which was then used to index an empty list. A checker that crashes on
malformed input is worse than one that reports it, since the operator learns
nothing. Fixed with a `phase_at()` guard that returns `UNKNOWN` for any index
outside the defined phases, pinned by
`test_a_roadmap_with_items_but_no_phases_reports_unknown_not_pass` and
`test_non_integer_phase_order_is_rejected_rather_than_guessed`.

The suite's substance is hostile and missing data: dangling references,
self-dependencies, two- and three-item loops, cascading inversions, unreadable
prerequisite lists, blank and undefined phases, duplicate ids, duplicate and
redundant edges, an empty roadmap, and a non-integer phase order.

---

## What is real, what is draft

**Real and working:** the checker, the SCC cycle detection, the cascading phase
arithmetic, the level/parallelism computation, the repair rehearsal, the four
exports and the graph rendering. Run it and it does what this file says.

**Fiction, labelled as such:** all three fixtures. `R-*`, `X-*` and `H-*` items
are invented to exercise the checker. **Nothing in this directory is a University
roadmap, a University recommendation, or a University finding.**

**Deliberately not in scope:** no effort, cost or duration estimates — this tool
answers *"can this order happen at all?"*, not *"how long will it take?"*, and
mixing the two would put a made-up number next to a real structural finding. No
scoring, maturity level, or benchmark position. The checker reports; it never
rewrites the planner's input file.

### University inputs still UNKNOWN

- The real recommendation set and its prerequisite relationships — this tool
  reads them, it does not derive them.
- Whether the real phase boundaries are the 0–90 / 90–180 / 180+ used here.
- Whether same-phase dependencies are acceptable in practice, which decides
  whether `same_phase_dependency` is an open question or an error locally.
- Capacity and external timing, which is why **slack is never reported as a
  recommendation to pull work earlier** — the graph cannot see the constraint
  that put the item where it is.
- For every `missing_prerequisite`: whether the referenced item is a real piece
  of work that was never written down, or a typo. The tool cannot know, so it
  offers both repairs and marks only one as safe to apply.
