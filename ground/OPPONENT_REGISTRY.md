# Opponent + causal-witness registry

`host/opponent_registry.py` implements visibility-plan D6. Opponent identity is content identity: the registry is keyed by exact lowercase SHA-256 digests rather than display names, mutable URLs, or score labels.

Each opponent digest has exactly:

```json
{
  "name": "Shop Router 0908",
  "source": "artifact:opponent-script"
}
```

Causal witnesses bind to one registered digest and require these fields:

```text
id
opponent_digest
canonical_parent
intervention
observable
outcome
evidence
```

`observable` is mandatory and non-empty. A causal-witness row therefore cannot be recorded as only an internal explanation such as “policy became better”; it has to name the state/action/measurement that was actually observable in the cited evidence.

Example:

```json
{
  "version": 1,
  "opponents": {
    "1111111111111111111111111111111111111111111111111111111111111111": {
      "name": "example opponent",
      "source": "artifact:<sha256>"
    }
  },
  "witnesses": [
    {
      "id": "w-opening-workers",
      "opponent_digest": "1111111111111111111111111111111111111111111111111111111111111111",
      "canonical_parent": "titan/v3.1-20260911@<sha>",
      "intervention": "enable candidate factor only",
      "observable": "worker count at the opening day-2 checkpoint",
      "outcome": "paired margin delta +12.5",
      "evidence": "artifact:<receipt-sha256>"
    }
  ]
}
```

Run:

```bash
python host/opponent_registry.py opponents.json --pretty
python host/opponent_registry.py opponents.json --opponent <sha256> --pretty
python host/opponent_registry.py opponents.json --witness w-opening-workers --pretty
```

The loader rejects malformed/non-lowercase digests, unknown opponent references, duplicate witness ids, missing/empty observable fields, unknown row fields, unsupported versions and non-JSON input. Output is deterministic: opponents sort by digest and witnesses by id, with aggregate witness counts per opponent digest.

`test_opponent_registry.py` covers exact digest identity, unknown-opponent rejection, mandatory observable custody, exact metadata/witness shapes, duplicate witness ids, deterministic ordering/counts and strict version typing without network or runner dependencies.
