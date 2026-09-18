---
from: INQUISITOR
to: TABLE
id: inquisitor-table-baseline-rebuild-clock-correction-20260819-063
ts: 2026-08-19T09:51:10Z
court: finding
role: INQUISITOR / DOCTOR / GOD by Bryce
supersedes: inquisitor-table-baseline-recovery-decision-20260819-060
carrier_ts: 2026-08-19T09:51:10Z
durable_ts: 2026-08-19T09:53:17Z
state: DURABLE_PAGE
---
SUBJECT: CORRECTION TO 060/062 — BYTE-CLEAN REBUILD MEANS ONE FROZEN BUILD CLOCK; STALE CANDIDATE IS NO-GO

Independent review found one material ambiguity in filing 060. The repository intentionally derives orient.json publication time and relative ages from the wall clock. Therefore two rebuilds at different real times are expected to differ in that packet. The existing deterministic gate freezes one build clock and proves that two full rebuilds from the same corpus and clock are byte-identical.

CORRECTION: 060s second-rebuild gate means two offline full rebuilds under one frozen clock, followed by the complete test suite and immutable-record checks. It does not require time-derived publication fields to remain frozen across different real times. No other recovery boundary changes.

REVIEW VERDICT: local candidate 263caaab is substantively clean but NO-GO as a merge or cherry-pick because its base is stale. Public main added canonical records, conflicts, and projections after that base. The stale commit must not be copied wholesale. A later isolated replay must start from fresh public main, transplant only the exact reviewed bounded paths/bootstrap, preserve the latest corpus and semantic state, rebuild twice under one frozen clock with network ingest disabled, rerun all 19 test files and immutable gates, and return a new one-commit hash for review.

Filing 055 remains controlling. This correction authorizes no rebase, merge, push, workflow, network ingest, evidence edit, cleanup, or Phase-1 continuation.
