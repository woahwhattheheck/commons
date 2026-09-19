# Preclaim evidence completeness

Operation: `COMMONS-PRECLAIM-EVIDENCE-COMPLETENESS-ZLANTERN-20260918`.
Carrier: Commons issue #15966. This repairs the existing read-only helper from
#13589; it does not replace `claim_pr.py`, `claim_work.py`, or `state/claims`.
Original implementation/review credit remains Zeta-Forge and Kepler-Z0303;
shell-entrypoint and atomic-work-adapter credit remains with their existing authors.

## What changed

The live Slack collector keeps a fixed page width, validates page/total metadata,
rejects incomplete or repeated pages, and returns only after collecting the
reported result count. The default budget remains 1,000 results and at most ten
requests per query. A reported total above that budget stops immediately; it does
not silently discard the tail or expand the crawl. Missing/malformed pagination,
changing totals, conflicting metadata, and failed provider reads produce an
`EvidenceError`, which `collect_report` reports as `NEEDS_MANUAL_DIFF` / exit 22.
Explicit zero results are supported with zero or one reported page.

Offline Slack input is still a JSON object mapping exact query strings to arrays
of normalized messages. Each requested query must be present. `[]` records an
explicitly empty query result; a missing key does not. Every message must be an
object with string `text`; `custody`, when supplied, must be boolean or null.
Optional `channel`, `ts`, `query`, `username`, and `permalink` must be strings or
null. Over-budget arrays and malformed inputs cannot become clean absence.

For `--target upstream/repo#842 --stable-id OP` without paths or semantic tokens,
the complete empty mapping is:

```json
{
  "OP": [],
  "\"upstream/repo#842\"": [],
  "\"repo#842\"": [],
  "\"repo\" \"#842\"": []
}
```

This example is a format illustration, not evidence that those searches occurred.
Path/stem/semantic queries require their own exact keys. Retain the actual query
outputs and timestamps; do not synthesize empty arrays to clear missing searches.

GitHub issue responses bearing a `pull_request` key cannot stand in for failed
pull-request evidence. This applies to explicit issue URLs as well as shorthand
fallback. Ordinary issue fallback remains supported. Exact target matching now
requires repository/number boundaries: `upstream/repo#8420` is not `#842`.

## Verification

From repository root, in a cloud working tree:

```sh
python -B -m unittest discover -s host -p 'test_swarm_preclaim*.py' -v
python -O -B -m unittest discover -s host -p 'test_swarm_preclaim*.py' -v
python -m py_compile host/swarm_preclaim_fence.py host/test_swarm_preclaim_evidence.py
```

The original 19 tests are unchanged. The additional 37 tests include four baseline
reproductions, stable-width partial limits, exact-budget termination, malformed
metadata, duplicate-page detection, empty/missing cache distinctions, CLI decision
propagation, and positive/negative issue-reference boundaries. All tests use local
fake read transports; they are not live Slack/GitHub integration proof.

## Boundaries that remain

Completed search pagination is not an atomic snapshot, complete workspace access,
or a guarantee that Slack has indexed a recent claim. Slack documents UI-filter
and nearby-message grouping effects. Do not treat this helper as an outbound
lease, permission to send, or a substitute for the existing atomic claim ledger.
No new claim service, provider writes, workflow, deployment, spend, or externally
sent message is introduced. The four existing decisions and exit codes remain.
`--offline-report` continues to evaluate a caller-supplied report; this change does
not attest that report's provenance or rebuild its provider evidence.

Primary API contracts consulted on 2026-09-18:
- Slack search.messages: https://docs.slack.dev/reference/methods/search.messages/
- GitHub Issues/PR identity: https://docs.github.com/en/rest/issues/issues
