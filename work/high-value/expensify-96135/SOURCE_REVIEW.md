# Expensify #96135 — persisted-distance semantic review

Status: **pre-assignment source review only**. This packet does not claim an Expensify assignment, Upwork hire, upstream PR, upstream comment, production reproduction, or payout.

## Pinned state

- Upstream: `Expensify/App`
- Issue: `#96135` — “[$250] Rate-Exclude Commute unit remains mi after switching to kilometres until setting is re-saved”
- Advertised amount: **$250 USD** in the issue title / linked Upwork job; not an accepted payout.
- Upstream main: `dd0e8b65546b6e2e8914e74c535da26cd85dacc5`
- Current issue state at review: open, `External` + `Help Wanted`; issue owner `@Gonals`; C+ reviewer `@sobitneupane` is explicitly waiting for internal-engineer input before selecting a fix direction.
- C+ semantic checkpoint: issue comment `5509650093`.
- Detailed stored-pair proposal / dev reproduction: issue comment `5003823819`.

## The invariant

`commuterExclusions.fixedDistance` and `commuterExclusions.fixedDistanceUnit` form a **persisted measurement pair**. The numeric value must not be relabelled under a different unit without a numeric conversion.

This is not merely presentation state. Current runtime expense logic in `src/libs/DistanceRequestUtils.ts` converts the persisted fixed distance from its stored unit into the request's distance unit before subtracting it. A stored `{fixedDistance: 2, fixedDistanceUnit: "km"}` therefore means “exclude 2 kilometres,” including when the workspace later displays miles.

That makes “change only the unit label in the settings summary” unsafe: `2 km` rendered as `2 mi` changes the represented physical distance without changing the stored value.

## Current-main ownership map

### 1. Workspace unit changes do not update the stored pair

`src/libs/actions/Policy/DistanceRate.ts` blob `8022dda15b06c6fac6553a229428f1cd73992297`:

- `setPolicyDistanceRatesUnit()` optimistically updates the selected custom unit and its `attributes.unit`.
- It does not update `policy.commuterExclusions`.

This produces an intentional temporary mismatch: current workspace unit may be `mi` while the persisted commute exclusion remains `2 km`.

### 2. Government auto-update can create the same mismatch

The same source file's `setWorkspaceDistanceAutoUpdate()` says the distance unit is corrected to the country's expected unit when needed, “only the unit, not the rate amounts, same as the manual unit change.”

Its `shouldCorrectUnit` path writes `customUnits[customUnitID].attributes.unit`; it does not migrate `commuterExclusions`.

Any durable repair must cover both manual unit changes and this automatic unit-correction path, or the stale-pair condition can recur through a second entry point.

### 3. The settings summary currently describes the persisted pair truthfully

`src/pages/workspace/distanceRates/PolicyDistanceRatesSettingsPage.tsx` blob `d8bd1d0b2779fd3543815376eda4b8c139508294` renders:

- distance = `commuterExclusions.fixedDistance`
- unit = `commuterExclusions.fixedDistanceUnit ?? defaultUnit ?? "mi"`

When the stored pair is `2 km` and current workspace unit is `mi`, displaying `2 km` is semantically accurate.

### 4. The editor mixes two sources of truth and can silently change the physical distance

`src/pages/workspace/distanceRates/PolicyCommuterExclusionsPage.tsx` blob `6a8beb4ad1e5fa6309a3f342c7c1e49a47e38a97`:

- seeds `fixedDistanceInput` from the persisted numeric `fixedDistance`;
- labels that number using the **current workspace unit**;
- on save, if the unit differs, writes the unchanged number with the current workspace unit.

So stored `2 km` + current `mi` becomes an editor showing `2 miles`. Pressing Save without changing the number writes `{2, "mi"}`, increasing the physical exclusion by ~60.9%. The reverse `2 mi -> 2 km` shrinks it by ~37.9%.

That is the highest-confidence frontend defect because it violates the measurement-pair invariant without requiring a product decision about how the summary should be presented.

### 5. Current input rules make automatic frontend conversion a product decision, not a trivial patch

The editor accepts only positive integers and sanitizes input with `value.replaceAll(/\D/g, '')`.

A physical-preserving conversion such as `2 km -> ~1.24 mi` therefore cannot be round-tripped through the current editor. Pasting `1.24` becomes `124`.

Before implementing automatic conversion, Expensify needs an explicit precision/rounding contract: allow decimals, round to an integer, preserve a hidden canonical value, or migrate the pair server-side.

### 6. Server command shape does not carry the unit, so do not infer persistence semantics from request params alone

`src/libs/API/parameters/SetPolicyCommuterExclusionsParams.ts` blob `9c55f16f7a67bac62b8ad084d7d8ad205ec1db42` sends `policyID`, `commuterExclusionMethod`, and optional `distance`, but not a unit.

Client optimistic data does store `fixedDistanceUnit`, while the C+ reviewer supplied a backend-returned pair containing both fields. This packet therefore does **not** claim “the backend never persists the unit”; that earlier premise was explicitly retracted in the issue thread.

## Additional hostile compatibility edge

`fixedDistanceUnit` is optional in the Onyx type (`src/types/onyx/Policy.ts` blob `26963e55f4d0df34d4c4f65466879272597be834`).

If legacy/malformed data has `fixedDistance` but no `fixedDistanceUnit`:

- the settings summary falls back to the current workspace unit;
- runtime exclusion calculation in `DistanceRequestUtils.ts` treats every value other than explicit `"km"` as miles.

Thus a workspace currently in kilometres could display “2 km” while the calculation interprets the same legacy value as 2 miles. This is a **hostile/compatibility test case**, not a claim that normal current Auth payloads omit the unit.

## Recommended acceptance contract

1. Preserve `fixedDistance + fixedDistanceUnit` as one physical measurement.
2. No screen may pair a stored numeric value with a different unit label unless it converts the number.
3. A no-edit Save after a workspace-unit change must not alter the physical excluded distance.
4. Manual unit change and government auto-update unit correction must obey the same invariant.
5. The selected design must state precision/rounding semantics before converting between km and mi.
6. Legacy/missing-unit behavior must be explicit and consistent between display and calculation.

## Implementation decision boundary

The C+ reviewer has already identified three viable directions and is waiting on internal-engineer input:

- **Preferred durable:** atomically migrate/convert the stored pair when the workspace unit changes (including automatic unit correction), with an explicit rounding/precision contract.
- **Safe frontend interim:** if stored unit != current unit, do not seed the stored number under the new label; require an explicit new value or show the stored pair read-only.
- **Converted frontend display/editor:** convert into current unit everywhere, but first change the integer-only input/precision contract so the conversion cannot corrupt values.

Until that choice is made, the source-backed contribution is the invariant + regression matrix, not a speculative upstream implementation.
