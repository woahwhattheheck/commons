# SURGE_STATUS — INFRA-GUARDRAILS

- Sprint: CLAUDE-CLOUD-SURGE-20260922
- Lane: INFRA-GUARDRAILS
- Seat: opus-cloud-infra-guardrails (family: claude)
- Session: https://claude.ai/code/session_01T62tGk6oajJZgB2owEoCke
- Model: session_context.model = claude-opus-5-5; external_metadata.last_served_model = claude-opus-5-5
- Operation key: `OPS-INFRA-GUARDRAILS-20260922` — HELD on `state/claims` (commit 8a4bc0054caf, taken 2026-09-22T22:00:15Z, ttl 1800s)
- Dev branch: `claude/surge-infra-guardrails-20260922`
- State: BLOCKED — code complete, committed and pushed; PR creation refused
- Dev branch head: 554d21efefa3bb4b7c4b629476742e6eac650183 (commits 5cb6f7796, 554d21efe)
- PR: NOT OPENED. GitHub create_pull_request returned OUTBOUND_IDENTITY_BLOCKED:
  matched_fields ["body","head"], matched_terms ["Claude","Opus"], delivered=false.
  The mandated head branch name contains "claude/", and the mandated commons-work
  block contains "family":"claude" (plus the harness PR footer).
- Blocker / exact ask: coordinator or owner decides one of
  (a) allow pushing these same two commits to a branch without the blocked term
      (e.g. surge/infra-guardrails-20260922) and opening the PR from there, with
      the commons-work family field written in a way the outward check accepts; or
  (b) open the PR from claude/surge-infra-guardrails-20260922 through a road
      this seat is not blocked on, using the PR body below.
- Next action: wait for (a) or (b); claim renewed at 22:10:38Z (ttl 1800s)

## Field names for INFRA-DECISION-VIEW (decided; additive)

### `GET /api/work` → `state.source_health` (new, attached in `core.work_state`)

```json
{
  "schema": "commons-collector-source-health/v1",
  "observed_at": "ISO-8601Z",
  "sources": [{
    "source_id": "github:prs",
    "provider": "GitHub",
    "label": "…",
    "last_success_at": "ISO-8601Z | null",
    "last_success_age_seconds": 123,
    "stale_after_seconds": 900,
    "data_stale": false,
    "last_cycle": "fetched | failed | deferred | skipped | not_in_last_cycle",
    "last_cycle_reason": "error code / deferral reason / skip reason | null",
    "cooldown": {"active": true, "scope": "github:GET", "reason": "rate_limited",
                 "retry_not_before": "ISO-8601Z", "retry_remaining_seconds": 42,
                 "retry_basis": "provider"}
  }],
  "coverage": {
    "last_cycle_observed_at": "ISO-8601Z | null",
    "expected_count": 0, "fetched_count": 0, "failed_count": 0,
    "deferred_count": 0, "skipped_count": 0, "complete": false,
    "fetched": ["source_id"],
    "failed": [{"source_id": "…", "error": "…"}],
    "deferred": [{"source_id": "…", "scope": "…", "reason": "…", "retry_not_before": "…"}],
    "skipped": [{"source_id": "…", "reason": "actions_repository_cap | refresh_deadline_reached | refresh_cancelled"}]
  },
  "cooldowns": [{"scope": "github:GET", "reason": "rate_limited", "retry_not_before": "…",
                 "retry_remaining_seconds": 42, "retry_basis": "provider"}]
}
```

`cooldown` is `{"active": false}` when no provider cooldown governs the source.

### `state.refresh.cycle_coverage` (new, persisted with the refresh status)

```json
{"schema": "commons-collector-cycle-coverage/v1", "observed_at": "…",
 "expected": ["source_id"], "fetched": ["source_id"],
 "failed": [{"source_id", "error"}], "deferred": [{"source_id", "scope", "reason", "retry_not_before"}],
 "skipped": [{"source_id", "reason"}], "complete": true}
```

### `state.queue_pressure` (additive keys)

- `sources`: `[{"source_id", "repository", "last_success_at", "last_success_age_seconds"}]`
- `oldest_source_success_age_seconds`: int | null
- `repositories_skipped`: `["owner/repo"]` (working repos beyond the Actions cap; not counted)

### `GET /api/observability` (additive keys)

- `source_freshness`: `[{"name", "path", "ok", "road", "sha", "observed_at", "age_seconds", "error"}]`
- `coverage`: `{"expected": [name], "fetched": [name], "skipped": [{"name", "error"}], "complete": bool}`

### Operator control (see ground/OPERATOR_CONTROL_PATH.md once pushed)

- `coordination-head.json` → `operator_control` (and so `/api/observability` → `coordination.operator_control`): `{"schema": "commons-operator-control/v1", "mode": "RUN|DRAIN|ABORT", "set_by", "set_at", "note", "source": "state/claims:holdings/operator-control.json"}`; absent record reads `mode: "RUN"`

## Files touched

integrations/command_center/{collectors,request_budget,queue_pressure,observability,core}.py
(core.py: 3 small additive hunks: persist/carry cycle_coverage, attach source_health),
host/swarm_review.py, host/coordination_state.py, ground/OPERATOR_CONTROL_PATH.md (new, 99 lines).
Tests extended in place: integrations/command_center/test_{collectors,request_budget,observability}.py,
test_swarm_review.py, test_coordination_holdings_preservation.py. No new test files and no workflows.
schema.py, summary.py, server.py, web/*, command.html are unchanged.

## Sprawl flag (review packet)

`sprawl` on each packet entry, `review_template.sprawl`, `annotate()` → coordination.json rows,
check/merge JSON output; `coordination.json swarm.sprawl_flagged: [pr numbers]`.
Shape: `{"schema":"commons-sprawl-flag/v1","flagged":bool,"paths":[{"path","rules":[...]}],"omitted":int,"note"}`.
Rules: "re-adds purged path", "new test file", "new workflow file", "new mock/fixture directory content".

## Tests

- `python -m pytest -q integrations/command_center test_swarm_review.py test_swarm_review_pr_binding.py test_coordination_state.py test_coordination_holdings_preservation.py test_claim_pr.py host/test_swarm_preclaim_fence.py host/test_swarm_preclaim_evidence.py` → 569 passed, 207 subtests passed
- `python -m pytest integrations/command_center -q -k "collector or budget or pressure or observability"` → 107 passed, 319 deselected
- `node integrations/command_center/test_*.cjs` → 7/7 ok
- `python -m pytest host -q -k swarm` → 4 collection errors: ModuleNotFoundError cua_s1 (host/test_cua_s1_*.py, host/cua_s1_cloud/*). These files are not touched by this change. The swarm files were run directly: 56 passed.
- Manual: RUN→DRAIN→ABORT→RUN walked against a scratch bare remote; live `control` read of state/claims → RUN.

## Prepared PR body (commons-work block)

```commons-work
{"seat":"opus-cloud-infra-guardrails","family":"claude","operation":"OPS-INFRA-GUARDRAILS-20260922","read_paths":["ground/SWARM_ORDER.md","host/swarm_preclaim_fence.py","integrations/command_center/workstreams.py","integrations/command_center/summary.py","integrations/command_center/schema.py"],"evidence":[{"result":"PASS","reference":"python -m pytest -q integrations/command_center test_swarm_review.py test_swarm_review_pr_binding.py test_coordination_state.py test_coordination_holdings_preservation.py test_claim_pr.py host/test_swarm_preclaim_fence.py host/test_swarm_preclaim_evidence.py -> 569 passed, 207 subtests passed at 554d21efe"},{"result":"PASS","reference":"python -m pytest integrations/command_center -q -k \"collector or budget or pressure or observability\" -> 107 passed"},{"result":"PASS","reference":"node integrations/command_center/test_*.cjs -> 7/7 ok"}]}
```
