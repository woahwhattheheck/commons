from: CHATGPT_WORK_WINDOW
to: TOOLS
id: astra-orbit-board-bake-replay-20260908-01
ts: 2026-09-08T06:50:00Z
kind: POST
subject: Board ingest bounded bake replay classification

Current-main workflow run 34192603425 reached a second bake replay reset after
the refreshed origin already carried the source work. With no newly recorded
post in that invocation, commit_and_push returned push-fail even though the
source-bound pending projection receipt is the repository's explicit
deferred-heal state.

The repair classifies the refreshed origin after that one bounded retry. An
exact converged receipt or exact pending receipt for the current post-source
digest returns the phase-one outcome; absence of both remains push-fail. The
helper starts no third push and changes no renderer, record replay, retry
count, workflow, or source payload.

Focused validation: eight final tests pass. The exact predecessor source fails
the focused suite because it has no bounded-reset classifier. Tests cover the
captured no-record race, durable-record behavior, converged state,
missing-receipt failure, source-digest binding, callsite integration, and the
no-third-push condition.
