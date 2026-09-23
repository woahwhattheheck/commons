# Expensify #96135 — unit/state regression matrix

Pinned upstream main: `dd0e8b65546b6e2e8914e74c535da26cd85dacc5`.

These cases are a **source-derived deterministic acceptance matrix** for the selected implementation. This seat did not run a production or staging account and does not label these as executed upstream UI tests.

| Case | Persisted exclusion | Current workspace unit | Current summary | Current editor | Current no-edit Save | Required invariant |
|---|---|---|---|---|---|---|
| R1 matched km | `2 km` | km | `2 km` | `2 kilometers` | no-op | Preserve 2 km |
| R2 matched mi | `2 mi` | mi | `2 mi` | `2 miles` | no-op | Preserve 2 mi |
| R3 km -> mi drift | `2 km` | mi | `2 km` | **`2 miles`** | rewrites to **`2 mi`** | Must not relabel/re-stamp 2 km as 2 mi |
| R4 mi -> km drift | `2 mi` | km | `2 mi` | **`2 kilometers`** | rewrites to **`2 km`** | Must not relabel/re-stamp 2 mi as 2 km |
| R5 runtime conversion | `2 km` | mi/request mi | stored pair remains 2 km | n/a | n/a | Expense exclusion converts 2 km to ~1.24 mi; stored unit has semantic meaning |
| R6 fractional conversion | `2 km` | mi | product may want ~1.24 mi | current editor is integer-only | pasted `1.24` sanitizes toward `124` | No auto-conversion until precision/rounding contract exists |
| R7 manual unit rollback | `2 km` | km -> mi request fails | summary/pair must return to original state | must not retain mixed state | no semantic drift | Unit failureData and exclusion state stay coherent |
| R8 government auto-correction | `2 km` | auto-corrected to mi | stored pair still 2 km today | mismatch appears | unsafe if saved unchanged | Same invariant as manual unit change |
| R9 missing stored unit (hostile legacy) | `2, unit=undefined` | km | current summary fallback says `2 km` | current editor says `2 kilometers` | may stamp km | runtime currently defaults non-km/missing unit to **miles**; display/calculation must agree |
| R10 route re-entry after mismatch | `2 km` | mi | `2 km` | current editor again shows `2 miles` | unsafe again | Fix survives navigation/re-mount |
| R11 explicit replacement | `2 km` | mi | depends on selected product policy | admin intentionally enters a new mi value | pair becomes entered value + mi | Explicit edit may change physical exclusion |
| R12 repeated unit toggles | `2 km` | km -> mi -> km | stored pair remains coherent or is atomically migrated each time | never display mismatched number+unit | no compounding drift | Toggle count cannot compound conversion/rounding |

## Physical-distance assertions

Using exact unit semantics (1 mile = 1.609344 km):

- `2 km` is about `1.242742 mi`.
- Silently rewriting `2 km` as `2 mi` increases the physical exclusion by about **60.9%**.
- `2 mi` is `3.218688 km`.
- Silently rewriting `2 mi` as `2 km` decreases the physical exclusion by about **37.9%**.

The important assertion is not a particular display precision. It is that a unit transition cannot change physical meaning without an explicit conversion or an explicit admin edit.

## Minimal regression seams

### Editor-level

Given a policy with stored pair `{fixedDistance: 2, fixedDistanceUnit: "km"}` and custom-unit `attributes.unit="mi"`:

- the component must not present numeric `2` with a miles suffix as though it were the stored value;
- pressing Save without an explicit replacement must not emit `{fixedDistance: 2, fixedDistanceUnit: "mi"}`.

Mirror for mi -> km.

### Action-level

Exercise both unit-changing routes:

1. `setPolicyDistanceRatesUnit()`;
2. `setWorkspaceDistanceAutoUpdate()` with `shouldCorrectUnit=true`.

Whichever architecture is selected, both paths must preserve the measurement-pair invariant and define failure rollback.

### Calculation-level

Keep `getPolicyCommuterExclusionForDistance()` as the truth check: a stored `2 km` requested in miles must continue to remove the mile-equivalent of 2 km, not 2 miles.

Add the hostile legacy case where `fixedDistanceUnit` is absent so UI fallback and calculation fallback cannot disagree silently.

## Decision gate

Do not encode one proposal as “the fix” until the internal engineer resolves:

- automatic migration vs explicit re-entry;
- precision/rounding for converted values;
- whether legacy missing-unit data exists and which unit is authoritative for it;
- whether backend/Auth should own migration so all clients observe one canonical pair.
