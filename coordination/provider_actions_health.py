from __future__ import annotations
import json
from datetime import datetime, timezone

INPUT_SCHEMA = "commons.provider-actions-health-evidence/v1"
OUTPUT_SCHEMA = "commons.provider-actions-health-report/v1"

class ProviderActionsHealthError(ValueError):
    pass

def _utc(value):
    if type(value) is not str or not value.endswith("Z"):
        raise ProviderActionsHealthError("timestamp must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ProviderActionsHealthError("timestamp must be canonical UTC") from exc
    if parsed.tzinfo != timezone.utc or parsed.microsecond:
        raise ProviderActionsHealthError("timestamp must be canonical UTC")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ProviderActionsHealthError("timestamp must be canonical UTC")
    return int(parsed.timestamp())

def classify_repository(repo, cutoff_at):
    if type(repo) is not dict:
        raise ProviderActionsHealthError("repository evidence must be object")
    if repo.get("provider_state") == "DISABLED":
        return "PROVEN_DISABLED"
    if repo.get("workflow_present") is False:
        return "NO_WORKFLOW"
    latest = repo.get("latest_run_at")
    eligible = repo.get("eligible_event_at")
    if eligible is not None and (latest is None or _utc(latest) < _utc(eligible)):
        return "SUSPICIOUS_EVENT_SUPPRESSION"
    if latest is not None and _utc(latest) >= _utc(cutoff_at):
        return "HEALTHY_PROVIDER_SEEN"
    if repo.get("eligible_event_kind") == "NONE":
        return "DORMANT_OR_NO_ELIGIBLE_EVENT"
    return "UNKNOWN_EVIDENCE"

def compile_health(packet):
    if type(packet) is not dict or packet.get("schema") != INPUT_SCHEMA:
        raise ProviderActionsHealthError("unsupported packet")
    cutoff = packet.get("cutoff_at")
    _utc(cutoff)
    repos = packet.get("repositories")
    if type(repos) is not list or not repos:
        raise ProviderActionsHealthError("repositories required")
    names = [r.get("repository") for r in repos]
    if any(type(n) is not str or not n for n in names) or len(names) != len(set(names)):
        raise ProviderActionsHealthError("repository names invalid or duplicate")
    rows = []
    for repo in sorted(repos, key=lambda r: r["repository"].casefold()):
        row = dict(repo)
        row["state"] = classify_repository(repo, cutoff)
        row["disabled_inferred_from_silence"] = False
        rows.append(row)
    return {
        "schema": OUTPUT_SCHEMA,
        "cutoff_at": cutoff,
        "observed_at": packet.get("observed_at"),
        "repositories": rows,
        "invariants": {
            "silence_proves_disabled": False,
            "unknown_provider_state_is_disabled": False,
        },
    }

def render_markdown(report):
    lines = ["# Provider Actions health", "", "| Repository | State | Latest run | Eligible event |", "| --- | --- | --- | --- |"]
    for row in report["repositories"]:
        lines.append(f"| `{row['repository']}` | **{row['state']}** | {row.get('latest_run_at') or 'none'} | {row.get('eligible_event_kind') or 'UNKNOWN'} |")
    lines += ["", "Workflow silence alone never proves Actions is disabled.", ""]
    return "\n".join(lines)
