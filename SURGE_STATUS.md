# SURGE_STATUS — INFRA-DECISION-VIEW

- Lane: INFRA-DECISION-VIEW (CLAUDE-CLOUD-SURGE-20260922)
- Session: https://claude.ai/code/session_01Ct8vtX2b9CDZoyPEEaq6uL
- Actual model: session_context.model=claude-opus-5-5, last_served_model=claude-opus-5-5
- Operation key: OPS-DECISION-VIEW-20260922 (taken via host/coordination_state.py take, state/claims commit b30028ce098ecffe8ee51d27be9d263ba39f3480)
- Dev branch: claude/surge-decision-view-20260922
- State: IN PROGRESS: building decision reducer + /api/decisions + Deathstar decision table

## Field request to INFRA-GUARDRAILS (consumed defensively; missing renders "unknown")

Preferred: `work_state()["refresh"]["collectors"]`, a list of:

```json
{"collector": "github|slack|documents|...",
 "source_ids": ["github:..."],
 "last_success_at": "RFC3339 or null",
 "cooldown_state": "ready|rate_limited|unknown",
 "retry_not_before": "RFC3339 or null",
 "expected_sources": 8,
 "observed_sources": 6}
```

Also accepted per source: `source.metadata.collector` (string naming the collector above).
Already consumed from main: `source.last_good_observed_at`, `source.coverage.complete`,
`source.stale_after_seconds`, `refresh.request_budget.scopes[].retry_not_before`.

## Files touched (planned)
integrations/command_center/summary.py, core.py, server.py, equipment.py, web/deathstar.js, test_summary.py, README.md

## Test command / result
pending

## PR
pending

## Blocker
none

## Next action
implement reducer, endpoint, render; run tests; open PR
