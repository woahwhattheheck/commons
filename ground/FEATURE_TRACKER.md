# Feature tracker

First-class shipped-state tracker for Commons. It shows at a glance what is actually built, live, tested, degraded, superseded, or only planned.

**Do not remint [features.html](../features.html).** That door is the FEATURES board lane. Cite [ground/FEATURES.md](./FEATURES.md). This tracker is a different object:

- human: [feature-tracker.html](../feature-tracker.html)
- machine: [feature-tracker.json](../feature-tracker.json)
- instrument: [host/feature_tracker.py](../host/feature_tracker.py)
- proof: [test_feature_tracker.py](../test_feature_tracker.py)
- registry: [features/registry/](../features/registry/)
- evidence: [features/evidence/](../features/evidence/)

## Evidence law

Status is derived. Author prose, chat, Slack, ntfy 200, an open PR, a Pages card, and a `claimed_status` field never promote a feature.

- **PLANNED** — registry row, no claimed source paths.
- **SOURCE_BUILT** — every `claimed_paths` entry exists on the measured tree or cited 40-character SHA.
- **TESTED** — SOURCE_BUILT plus every `test_paths` entry exists. Existence is the proof this instrument can see; a green CI run is extra evidence, not a substitute for the files.
- **LIVE** — SOURCE_BUILT plus a `LIVE_MEASUREMENT` evidence row with a public URL and a 40-character SHA. HTTP is a bake. Listing `public_entrypoint` only proves a source door. A cited `blob` that no longer matches the measured tree is stale; append a new row, never overwrite.
- **DEGRADED** — claimed paths, tests, or a live measurement that no longer hold. Stale-only LIVE (cited blob moved, no current pin) is DEGRADED.
- **SUPERSEDED** — a `SUPERSEDE` evidence row (or `superseded_by`) names the replacement. History stays.

Source-built and live stay separate columns. Never collapse them.

## Append-only

- New feature: add `features/registry/{id}.json`. Filename equals `{id}.json`.
- New evidence: add `features/evidence/{id}.json`. Do not edit a prior evidence file.
- Same id + identical bytes is idempotent.
- Same id + different bytes is `CONFLICT`. Never overwrite. Add evidence or mint a new id.
- Projection never mutates registry or evidence files.
- Compatible concurrent work merges by default: different feature ids are different files. Only same-id semantic disagreement conflicts.

## Add a shipped feature (every carrier)

1. Mint `id` matching `^[A-Za-z0-9._-]{8,80}$`.
2. Write one new registry file. Fill name, capability, owning subsystem, carrier, claimed_paths, test_paths, public_entrypoint, dependencies, resource_links, next_gap.
3. Optionally write evidence: SOURCE_PATHS, TEST_PATHS, GIT_SHA, BLOB, LIVE_MEASUREMENT, RECEIPT, SUPERSEDE.
4. `python3 host/feature_tracker.py --write`
5. `python3 test_feature_tracker.py`
6. Unique branch from current main. Merge, not force. Read back the paths on the official 40-character SHA. File `p/{id}.md`.

No auth. No secrets. No generated-history rewrite. No fabricated LIVE.

## Not this tracker

- `features.html` — FEATURES lane
- `current-work.html` — unfinished now
- `todo.html` — DIRECTIVES view
- `builds.html` — permit SOP
- `ledger.html` — resource census
- `right-now.html` — buyer desk
- `ground/PROFITABILITY_BUILD_MAP.md` — execution map; this tracker links it, it does not replace it
