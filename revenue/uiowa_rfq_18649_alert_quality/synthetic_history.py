#!/usr/bin/env python3
"""Produce the fictional UIOWA-066 rehearsal packet; no live University records."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


def packet() -> dict[str, Any]:
    def time(hm: str, day: str = "18") -> str:
        return f"2026-09-{day}T{hm}:00Z"

    incidents: list[dict[str, Any]] = []
    sources = [{"id": "COVERAGE", "locator": "synthetic_history.py#coverage",
                "excerpt": "FICTIONAL evidence export for 2026-09-18 08:00Z to 12:00Z. Notification rows include one exact export duplicate and one boundary row. Lifecycle records are complete for the selected records except I2. This is a convenience sample, not a census of all service incidents."}]

    def incident(iid: str, group: str, service: str, detected: str, ack: str | None,
                 response: str | None, resolved: str | None, *, owner: str = "owned",
                 actionable: str = "actionable", runbook: str = "useful",
                 escalation: tuple[str, str | None, str | None] = ("no", None, None),
                 coverage: str = "complete", narrative: str) -> None:
        sid = "EV-" + iid
        sources.append({"id": sid, "locator": "synthetic_history.py#" + iid,
                        "excerpt": "FICTIONAL: " + narrative})
        incidents.append({"id": iid, "group": group, "service": service,
            "detected_at": detected, "ack_at": ack, "resolved_at": resolved,
            "meaningful_response": {"at": response, "action": "Identified the relevant condition and performed the first recorded useful diagnostic or corrective step.", "source_refs": [sid]} if response else None,
            "owner_state": owner, "owner_role": group + " service operations" if owner == "owned" else None,
            "owner_source_refs": [sid] if owner != "unknown" else [],
            "actionability": actionable, "actionability_source_refs": [sid] if actionable != "unknown" else [],
            "runbook": {"ref": "fictional-runbook/" + service if runbook != "not_used" else None,
                        "use": runbook, "source_refs": [sid] if runbook != "unknown" else []},
            "escalation": {"required": escalation[0], "due_at": escalation[1], "at": escalation[2],
                           "source_refs": [sid] if escalation[0] != "unknown" else []},
            "lifecycle_coverage": coverage, "source_refs": [sid]})

    incident("E1", "ESS", "registration", time("08:00"), time("08:01"), time("08:05"), time("08:20"),
             narrative="Registration incident E1 started at 08:00Z. The team acknowledged at 08:01, used the dependency check successfully at 08:05, and restored at 08:20. Two repeats at 08:02 and 08:03 required 30 and 45 seconds of triage. No escalation was required. Routing ownership was checked in the exercise.")
    incident("E2", "ESS", "registration", time("11:00"), time("11:01"), time("11:04"), time("11:15"),
             narrative="A DIFFERENT registration incident E2 began at 11:00Z with the same rule and fingerprint as E1. It was acknowledged at 11:01, first useful action at 11:04, restored at 11:15. The runbook worked. No escalation was required.")
    incident("R1", "RIS", "research-submission", time("09:00"), time("09:01"), None, None,
             owner="unowned", actionable="nonactionable", runbook="not_used",
             escalation=("yes", time("09:10"), time("09:25")),
             narrative="Research queue warning R1 began at 09:00Z and was acknowledged at 09:01, but a reviewed route had no accountable owner. The selected condition did not identify an action in the exercise. No useful response or resolution occurred by noon. Escalation due at 09:10 reached a fallback route at 09:25. Its 09:25 notification is an intentional escalation, not a duplicate. One 09:02 repeat has unknown triage duration. No runbook was used.")
    incident("I1", "IAM", "sign-in", time("10:00"), time("10:00"), time("10:12"), time("10:25"),
             runbook="not_useful", escalation=("yes", time("10:05"), time("10:05")),
             narrative="Sign-in incident I1 was detected and acknowledged at 10:00Z. The owned route responded but the runbook used an obsolete diagnostic location. First useful action was at 10:12; restoration at 10:25. The fallback escalation occurred on its agreed 10:05 deadline. A repeat at 10:03 required 120 seconds of triage; an intentional escalation was sent at 10:05.")
    incident("I2", "IAM", "sign-in", time("10:30"), time("10:31"), None, None,
             owner="unknown", actionable="unknown", runbook="unknown", escalation=("unknown", None, None), coverage="partial",
             narrative="Sign-in record I2 began at 10:30Z, with an acknowledgement at 10:31. The export lacks action, routing and escalation detail. Runbook existence is known, but use was not observed. Missing useful-action and owner fields cannot establish inactivity or an unowned service.")
    incident("E3", "ESS", "registration", time("11:59"), None, time("12:04"), time("12:10"),
             runbook="not_used", escalation=("yes", time("12:05"), time("12:05")),
             narrative="Registration incident E3 began at 11:59Z. No acknowledgement or useful action occurred before the observation ended at noon. Follow-up records show first useful action at 12:04 and escalation at its 12:05 due time. These later events must not leak into the noon analysis. Restoration at 12:10 is outside the window.")
    incident("R0", "RIS", "research-submission", time("07:50"), time("07:51"), time("08:10"), time("08:30"),
             narrative="Carry-in research incident R0 began before the window at 07:50Z, acknowledged at 07:51, first useful action at 08:10 and restored at 08:30. A repeat at 08:01 required 20 seconds of triage. Its 20-minute response must not enter the new-detection cohort or be clipped to ten minutes.")
    incident("R2", "RIS", "research-submission", time("10:45"), time("10:46"), None, time("11:00"),
             actionable="unknown", runbook="unknown", escalation=("unknown", None, None),
             narrative="Research record R2 was detected at 10:45Z and acknowledged at 10:46; a reliable restoration record exists at 11:00. The first useful action was not recorded. This is an evidence gap, not a claim that nobody acted before restoration.")

    lookup = {x["id"]: x for x in incidents}
    notifications: list[dict[str, Any]] = []

    def notice(nid: str, iid: str | None, at: str, kind: str = "initial", triage: int | None = 10) -> None:
        inc = lookup[iid] if iid else {"group": "RIS", "service": "research-submission"}
        sid = "EV-" + iid if iid else "EV-UNLINKED"
        notifications.append({"id": nid, "incident_id": iid, "group": inc["group"],
            "service": inc["service"], "rule": "user-flow-degraded", "fingerprint": inc["service"] + ":flow",
            "at": at, "kind": kind, "triage_seconds": triage, "source_refs": [sid]})

    notice("N01", "E1", time("08:00"))
    notice("N02", "E1", time("08:02"), "repeat", 30)
    notice("N03", "E1", time("08:03"), "repeat", 45)
    notice("N04", "E2", time("11:00"))
    notice("N05", "R1", time("09:00"))
    notice("N06", "R1", time("09:02"), "repeat", None)
    notice("N07", "R1", time("09:25"), "escalation", 25)
    notice("N08", "I1", time("10:00"))
    notice("N09", "I1", time("10:03"), "repeat", 120)
    notice("N10", "I1", time("10:05"), "escalation", 15)
    notice("N11", "I2", time("10:30"), "initial", None)
    notice("N12", "E3", time("11:59"), "initial", None)
    notice("N13", "R0", time("08:01"), "repeat", 20)
    notice("N14", "R2", time("10:45"), "initial", None)
    sources.append({"id": "EV-UNLINKED", "locator": "synthetic_history.py#unlinked",
                    "excerpt": "FICTIONAL: Two independent notification export rows at 09:40 and 09:41 have the same service/rule/fingerprint, but neither has incident linkage. They might describe one or two incidents; retain both and request reconciliation. No owner or response inference is possible."})
    notice("N15", None, time("09:40"), "unknown", None)
    notice("N16", None, time("09:41"), "unknown", None)
    notice("N17", "E3", time("12:00"), "repeat", 10)
    notifications.append(copy.deepcopy(notifications[1]))
    return {"schema_version": 1, "synthetic": True,
            "observation": {"start": time("08:00"), "end": time("12:00"),
                "lifecycle_coverage": "complete", "coverage_basis": "COVERAGE excerpt; I2 is explicitly partial. Selected record history only, not a full incident universe.", "source_refs": ["COVERAGE"]},
            "sources": sources, "incidents": incidents, "notifications": notifications}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(packet(), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
