# Factor lane registry

`host/lane_registry.py` implements visibility-plan D4. A registry is strict JSON with version `1` and one row per factor lane.

Every row must carry the five-field factor report:

1. `canonical_parent` — exact root/ref the evidence is about.
2. `durable_carrier` — retrievable PR/commit/artifact coordinate for the lane.
3. `terminal_state` — one exact lifecycle state.
4. `next_gate` — the declared next decision boundary.
5. `production_consumer` — the intended production integration target.

Rows also have an exact `id` and optional `composes` lane ids. `composes` means this lane includes or depends on those factor lines.

Example:

```json
{
  "version": 1,
  "lanes": [
    {
      "id": "h3c",
      "canonical_parent": "titan/v3.1-20260911@720c125c...",
      "durable_carrier": "pr:12555@<head>",
      "terminal_state": "PASSED",
      "next_gate": "literal-final-artifact paired gate",
      "production_consumer": "v3.1-final",
      "composes": []
    },
    {
      "id": "final-stack",
      "canonical_parent": "titan/v3.1-20260911@720c125c...",
      "durable_carrier": "artifact:<sha256>",
      "terminal_state": "BLOCKED",
      "next_gate": "close remaining source blocker",
      "production_consumer": "kaggle-submit",
      "composes": ["h3c"]
    }
  ]
}
```

Run:

```bash
python host/lane_registry.py path/to/lanes.json --pretty
python host/lane_registry.py path/to/lanes.json --lane final-stack --pretty
```

## Rejection propagation

`REJECTED` is contagious along composition edges. If lane `A` is `REJECTED` and lane `B` composes `A`, `B.effective_state` becomes `REJECTED_UPSTREAM`. That propagation is transitive. `rejected_by` lists the sorted rejected root lane ids so a consumer can see which factor poisoned the composed line.

A sibling that does not depend on the rejected lane is unchanged. A lane explicitly declared `REJECTED` remains `REJECTED`, even if it also composes another rejected lane.

The registry rejects unknown composition ids, duplicate ids/edges, self-composition, and cycles before computing effective state.

## Exact states

Accepted `terminal_state` values are:

```text
NOT_EXECUTED
RUNNING
BLOCKED
PASSED
REJECTED
SHIPPED
SUPERSEDED
```

The loader also rejects unknown row fields, missing factor fields, non-string factor values, non-integer/unsupported versions, and non-JSON input. This keeps the registry a small coordination contract rather than a prose bucket.

`test_lane_registry.py` covers required fields, strict types, graph validity, deterministic rendering, and direct/transitive rejection propagation without network or runner dependencies.
