# Finding activation census

`host/finding_registry.py` implements visibility-plan D5. It keeps the three layers of a mechanism finding separate instead of allowing “the detector fired” to stand in for “the policy acted.”

Every finding has an exact id, canonical parent, durable evidence coordinate, and these census layers:

```text
detector_hits
candidate_callbacks
realized_actions
```

Each layer is exactly:

```json
{"state": "MEASURED", "count": 12, "search_space": "13 tapes x 719 authored steps"}
```

The `state` is one of three exact values:

- `MEASURED`: the declared search space was searched and `count` is a non-negative exact integer. A zero count means “searched this named space and observed zero.”
- `UNKNOWN`: the declared search space was searched or otherwise examined, but the result count is unavailable or indeterminate. `count` must be null.
- `NOT_SEARCHED`: the declared search space was not searched. `count` must be null.

For example, these two null counts deliberately do **not** mean the same thing:

```json
{"state": "UNKNOWN", "count": null, "search_space": "full replay searched; result unavailable"}
{"state": "NOT_SEARCHED", "count": null, "search_space": "targeted replay not executed"}
```

A missing or empty `search_space` is invalid in every state. Counts are strict non-negative integers when measured; booleans, floats, strings and negatives are rejected. The registry does not assume detector/callback/action counts must be numerically monotone because one detector event may legitimately fan out to more than one callback depending on the instrumented mechanism.

Example input:

```json
{
  "version": 1,
  "findings": [
    {
      "id": "row-shed-falsey-slot",
      "canonical_parent": "titan/v3.1-20260911@<sha>",
      "evidence": "artifact:<sha256>",
      "detector_hits": {"state": "MEASURED", "count": 131, "search_space": "13 x 719 authored actions"},
      "candidate_callbacks": {"state": "MEASURED", "count": 19, "search_space": "13 x 719 authored actions"},
      "realized_actions": {"state": "NOT_SEARCHED", "count": null, "search_space": "targeted replay not yet executed"}
    }
  ]
}
```

Run:

```bash
python host/finding_registry.py findings.json --pretty
python host/finding_registry.py findings.json --finding row-shed-falsey-slot --pretty
```

The rendered row includes `complete_census`, `unknown_layers`, `not_searched_layers`, and `zero_layers`; aggregate output counts complete versus incomplete findings. A census is complete only when all three layers are `MEASURED`. Input and output order are deterministic by finding id.

`test_finding_registry.py` covers zero/unknown/not-searched separation, required search-space custody, state/count consistency, exact integer typing, complete three-layer shape, duplicates, unknown fields, version strictness and deterministic ordering without network or runner dependencies.
