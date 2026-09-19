#!/usr/bin/env python3
"""UIOWA-002: offline, assumption-driven person-hour planning; no bookings or fees."""
from __future__ import annotations
import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass, fields
from pathlib import Path

ROLES = ("Clark", "TJLabs", "University")
PACKAGES = {
    "P1": "Evidence plan and register",
    "P2": "Twelve-cell evidence matrix",
    "P3": "Draft findings and context",
    "P4": "Phased roadmap inputs",
    "P5": "Review, reconciliation and receipts",
    "X": "Cross-cutting coordination",
}

@dataclass(frozen=True)
class Assumptions:
    ess_participants: int = 7
    ris_participants: int = 7
    iam_participants: int = 7
    max_group_size: int = 3
    interview_hours: float = 1.25
    evidence_delay_weeks: int = 0
    review_delay_weeks: int = 0
    clark_capacity: float = 32
    tjlabs_capacity: float = 48
    university_capacity: float = 24
    clark_onsite_share: float = 0.5
    tjlabs_onsite_share: float = 0
    university_onsite_share: float = 0.5
    production_multiplier: float = 1
    clark_coordination_weekly: float = 1.5
    tjlabs_coordination_weekly: float = 2
    university_coordination_weekly: float = 1
    onsite_person_day_hours: float = 6

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field.name}: expected finite number, not boolean")
            if field.name.endswith("participants") or field.name == "max_group_size":
                if value != int(value) or not 1 <= value <= 1000:
                    raise ValueError(f"{field.name}: integer from 1 to 1000 required")
                object.__setattr__(self, field.name, int(value))
            elif field.name.endswith("delay_weeks"):
                if value != int(value) or not 0 <= value <= 4:
                    raise ValueError(f"{field.name}: integer from 0 to 4 required")
                object.__setattr__(self, field.name, int(value))
            elif field.name.endswith("onsite_share"):
                if not 0 <= value <= 1:
                    raise ValueError(f"{field.name}: fraction from 0 to 1 required")
            elif field.name.endswith("coordination_weekly"):
                if value < 0:
                    raise ValueError(f"{field.name}: nonnegative hours required")
            elif value <= 0:
                raise ValueError(f"{field.name}: positive number required")

    @classmethod
    def from_mapping(cls, data):
        if not isinstance(data, dict):
            raise ValueError("assumptions must be an object")
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"unknown assumptions: {sorted(unknown)}")
        return cls(**data)

    @property
    def participants(self):
        return self.ess_participants + self.ris_participants + self.iam_participants

    @property
    def sessions_by_group(self):
        return {group: math.ceil(getattr(self, f"{group.lower()}_participants") / self.max_group_size)
                for group in ("ESS", "RIS", "IAM")}

# Work breakdown buckets are a planning decomposition, not contract amendments.
# tuple: id, package, activity, six(start,end), eight(start,end), evidence-dependent,
# post-review dependent, meeting eligible for onsite subset, hour basis / explanation.
SPECS = [
    ("A01", "P1", "Kickoff preparation / evidence plan", (1,1), (1,1), 0,0,0, "fixed", (4,12,2)),
    ("A02", "P1", "Kickoff workshop", (1,1), (1,1), 0,0,1, "fixed", (3,3,9)),
    ("A03", "P1", "Evidence inventory / intake", (1,2), (1,3), 1,0,0, "fixed", (4,20,10)),
    ("A04", "P1", "Interview coordination", (1,2), (1,3), 1,0,0, "sessions", (.5,.25,.5)),
    ("A05", "P2", "Interview preparation / pre-read", (1,2), (1,3), 1,0,0, "prepare", (.75,1,.5)),
    ("A06", "P2", "Facilitated group interviews", (2,3), (2,4), 1,0,1, "interviews", (1,1,1)),
    ("A07", "P2", "Debrief / evidence processing", (2,3), (2,4), 1,0,0, "sessions", (.5,1.5,0)),
    ("A08", "P2", "Twelve-cell evidence matrix", (2,3), (3,5), 1,0,0, "fixed", (12,36,6)),
    ("A09", "P3", "Draft findings / synthesis", (3,4), (4,6), 1,0,0, "fixed", (20,40,6)),
    ("A10", "P3", "Peer-context interpretation", (2,4), (3,5), 1,0,0, "fixed", (14,16,2)),
    ("A11", "P4", "Prioritized phased roadmap", (3,4), (5,6), 1,0,0, "fixed", (12,24,4)),
    ("A12", "P5", "Prime consolidated draft review", (5,5), (7,7), 1,0,0, "fixed", (10,4,0)),
    ("A13", "P5", "University draft review / factual input", (5,5), (7,7), 1,0,0, "fixed", (4,4,12)),
    ("A14", "P5", "Corrections / reconciliation", (6,6), (8,8), 1,1,0, "fixed", (6,20,4)),
    ("A15", "P5", "Final artifact QA / receipts", (6,6), (8,8), 1,1,0, "fixed", (6,16,2)),
    ("A16", "X", "Weekly coordination / decisions", (1,6), (1,8), 0,0,0, "coordination", (0,0,0)),
]

def build_plan(a: Assumptions, target_weeks: int):
    if isinstance(target_weeks, bool) or target_weeks not in (6, 8):
        raise ValueError("target_weeks must be 6 or 8")
    sessions = sum(a.sessions_by_group.values())
    horizon = target_weeks + a.evidence_delay_weeks + a.review_delay_weeks
    capacities = dict(zip(ROLES, (a.clark_capacity,a.tjlabs_capacity,a.university_capacity)))
    shares = (a.clark_onsite_share,a.tjlabs_onsite_share,a.university_onsite_share)
    tasks = []
    for key, package, title, six, eight, evidence, review, meeting, basis, factors in SPECS:
        start, end = six if target_weeks == 6 else eight
        shift = evidence*a.evidence_delay_weeks + review*a.review_delay_weeks
        start, end = start+shift, end+shift
        if basis == "coordination":
            end = horizon
            hours = [horizon*x for x in (a.clark_coordination_weekly,a.tjlabs_coordination_weekly,a.university_coordination_weekly)]
        elif basis == "fixed":
            hours = [x*a.production_multiplier for x in factors]
        elif basis == "sessions":
            hours = [x*sessions for x in factors]
        elif basis == "prepare":
            hours = [factors[0]*sessions,factors[1]*sessions,factors[2]*a.participants]
        else:
            hours = [sessions*a.interview_hours,sessions*a.interview_hours,a.participants*a.interview_hours]
        tasks.append({"id":key,"package":package,"activity":title,"start_week":start,"end_week":end,
                      "hours":dict(zip(ROLES,hours)),"onsite_hours":dict(zip(ROLES,[h*s*meeting for h,s in zip(hours,shares)]))})
    weekly = []
    for week in range(1, horizon+1):
        hours = {r:sum(t["hours"][r]/(t["end_week"]-t["start_week"]+1) for t in tasks if t["start_week"]<=week<=t["end_week"]) for r in ROLES}
        weekly.append({"week":week,"within_target":week<=target_weeks,"hours":hours,
                       "utilization":{r:hours[r]/capacities[r] for r in ROLES}})
    totals = {r:sum(t["hours"][r] for t in tasks) for r in ROLES}
    onsite = {r:sum(t["onsite_hours"][r] for t in tasks) for r in ROLES}
    by_package = {p:{r:sum(t["hours"][r] for t in tasks if t["package"]==p) for r in ROLES} for p in PACKAGES}
    return {"status":"PROPOSED_PLANNING_ONLY","target_weeks":target_weeks,"finish_week":horizon,
            "weeks_beyond_target":horizon-target_weeks,"participants":a.participants,"sessions":sessions,
            "sessions_by_group":a.sessions_by_group,"assumptions":asdict(a),"tasks":tasks,"weekly":weekly,
            "totals":totals,"by_package":by_package,"onsite_hours":onsite,
            "onsite_person_days":{r:onsite[r]/a.onsite_person_day_hours for r in ROLES},
            "peak_hours":{r:max(w["hours"][r] for w in weekly) for r in ROLES},
            "over_capacity_weeks":{r:[w["week"] for w in weekly if w["hours"][r]>capacities[r]+1e-9] for r in ROLES},
            "scheduling_authority":False,"tjlabs_onsite_change_required":a.tjlabs_onsite_share>0}

def export(directory: Path, a: Assumptions):
    directory.mkdir(parents=True,exist_ok=True)
    plans = [build_plan(a,n) for n in (6,8)]
    (directory/"staffing_plans.json").write_text(json.dumps(plans,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    with (directory/"weekly_hours.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.writer(stream)
        writer.writerow(["target_weeks","week","within_target",*ROLES])
        for p in plans:
            for w in p["weekly"]:
                writer.writerow([p["target_weeks"],w["week"],w["within_target"],*[round(w["hours"][r],6) for r in ROLES]])
    return plans

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assumptions",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    try:
        a=Assumptions.from_mapping(json.loads(args.assumptions.read_text(encoding="utf-8"))) if args.assumptions else Assumptions()
        plans=export(args.out,a)
    except (ValueError,OSError,TypeError) as exc:
        parser.exit(2,f"Invalid planning input: {exc}\n")
    print(json.dumps([{k:p[k] for k in ("target_weeks","finish_week","totals","peak_hours","over_capacity_weeks")} for p in plans],indent=2))

if __name__ == "__main__":
    main()
