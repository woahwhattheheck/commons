#!/usr/bin/env python3
"""Internal-only WRF 5417 manifest checker. No network or submission actions."""
from __future__ import annotations
import datetime as dt
import json
import math
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

READY = "READY_FOR_AUTHORIZED_SUBMITTER_REVIEW"
ALLOWED = {"PROVEN", "PARTNER_CURABLE", "MISSING", "NOT_APPLICABLE", "HOLD"}


def evidence(entry):
    refs = entry.get("evidence", []) if isinstance(entry, dict) else []
    return isinstance(refs, list) and bool(refs) and all(isinstance(x, str) and x.strip() for x in refs)


def require_proven(name, entry, reasons):
    status = entry.get("status") if isinstance(entry, dict) else None
    if status not in ALLOWED:
        reasons.append(f"{name}: invalid status")
    elif status != "PROVEN":
        reasons.append(f"{name}: {status}")
    elif not evidence(entry):
        reasons.append(f"{name}: proven without evidence")


def check(manifest, now=None):
    reasons = []
    if manifest.get("opportunity_id") != "WRF-5417":
        reasons.append("wrong opportunity_id")

    intended = manifest.get("intended_submission_state")
    if intended not in {"HOLD", READY}:
        reasons.append("invalid intended_submission_state")
    elif intended == "HOLD":
        reasons.append("owner intent remains HOLD")

    deadline = manifest.get("deadline", {})
    try:
        wall = dt.datetime.fromisoformat(deadline["local"])
        if wall.tzinfo is not None:
            raise ValueError("deadline.local must be offset-free wall time")
        due = wall.replace(tzinfo=ZoneInfo(deadline["iana_zone"]))
    except Exception as exc:
        reasons.append(f"invalid deadline: {exc}"); due = None
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if due and now.astimezone(dt.timezone.utc) >= due.astimezone(dt.timezone.utc):
        reasons.append("deadline expired")
    require_proven("live_deadline_recheck", deadline.get("deadline_offset_recheck", {}), reasons)

    gates = manifest.get("hard_gates", {})
    if not gates:
        reasons.append("hard gates missing")
    for name, entry in sorted(gates.items()):
        require_proven(name, entry, reasons)

    budget = manifest.get("budget", {})
    req = budget.get("wrf_request_usd")
    contrib = budget.get("documented_eligible_contribution_usd")
    if not isinstance(req, (int, float)) or isinstance(req, bool) or not math.isfinite(req) or not (0 < req <= 300000):
        reasons.append("valid WRF request amount not set")
    if budget.get("minimum_contribution_fraction") != 0.33:
        reasons.append("cost-share fraction must be 0.33")
    if not isinstance(contrib, (int, float)) or isinstance(contrib, bool) or not math.isfinite(contrib) or contrib < 0:
        reasons.append("documented eligible contribution not set")
    if isinstance(req, (int, float)) and not isinstance(req, bool) and isinstance(contrib, (int, float)) and not isinstance(contrib, bool):
        required = round(req * 0.33, 2)
        if contrib + 1e-9 < required:
            reasons.append(f"contribution below required {required:.2f}")
    require_proven("budget_workbook", budget.get("budget_workbook", {}), reasons)
    require_proven("budget_narrative", budget.get("budget_narrative", {}), reasons)

    participants = manifest.get("utility_participants", [])
    sectors = set()
    if not participants:
        reasons.append("no utility participants")
    for idx, p in enumerate(participants):
        if not isinstance(p, dict) or p.get("consent_status") != "PROVEN" or not evidence({"evidence": p.get("consent_evidence", [])}):
            reasons.append(f"utility {idx}: consent not proven")
            continue
        sector = p.get("sector")
        if sector not in {"drinking_water", "wastewater", "both"}:
            reasons.append(f"utility {idx}: invalid sector")
        else:
            sectors.add(sector)
    if not (sectors & {"drinking_water", "both"}) or not (sectors & {"wastewater", "both"}):
        reasons.append("proven utilities do not span both sectors")

    authority = manifest.get("submission_authority", {})
    if authority.get("carrier_may_submit") is not False:
        reasons.append("carrier_may_submit must remain false")
    if intended == READY and reasons:
        reasons.insert(0, "READY spoofed while blockers remain")
    return (READY if not reasons else "HOLD"), reasons


def main():
    if len(sys.argv) != 2:
        print("usage: validate_readiness.py MANIFEST.json", file=sys.stderr); return 2
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    state, reasons = check(data)
    print(json.dumps({"state": state, "reasons": reasons}, indent=2))
    return 0 if state == READY else 3


if __name__ == "__main__":
    raise SystemExit(main())
