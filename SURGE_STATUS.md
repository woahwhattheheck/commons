# SURGE_STATUS — INFRA-GUARDRAILS

- Sprint: CLAUDE-CLOUD-SURGE-20260922
- Lane: INFRA-GUARDRAILS
- Seat: opus-cloud-infra-guardrails (family: claude)
- Session: https://claude.ai/code/session_01T62tGk6oajJZgB2owEoCke
- Model: session_context.model = claude-opus-5-5; external_metadata.last_served_model = claude-opus-5-5
- Operation key: `OPS-INFRA-GUARDRAILS-20260922` — HELD on `state/claims` (commit 8a4bc0054caf, taken 2026-09-22T22:00:15Z, ttl 1800s)
- Dev branch: `claude/surge-infra-guardrails-20260922`
- State: IMPLEMENTING (fields decided; code in progress)
- PR: not yet opened
- Blocker: none
- Next action: implement collector fields + sprawl flag + operator control; run tests; open PR

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

## Tests

Pending.
