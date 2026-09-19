# Repair rehearsal

> **This is a proposal, not a decision.** The mechanically safe repairs below were applied to a *copy* of the roadmap and the result re-checked. The original input file was not modified.

| | errors | unknown | open questions | info |
|---|---|---|---|---|
| before | **4** | 3 | 1 | 7 |
| after | **0** | 2 | 4 | 8 |

## Repairs applied

- `remove_prerequisite` — Remove prerequisite 'X-06' from 'X-08'.
- `remove_prerequisite` — Or remove the reference to 'X-99' from 'X-04', if it was a typo or a dropped item.
- `set_phase` — Move 'X-03' to '90-180' - the earliest phase consistent with its prerequisites.
- `remove_prerequisite` — Remove 'X-05' from its own prerequisites.

Where a loop offered several equally valid cuts, exactly one was taken, chosen deterministically so the rehearsal is reproducible. That choice is **not** a recommendation: the other cuts in the same loop are just as valid and a planner has to pick the dependency that is actually wrong.

Any `remove_prerequisite` applied against an unresolvable reference removed a dependency the roadmap could not resolve. If one of those was a real dependency, defining the missing item is the correct repair instead.

## Still requires a planner

- **`feasibility_unknown`** Whether 'X-10' is placed consistently cannot be determined: something it depends on is unassigned, unresolved or caught in a loop. This is not the same as being placed correctly.
- **`unassigned_phase`** Item 'X-09' has no phase. It stays UNASSIGNED; the checker will not place it in the first phase or anywhere else.
- **`redundant_edge`** Item 'X-11' lists 'X-01' directly, but already reaches it through X-02. The direct edge can be removed without changing the plan.
