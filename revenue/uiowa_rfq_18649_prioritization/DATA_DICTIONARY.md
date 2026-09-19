# Data dictionary — prioritization worksheet

Every field the calculator reads and writes. The distinction that matters most is at the top.

---

## 0 versus UNKNOWN

These are different facts about the world and the tool keeps them apart everywhere.

| | Meaning | Scored? | Ranked? | Written in CSV as |
|---|---|---|---|---|
| `0` | **Assessed.** Somebody looked and expects no effect on this dimension. | Yes — contributes a term of exactly 0.0 | Yes | `0` |
| UNKNOWN | **Not assessed.** Nobody has said. | No | No — held in the `NEEDS_ESTIMATE` bucket | `UNKNOWN`, with rank `NOT_RANKED` and a populated `blocked_by` |

A `0` in a score column is a result. `UNKNOWN` is an open question. Collapsing them is the
failure mode this tool exists to prevent, and `test_zero_and_missing_are_not_the_same_outcome`
asserts it directly.

Complexity has no `0`, because "no effort" is not a real estimate — it would divide an item
straight to the top of the list. A submitted `0` is refused by name, not coerced.

---

## Input: recommendation record

`fixtures/synthetic-recommendations.json`, under `recommendations[]`.

| Field | Type | Required | Notes |
|---|---|---|---|
| `recommendation_id` | string | **yes** | Unique. Convention `REC-SYN-{GROUP}-{AREA}-{NNN}`, matching the evidence register's `FND-SYN-*` shape. Duplicates are refused. |
| `title` | string | no | Shown in every output. |
| `group` | string | no | `ESS` / `RIS` / `IAM` in the synthetic set. Carried through, not interpreted. |
| `area` | string | no | `SD` / `SEC` / `DEP` / `AI` in the synthetic set. Carried through, not interpreted. |
| `finding_ids` | list of string | no | Traceability back to findings. An empty list ranks normally but is reported under "Not traceable to a finding". |
| `effects.quality` | estimate | no | Missing → UNKNOWN. |
| `effects.security` | estimate | no | Missing → UNKNOWN. |
| `effects.delivery` | estimate | no | Missing → UNKNOWN. |
| `complexity` | estimate | no | Missing → UNKNOWN. Scale starts at 1. |
| `notes` | string | no | Free text, carried through. |

Any effect dimension other than `quality` / `security` / `delivery` is refused rather than
ignored — silently dropping a dimension somebody took the trouble to estimate would be its own
kind of lie.

### The `estimate` type

Either a bare value:

```json
"quality": 3
```

or an object carrying the justification next to the number:

```json
"quality": {"value": 3, "basis": "removes the ambiguity about which approval path a change took"}
```

**Accepted as UNKNOWN:** the key absent entirely, `null`, `""`, `"UNKNOWN"` (any case), `"n/a"`,
`"na"`, `"tbd"`, `"none"`, `"null"`, `"?"`, or an object with a `basis` but no `value`. That last
form is the useful one — it records *why* there is no estimate:

```json
"quality": {"basis": "what assistive generation is doing to code quality is exactly what the recommended inventory would find out"}
```

**Refused, with the recommendation and field named:** out-of-range numbers, fractional numbers,
booleans (`true` would otherwise become `1`), and unparseable text like `"high"` — somebody's
estimate expressed in words is not an absence, and guessing which number they meant is not this
tool's job.

---

## Input: weight scenario

`fixtures/weight-scenarios.json`, under `scenarios`.

| Field | Type | Notes |
|---|---|---|
| `weights.quality` | number ≥ 0 | |
| `weights.security` | number ≥ 0 | |
| `weights.delivery` | number ≥ 0 | |
| `rationale` | string | Why anyone would hold this view. Not read by the calculator. |

Weights need not sum to 1.0 — they are normalized, and both the entered and the used values are
reported. Negative weights are refused. All-zero weights are refused (`at least one dimension
must carry weight`).

A weight of exactly `0` is legal and meaningful: it says this dimension does not count here,
which is what makes an unknown in that dimension non-material. See `non_material_unknowns`.

---

## Output: scored record

| Field | Notes |
|---|---|
| `status` | `RANKED` or `NEEDS_ESTIMATE`. |
| `rank` | Integer, or `null` for `NEEDS_ESTIMATE`. Never `0`. |
| `benefit` | Weighted sum. `null` when unranked. |
| `priority_score` | `benefit / complexity`. `null` when unranked. |
| `arithmetic` | The substituted calculation as a string, e.g. `benefit = 0.350x3 + 0.400x5 + 0.250x3 = 3.8; score = 3.8 / 2 = 1.9`. For unranked items it says which field has no estimate and that it is not scored as 0. |
| `contributions.{dim}.weight` | Normalized weight used. |
| `contributions.{dim}.estimate` | The value, or `null` if unestimated. |
| `contributions.{dim}.estimate_is_unknown` | Explicit boolean, so a consumer never has to infer "missing" from a `null` that could also mean zero. |
| `contributions.{dim}.contribution` | `weight x estimate`, or `null` if unestimated. |
| `contributions.{dim}.basis` | The justification text, if one was supplied. |
| `unknown_fields` | Every unestimated field on the record, regardless of weighting. |
| `blocking_unknowns` | The subset that prevents ranking **under the active weights**. |
| `non_material_unknowns` | Unestimated fields in zero-weight dimensions. Still missing; just cannot change this order. |
| `score_bounds` | Present only when unranked. See below. |
| `estimate_urgency` | `DECISION_BLOCKING` / `NOT_DECISION_BLOCKING`. Unranked items only. |
| `estimate_urgency_basis` | The comparison that produced the label, in words. |
| `tie_group_size` | `1` when not tied. |
| `is_tied` | Boolean. |
| `display_order_is_not_priority` | `true` inside a tie group — position within the group is alphabetical, not a ranking. |
| `traceable_to_finding` | `false` when `finding_ids` is empty. |

### `score_bounds`

Present only on unranked items. **A bound, not a score.** The unknown is walked across its full
admissible range (effects 0–5, complexity 1–5) to produce:

| Field | Notes |
|---|---|
| `score_if_unknowns_lowest` | Worst case: unknown effects at 0, unknown complexity at 5. |
| `score_if_unknowns_highest` | Best case: unknown effects at 5, unknown complexity at 1. |
| `basis` | Text restating that this is a bound. |

`estimate_urgency` is derived from it: if `score_if_unknowns_highest` reaches or exceeds the
current top ranked score, the item could lead the list and the ranking is not decidable without
the estimate.

---

## Output: CSV columns

`rank`, `status`, `recommendation_id`, `title`, `group`, `area`, `finding_ids`,
`quality_estimate`, `security_estimate`, `delivery_estimate`, `complexity`, `benefit`,
`priority_score`, `blocked_by`, `non_material_unknowns`, `estimate_urgency`, `score_bound_low`,
`score_bound_high`, `tie_group_size`, `arithmetic`.

Conventions that exist specifically so a spreadsheet cannot misread a gap:

- `rank` for an unranked row is the literal `NOT_RANKED` — never blank (which sorts as 0) and
  never `0`.
- `benefit` and `priority_score` for an unranked row are the literal `UNKNOWN`.
- `finding_ids` for an untraceable row is the literal `NONE`, not blank.
- Multi-value cells are `|`-delimited.
- Every input row appears exactly once. Gaps are never dropped to tidy the table.

---

## Output: sensitivity

| Field | Notes |
|---|---|
| `scenarios[]` | Each weighting, entered and normalized, with its formula. |
| `results{}` | The full ranking under each scenario, keyed by scenario name. |
| `rank_stability[]` | Per recommendation: rank under each scenario, best, worst, spread, and a `stability` label. |
| `leader_by_scenario{}` | Who holds rank 1 under each weighting. A list, because rank 1 can be tied. |
| `top_item_stable` | `false` means changing the assumptions changes who goes first. |
| `interpretation` | The plain-language reading, generated from the result rather than asserted. |

`stability` labels: `PINNED` (same rank under every scenario), `MOVES`, `ENTERS_UNKNOWN_BUCKET`
(ranked under some weightings, held for a missing estimate under others), `NEVER_RANKED`.

## Output: crossover sweep

| Field | Notes |
|---|---|
| `dimension` | The weight being walked 0.0 → 1.0. |
| `steps` | Sample count. |
| `points[]` | Every sampled weight with the resulting order. Omitted from CLI JSON unless `--include-sweep-points`. |
| `crossovers[]` | Every weight at which the order changed, with a plain-language `changed` list. |
| `leader_changes[]` | The subset where rank 1 changed hands. |
| `materiality_changes[]` | The subset where an item entered or left the ranked list — i.e. where a missing estimate started or stopped mattering. |
| `reorders` | `false` means the ranking is insensitive to this assumption across its whole range. |

---

All content in this directory is synthetic. No field above was populated from University of Iowa
data, and no output is a finding, a maturity score, a compliance verdict, a peer comparison, or
an assessment of any individual.
