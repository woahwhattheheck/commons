# Proposal compliance gate

A buyer-neutral, stdlib-only gate for turning an RFP requirement register into a deterministic submission-readiness check.

It exists to prevent a common failure mode in proposal work: polished prose silently substituting for evidence. Requirements can be marked `mandatory`, `scored`, or `informational`; evidence is tracked as `available`, `pending`, `missing`, or `not_applicable`; and owner/authorized-human decisions can be hard-gated so an automated workflow cannot certify its own signature, financial statements, references, insurance, or other human-controlled facts.

## Usage

```bash
python tools/proposal_gate/proposal_gate.py requirements.json evidence.json \
  --markdown-out compliance.md \
  --json-out compliance.json \
  --skeleton-out response.md \
  --draft-out draft.md \
  --check
```

`--check` exits `2` when a mandatory blocker or owner gate remains. A scored weakness is reported as `AT_RISK` but does not by itself make the packet formally incomplete.

Minimal requirement:

```json
{
  "requirements": [
    {
      "id": "A-1",
      "section": "Architecture",
      "type": "mandatory",
      "statement": "Describe scalability",
      "evidence": ["architecture-note"],
      "response": "Horizontal workers with bounded queues."
    }
  ]
}
```

Minimal evidence inventory:

```json
{
  "evidence": [
    {"id": "architecture-note", "status": "available"}
  ]
}
```

## Safety properties

- Missing or pending mandatory evidence blocks submission readiness.
- `[TBD]`, `TODO`, and insert-style placeholders do not count as responses.
- `owner_gate: true` blocks submission even if an artifact is present.
- Requirement IDs and evidence IDs are validated for uniqueness and status vocabulary.
- Output is human-readable Markdown plus machine-readable JSON, and can render both a blank response skeleton and the current evidence-backed draft.
- Buyer-specific requirements stay runtime data; the engine itself contains no procurement-confidential content.

## Tests

```bash
python -m unittest tools/proposal_gate/test_proposal_gate.py -v
```
