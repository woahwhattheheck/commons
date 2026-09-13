# Swarm pre-claim multikey custody fence

`tools.swarm_preclaim_fence` is a small **read-only** decision fence for a
problem that repeatedly caused duplicate work in the swarm: one lookup key
(e.g. a stable operation ID) can be empty while the same work is already owned
under an upstream PR number, a changed path, an owner-fork PR, or bytes that
have already landed on the owner default branch.

It never claims work and never talks to a mutation endpoint. It consumes a
bounded request plus **connector-captured read-only evidence** and emits one of:

- `SAFE_TO_BIND_BRANCH`
- `OWNED`
- `ALREADY_ABSORBED`
- `NEEDS_MANUAL_DIFF`

Only `SAFE_TO_BIND_BRANCH` exits the CLI with status `0`. Every other decision
exits `3`; malformed or incomplete input exits/fails closed.

## Why connector-captured evidence?

The ChatGPT Slack/GitHub connector credentials used by swarm workers are not
repository credentials and must not be copied into scripts. Acquisition stays
outside this package. A worker performs the read-only searches/GETs with its
authorized connector and normalizes only minimal metadata into the evidence
document. Raw Slack message bodies are deliberately rejected.

The required request fields are:

```json
{
  "owner_fork": "woahwhattheheck/tarsnap",
  "upstream_pr_or_issue": "Tarsnap/tarsnap#836",
  "stable_id": "TARSNAP-836-FOO",
  "candidate_paths": ["lib/foo.c", "tests/foo_test.sh"],
  "semantic_phrases": ["foo resync"]
}
```

`stable_id`, `candidate_paths`, and `semantic_phrases` may be omitted/empty.
The evidence document must have complete slices for every requested search:

- Slack stable-ID hits (when a stable ID exists);
- Slack exact `owner/repo#N` hits;
- Slack candidate-path and semantic-phrase hits;
- matching open PRs on the owner fork;
- per-candidate-path owner-default/upstream-base/upstream-head blob SHAs.

A hit contains metadata only (`id`, optional URL/channel/timestamp/kind/repo/
number/overlap paths). Do not paste Slack message text into the receipt.

## Path states

For each candidate path the evaluator emits exactly one state:

- `MISSING` — path is absent on the owner default branch;
- `EXACT_BASE` — owner default has the upstream base blob;
- `EXACT_HEAD` — owner default already has the upstream head blob;
- `DIVERGED` — owner default is neither the candidate base nor head.

Decision precedence is intentionally conservative:

1. any incomplete evidence => `NEEDS_MANUAL_DIFF`;
2. all candidate paths `EXACT_HEAD` => `ALREADY_ABSORBED`;
3. any Slack/open-owner-PR custody hit => `OWNED`;
4. any `DIVERGED`, or partial `EXACT_HEAD` absorption => `NEEDS_MANUAL_DIFF`;
5. otherwise => `SAFE_TO_BIND_BRANCH`.

This pins the three acceptance cases that motivated the tool:

- stable-ID empty + exact upstream PR-number custody hit => `OWNED`;
- still-open upstream PR + exact candidate head already on owner default =>
  `ALREADY_ABSORBED`;
- any divergent candidate path => no automatic transplant,
  `NEEDS_MANUAL_DIFF`.

## CLI

```bash
python -m tools.swarm_preclaim_fence.preclaim \
  --request request.json \
  --evidence evidence.json \
  --pretty
```

The JSON receipt is deterministic and includes `receipt_sha256`.
`mutations_performed` is always an empty list.

## Verification

```bash
python -m unittest -v tools.swarm_preclaim_fence.tests.test_preclaim
python -O -m unittest -v tools.swarm_preclaim_fence.tests.test_preclaim
python -m py_compile \
  tools/swarm_preclaim_fence/preclaim.py \
  tools/swarm_preclaim_fence/tests/test_preclaim.py
```
