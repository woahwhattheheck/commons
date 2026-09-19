#!/usr/bin/env python3
"""Feasible one-to-two-level improvement paths (RFQ 18649, work order 030).

Translates a stated current practice profile into realistic next one or two
maturity levels, with prerequisites, capability changes, adoption evidence,
effort and skill needs, and observable advancement.

The rule this file exists to enforce
------------------------------------
**No aspirational endpoint, and no unverified baseline presented as fact.**

That is implemented, not asserted, in four places:

1.  **A path is emitted only if the evidence it would actually produce reaches
    the target level's evidence cap.** The maturity anchors (UIOWA-021) bound
    what a kind of evidence can demonstrate regardless of volume: policy
    documents alone cap at level 2, a single observed instance caps at 3, level 4
    needs repeated instances across a window, and level 5 additionally needs
    outcome measurement. So "write a policy, reach level 4" is refused by
    arithmetic, not by a warning in prose. A step that produces the wrong *kind*
    of evidence cannot buy a level however much effort it carries.

2.  **Jumps beyond +2 are refused.** The order asks for one-to-two-level paths.
    A plan that reaches further is an aspiration, and it is rejected by name.

3.  **A target with no observable advancement criterion is refused.** Not emitted
    with a TBD, not emitted with a generic "review adoption". If nobody can say
    what would be observed, the step is not a plan.

4.  **A baseline that the stated evidence does not support is UNKNOWN, and an
    UNKNOWN baseline generates no path.** You cannot plan a route from a place
    you have not established. The unknown is reported with the evidence that
    would settle it.

Every profile carried here is a synthetic assumption set. Nothing in this module
describes the University of Iowa's actual practice, and no output may be
presented as a University baseline or finding.

Offline, Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------------

ASSESSMENT_AREAS: Tuple[str, ...] = (
    "software_development",
    "security",
    "deployment",
    "ai_readiness",
)

#: Evidence kinds, and the highest maturity level each can support ON ITS OWN.
#: This is the UIOWA-021 anchor contract's central rule: volume cannot buy a
#: level. Ten written policies are still zero instances of practice.
EVIDENCE_KIND_CAPS: Dict[str, int] = {
    "policy_document": 2,
    "procedure_document": 2,
    "single_observed_instance": 3,
    "repeated_instances": 4,
    "outcome_measurement": 5,
}

MIN_LEVEL = 1
MAX_LEVEL = 5

#: The order asks for one-to-two-level paths. Anything further is aspiration.
MAX_LEVEL_GAIN = 2

ASSESSED = "assessed"
UNASSESSED = "unassessed"
NOT_APPLICABLE = "not_applicable"

FEASIBLE = "FEASIBLE"
REFUSED_ASPIRATIONAL_JUMP = "REFUSED_ASPIRATIONAL_JUMP"
REFUSED_EVIDENCE_CAP = "REFUSED_EVIDENCE_CAP"
REFUSED_NO_OBSERVABLE = "REFUSED_NO_OBSERVABLE"
REFUSED_UNMET_PREREQUISITE = "REFUSED_UNMET_PREREQUISITE"
BASELINE_UNKNOWN = "BASELINE_UNKNOWN"

#: Path variants the order names.
VARIANT_DIRECT = "direct"
VARIANT_LIMITED_CAPACITY = "limited_capacity"
VARIANT_SHARED_SERVICE = "shared_service"

CONTENT_CLASS = "SYNTHETIC_ASSUMPTION_SET_NOT_A_UNIVERSITY_BASELINE"


class ProgressionError(ValueError):
    """Input the method refuses to interpret by guessing."""


# --------------------------------------------------------------------------------
# Evidence and baseline
# --------------------------------------------------------------------------------


class EvidenceAssumption:
    """One stated assumption about what evidence exists today.

    It is an *assumption*, and it says so in its own type name, because the whole
    method rests on these and none of them was observed at the University.
    """

    def __init__(self, payload: Dict[str, Any], *, profile_id: str) -> None:
        kind = payload.get("kind")
        if kind not in EVIDENCE_KIND_CAPS:
            raise ProgressionError(
                f"{profile_id}: evidence kind {kind!r} is not one of "
                f"{sorted(EVIDENCE_KIND_CAPS)}. An unrecognized kind cannot be "
                f"capped, and an uncapped kind could buy any level."
            )
        self.kind = kind
        self.statement = str(payload.get("statement", "")).strip()
        self.basis = str(payload.get("basis", "")).strip()
        if not self.statement:
            raise ProgressionError(
                f"{profile_id}: every evidence assumption needs a 'statement'"
            )
        if not self.basis:
            raise ProgressionError(
                f"{profile_id}: evidence assumption {self.statement!r} has no "
                f"'basis'. An assumption with no stated origin is indistinguishable "
                f"from an observation, which is exactly the confusion this method "
                f"must not create."
            )

    @property
    def cap(self) -> int:
        return EVIDENCE_KIND_CAPS[self.kind]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "supports_up_to_level": self.cap,
            "statement": self.statement,
            "basis": self.basis,
        }


class Profile:
    """A stated current practice profile for one group and assessment area."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        profile_id = payload.get("profile_id")
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise ProgressionError("every profile needs a 'profile_id'")
        self.profile_id = profile_id.strip()
        area = payload.get("assessment_area")
        if area not in ASSESSMENT_AREAS:
            raise ProgressionError(
                f"{self.profile_id}: assessment_area must be one of "
                f"{list(ASSESSMENT_AREAS)}, got {area!r}"
            )
        self.assessment_area = area
        self.group = str(payload.get("group", "")).strip()
        self.practice = str(payload.get("practice", "")).strip()

        status = payload.get("assessment_status", ASSESSED)
        if status not in (ASSESSED, UNASSESSED, NOT_APPLICABLE):
            raise ProgressionError(
                f"{self.profile_id}: assessment_status must be one of "
                f"{[ASSESSED, UNASSESSED, NOT_APPLICABLE]}"
            )
        self.assessment_status = status

        self.evidence = [
            EvidenceAssumption(entry, profile_id=self.profile_id)
            for entry in payload.get("evidence_assumptions", [])
        ]
        self.capacity_note = str(payload.get("capacity_note", "")).strip()
        self.shared_services = list(payload.get("shared_services", []))

    # -- baseline ---------------------------------------------------------------

    def baseline(self) -> Dict[str, Any]:
        """The current level the stated evidence supports. Never asserted.

        The level is the best cap any single stated evidence kind reaches. If no
        evidence is stated, or the profile is unassessed/not-applicable, the
        baseline is UNKNOWN with `maturity_rank = None` -- it never falls back to
        level 1, because "we have not established this" is not "this is bad".
        """
        if self.assessment_status != ASSESSED:
            return {
                "maturity_rank": None,
                "maturity_label": None,
                "assessment_status": self.assessment_status,
                "basis": (
                    f"assessment_status is '{self.assessment_status}', so no "
                    f"level is computed. Not level 1: an unassessed practice is "
                    f"an open question, not a weak one."
                ),
                "supporting_evidence": [],
                "evidence_needed_to_establish": [
                    "an assessment of this practice, with stated evidence"
                ],
            }
        if not self.evidence:
            return {
                "maturity_rank": None,
                "maturity_label": None,
                "assessment_status": UNASSESSED,
                "basis": (
                    "no evidence assumption is stated, so no level is supported. "
                    "Not level 1: absence of stated evidence is not evidence of "
                    "absence."
                ),
                "supporting_evidence": [],
                "evidence_needed_to_establish": [
                    "at least one stated evidence assumption with its basis"
                ],
            }
        best = max(self.evidence, key=lambda e: e.cap)
        return {
            "maturity_rank": best.cap,
            "maturity_label": LEVEL_LABELS[best.cap],
            "assessment_status": ASSESSED,
            "basis": (
                f"the strongest stated evidence is '{best.kind}', which supports "
                f"up to level {best.cap}. This is what the ASSUMED evidence "
                f"supports, not an observation of any real practice."
            ),
            "supporting_evidence": [e.to_dict() for e in self.evidence],
            "evidence_needed_to_establish": [],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "assessment_area": self.assessment_area,
            "group": self.group,
            "practice": self.practice,
            "assessment_status": self.assessment_status,
            "evidence_assumptions": [e.to_dict() for e in self.evidence],
            "capacity_note": self.capacity_note,
            "shared_services": list(self.shared_services),
            "content_class": CONTENT_CLASS,
        }


LEVEL_LABELS: Dict[int, str] = {
    1: "ad hoc",
    2: "documented",
    3: "practised",
    4: "consistent",
    5: "measured",
}


# --------------------------------------------------------------------------------
# Steps and paths
# --------------------------------------------------------------------------------


class Step:
    """One capability change, with what it costs and what it would produce."""

    def __init__(self, payload: Dict[str, Any], *, path_id: str) -> None:
        self.step_id = str(payload.get("step_id", "")).strip()
        if not self.step_id:
            raise ProgressionError(f"{path_id}: every step needs a 'step_id'")
        self.capability_change = str(payload.get("capability_change", "")).strip()
        if not self.capability_change:
            raise ProgressionError(
                f"{path_id}/{self.step_id}: a step must state its capability change"
            )
        produces = payload.get("produces_evidence_kind")
        if produces not in EVIDENCE_KIND_CAPS:
            raise ProgressionError(
                f"{path_id}/{self.step_id}: 'produces_evidence_kind' must be one "
                f"of {sorted(EVIDENCE_KIND_CAPS)}. A step whose evidence kind is "
                f"unstated cannot be checked against the target level, and would "
                f"let any step claim any level."
            )
        self.produces_evidence_kind = produces
        self.observable_advancement = str(
            payload.get("observable_advancement", "")
        ).strip()
        self.prerequisites = [str(p) for p in payload.get("prerequisites", [])]
        self.effort_person_days = payload.get("effort_person_days")
        self.skills_needed = [str(s) for s in payload.get("skills_needed", [])]
        self.effort_basis = str(payload.get("effort_basis", "")).strip()

    @property
    def supports_up_to(self) -> int:
        return EVIDENCE_KIND_CAPS[self.produces_evidence_kind]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "capability_change": self.capability_change,
            "produces_evidence_kind": self.produces_evidence_kind,
            "supports_up_to_level": self.supports_up_to,
            "observable_advancement": self.observable_advancement or None,
            "prerequisites": list(self.prerequisites),
            "effort_person_days": (
                None if self.effort_person_days in (None, "", "UNKNOWN")
                else self.effort_person_days
            ),
            "effort_basis": self.effort_basis,
            "skills_needed": list(self.skills_needed),
        }


class PathProposal:
    """A proposed route from a profile's baseline to a target level."""

    def __init__(self, payload: Dict[str, Any]) -> None:
        self.path_id = str(payload.get("path_id", "")).strip()
        if not self.path_id:
            raise ProgressionError("every path needs a 'path_id'")
        self.profile_id = str(payload.get("profile_id", "")).strip()
        if not self.profile_id:
            raise ProgressionError(f"{self.path_id}: needs a 'profile_id'")
        variant = payload.get("variant", VARIANT_DIRECT)
        if variant not in (
            VARIANT_DIRECT,
            VARIANT_LIMITED_CAPACITY,
            VARIANT_SHARED_SERVICE,
        ):
            raise ProgressionError(
                f"{self.path_id}: variant must be one of "
                f"{[VARIANT_DIRECT, VARIANT_LIMITED_CAPACITY, VARIANT_SHARED_SERVICE]}"
            )
        self.variant = variant
        self.rationale = str(payload.get("rationale", "")).strip()
        target = payload.get("target_level")
        if not isinstance(target, int) or isinstance(target, bool):
            raise ProgressionError(
                f"{self.path_id}: 'target_level' must be an integer level"
            )
        if target < MIN_LEVEL or target > MAX_LEVEL:
            raise ProgressionError(
                f"{self.path_id}: target_level {target} is outside {MIN_LEVEL}-"
                f"{MAX_LEVEL}"
            )
        self.target_level = target
        self.steps = [
            Step(entry, path_id=self.path_id) for entry in payload.get("steps", [])
        ]


# --------------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------------


def evaluate_path(path: PathProposal, profile: Profile) -> Dict[str, Any]:
    """Decide whether a proposed path is feasible, and say exactly why not.

    Check order is the policy. The baseline is established first, because a path
    from an unestablished start cannot be assessed at all. Then the size of the
    jump, then whether the steps' evidence can actually reach the target, then
    whether advancement is observable, then prerequisites.
    """
    baseline = profile.baseline()
    record: Dict[str, Any] = {
        "path_id": path.path_id,
        "profile_id": profile.profile_id,
        "assessment_area": profile.assessment_area,
        "group": profile.group,
        "practice": profile.practice,
        "variant": path.variant,
        "rationale": path.rationale,
        "baseline": baseline,
        "target_level": path.target_level,
        "target_label": LEVEL_LABELS[path.target_level],
        "steps": [s.to_dict() for s in path.steps],
        "content_class": CONTENT_CLASS,
    }

    # 1. You cannot plan a route from a place you have not established.
    if baseline["maturity_rank"] is None:
        record["verdict"] = BASELINE_UNKNOWN
        record["level_gain"] = None
        record["reason"] = (
            "No path is produced. The baseline is not established: "
            + baseline["basis"]
            + " A route needs a starting point, and inventing one would be the "
            "unverified baseline this method must not present as fact."
        )
        record["what_would_unblock_it"] = baseline["evidence_needed_to_establish"]
        return record

    current = baseline["maturity_rank"]
    gain = path.target_level - current
    record["level_gain"] = gain

    # 2. One-to-two levels. Further is aspiration.
    if gain > MAX_LEVEL_GAIN:
        record["verdict"] = REFUSED_ASPIRATIONAL_JUMP
        record["reason"] = (
            f"Refused: level {current} to level {path.target_level} is a gain of "
            f"{gain}, beyond the {MAX_LEVEL_GAIN}-level maximum this method will "
            f"plan. A longer jump is an aspiration, not a path; split it and plan "
            f"the first {MAX_LEVEL_GAIN} levels."
        )
        return record
    if gain <= 0:
        record["verdict"] = REFUSED_ASPIRATIONAL_JUMP
        record["reason"] = (
            f"Refused: the target level {path.target_level} is not above the "
            f"established baseline of {current}. There is nothing to advance."
        )
        return record

    # 3. The decisive check. Can the evidence these steps produce actually reach
    #    the target, or is the target being claimed rather than earned?
    best_step = max(path.steps, key=lambda s: s.supports_up_to, default=None)
    reachable = best_step.supports_up_to if best_step else current
    record["evidence_ceiling_of_this_path"] = reachable
    if best_step is None or reachable < path.target_level:
        produced = sorted({s.produces_evidence_kind for s in path.steps}) or ["none"]
        record["verdict"] = REFUSED_EVIDENCE_CAP
        record["reason"] = (
            f"Refused: these steps produce {', '.join(produced)}, which supports "
            f"up to level {reachable}. Level {path.target_level} needs evidence of "
            f"a kind this path never creates. Effort cannot buy the difference -- "
            f"the cap is about the kind of evidence, not its volume."
        )
        record["evidence_kind_needed"] = [
            kind
            for kind, cap in sorted(EVIDENCE_KIND_CAPS.items(), key=lambda x: x[1])
            if cap >= path.target_level
        ]
        return record

    # 4. An advancement nobody can observe is not a plan.
    unobservable = [s.step_id for s in path.steps if not s.observable_advancement]
    if unobservable:
        record["verdict"] = REFUSED_NO_OBSERVABLE
        record["reason"] = (
            "Refused: step(s) "
            + ", ".join(unobservable)
            + " state no observable advancement. A step whose completion nobody "
            "can check is not a plan, and it is not made into one by writing TBD."
        )
        return record

    # 5. A prerequisite that no step in the path satisfies.
    provided = {s.step_id for s in path.steps}
    unmet = sorted(
        {
            prerequisite
            for step in path.steps
            for prerequisite in step.prerequisites
            if prerequisite not in provided
        }
    )
    external = [p for p in unmet if p.startswith("EXTERNAL:")]
    internal = [p for p in unmet if not p.startswith("EXTERNAL:")]
    if internal:
        record["verdict"] = REFUSED_UNMET_PREREQUISITE
        record["reason"] = (
            "Refused: prerequisite(s) "
            + ", ".join(internal)
            + " are named by a step but produced by no step in this path. Either "
            "add the step or declare the prerequisite external with an "
            "'EXTERNAL:' prefix so it is visibly somebody else's to deliver."
        )
        return record

    # Feasible. Report the cost honestly, including what is not estimated.
    known = [
        s.effort_person_days
        for s in path.steps
        if isinstance(s.effort_person_days, (int, float))
        and not isinstance(s.effort_person_days, bool)
    ]
    unestimated = [
        s.step_id
        for s in path.steps
        if not (
            isinstance(s.effort_person_days, (int, float))
            and not isinstance(s.effort_person_days, bool)
        )
    ]
    record["verdict"] = FEASIBLE
    record["reason"] = (
        f"Level {current} ({LEVEL_LABELS[current]}) to level "
        f"{path.target_level} ({LEVEL_LABELS[path.target_level]}). The steps "
        f"produce {best_step.produces_evidence_kind}, which supports up to level "
        f"{reachable}, so the target is earned by the evidence rather than "
        f"asserted."
    )
    record["effort_person_days_known"] = round(sum(known), 2) if known else 0
    record["effort_is_partial"] = bool(unestimated)
    record["effort_unestimated_steps"] = unestimated
    record["effort_statement"] = (
        f"{round(sum(known), 2)} person-days across "
        f"{len(path.steps) - len(unestimated)} of {len(path.steps)} steps"
        + (
            f"; {len(unestimated)} step(s) unestimated ("
            + ", ".join(unestimated)
            + "), so this is a FLOOR, not a total"
            if unestimated
            else ""
        )
    )
    record["skills_needed"] = sorted(
        {skill for step in path.steps for skill in step.skills_needed}
    )
    record["external_prerequisites"] = external
    record["observable_advancement"] = [
        {"step_id": s.step_id, "observable": s.observable_advancement}
        for s in path.steps
    ]
    return record


def evaluate_all(
    paths: Sequence[PathProposal], profiles: Sequence[Profile]
) -> Dict[str, Any]:
    by_id = {p.profile_id: p for p in profiles}
    results: List[Dict[str, Any]] = []
    for path in paths:
        profile = by_id.get(path.profile_id)
        if profile is None:
            raise ProgressionError(
                f"{path.path_id}: no profile {path.profile_id!r}. A path with no "
                f"stated starting profile has no baseline to plan from."
            )
        results.append(evaluate_path(path, profile))

    verdicts: Dict[str, int] = {}
    for record in results:
        verdicts[record["verdict"]] = verdicts.get(record["verdict"], 0) + 1

    areas_with_feasible = sorted(
        {r["assessment_area"] for r in results if r["verdict"] == FEASIBLE}
    )
    return {
        "content_class": CONTENT_CLASS,
        "paths": results,
        "counts_by_verdict": verdicts,
        "coverage": {
            "assessment_areas": list(ASSESSMENT_AREAS),
            "areas_with_a_feasible_path": areas_with_feasible,
            "areas_without_a_feasible_path": [
                a for a in ASSESSMENT_AREAS if a not in areas_with_feasible
            ],
        },
        "scale": {
            "levels": {str(k): v for k, v in LEVEL_LABELS.items()},
            "evidence_kind_caps": dict(EVIDENCE_KIND_CAPS),
            "source": (
                "Anchor contract from UIOWA-021 (maturity anchors) as declared in "
                "the build channel. This module consumes that scale and does not "
                "define a second one."
            ),
        },
        "limits": [
            "Every profile here is a synthetic assumption set. None describes the "
            "University of Iowa's practice, and no output may be presented as a "
            "University baseline or finding.",
            "A FEASIBLE verdict means the path's evidence kind can reach the "
            "target level and every step is observable. It is not a prediction "
            "that the work will succeed, and not a commitment to deliver it.",
            "Effort figures are stated assumptions. Where a step is unestimated "
            "the total is reported as a floor, never completed to a round number.",
            "No individual, team or unit is rated anywhere in this output.",
        ],
    }


# --------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------


def load_profiles(payload: Any) -> List[Profile]:
    if isinstance(payload, dict):
        payload = payload.get("profiles")
    if not isinstance(payload, list):
        raise ProgressionError("expected an object with a 'profiles' list")
    profiles = [Profile(entry) for entry in payload]
    seen: Dict[str, int] = {}
    for profile in profiles:
        seen[profile.profile_id] = seen.get(profile.profile_id, 0) + 1
    duplicates = sorted(k for k, v in seen.items() if v > 1)
    if duplicates:
        raise ProgressionError(f"duplicate profile_id(s): {duplicates}")
    return profiles


def load_paths(payload: Any) -> List[PathProposal]:
    if isinstance(payload, dict):
        payload = payload.get("paths")
    if not isinstance(payload, list):
        raise ProgressionError("expected an object with a 'paths' list")
    paths = [PathProposal(entry) for entry in payload]
    seen: Dict[str, int] = {}
    for path in paths:
        seen[path.path_id] = seen.get(path.path_id, 0) + 1
    duplicates = sorted(k for k, v in seen.items() if v > 1)
    if duplicates:
        raise ProgressionError(f"duplicate path_id(s): {duplicates}")
    return paths


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError as exc:
            raise ProgressionError(f"{path}: not valid JSON ({exc})") from exc


# --------------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------------

CSV_COLUMNS = [
    "path_id",
    "profile_id",
    "assessment_area",
    "variant",
    "verdict",
    "baseline_level",
    "target_level",
    "level_gain",
    "evidence_ceiling",
    "effort_person_days",
    "effort_is_partial",
    "skills_needed",
    "reason",
]


def to_csv_rows(result: Dict[str, Any]) -> List[List[str]]:
    rows: List[List[str]] = [list(CSV_COLUMNS)]
    for record in result["paths"]:
        baseline = record["baseline"]["maturity_rank"]
        effort = record.get("effort_person_days_known")
        rows.append(
            [
                record["path_id"],
                record["profile_id"],
                record["assessment_area"],
                record["variant"],
                record["verdict"],
                # A word, never a blank and never 0: an unestablished baseline
                # must not sort as the bottom of the scale.
                "UNKNOWN" if baseline is None else str(baseline),
                str(record["target_level"]),
                "UNKNOWN" if record["level_gain"] is None else str(record["level_gain"]),
                str(record.get("evidence_ceiling_of_this_path", "")),
                "NOT_APPLICABLE" if effort is None else str(effort),
                "YES" if record.get("effort_is_partial") else "NO",
                "|".join(record.get("skills_needed", [])) or "",
                record["reason"],
            ]
        )
    return rows


def write_csv(result: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(to_csv_rows(result))


VERDICT_HEADINGS = {
    FEASIBLE: "Feasible paths",
    REFUSED_ASPIRATIONAL_JUMP: "Refused: aspirational jump",
    REFUSED_EVIDENCE_CAP: "Refused: the evidence cannot reach the target",
    REFUSED_NO_OBSERVABLE: "Refused: advancement is not observable",
    REFUSED_UNMET_PREREQUISITE: "Refused: an unmet prerequisite",
    BASELINE_UNKNOWN: "No path: the baseline is not established",
}

VERDICT_ORDER = (
    FEASIBLE,
    BASELINE_UNKNOWN,
    REFUSED_EVIDENCE_CAP,
    REFUSED_ASPIRATIONAL_JUMP,
    REFUSED_NO_OBSERVABLE,
    REFUSED_UNMET_PREREQUISITE,
)


def render_markdown(result: Dict[str, Any]) -> str:
    out: List[str] = []
    out.append("# Feasible one-to-two-level improvement paths")
    out.append("")
    out.append(
        "**SYNTHETIC. Every profile below is an assumption set written to "
        "exercise the method.** None describes the University of Iowa's practice. "
        "No level, path or effort figure here is a University baseline, a "
        "finding, or a commitment."
    )
    out.append("")
    out.append("## The scale this method plans against")
    out.append("")
    out.append(result["scale"]["source"])
    out.append("")
    out.append("| level | label | reachable only with |")
    out.append("|---:|---|---|")
    for level in range(MIN_LEVEL, MAX_LEVEL + 1):
        kinds = sorted(
            k for k, cap in EVIDENCE_KIND_CAPS.items() if cap >= level
        )
        out.append(
            f"| {level} | {LEVEL_LABELS[level]} | "
            + (", ".join(f"`{k}`" for k in kinds) or "—")
            + " |"
        )
    out.append("")
    out.append(
        "**The kind of evidence bounds the level, and volume cannot raise the "
        "bound.** Ten policy documents are still zero instances of practice, so "
        "they support level 2 and no more. This is what makes a target *earned* "
        "rather than claimed, and it is the mechanism that refuses an aspirational "
        "endpoint."
    )
    out.append("")

    counts = result["counts_by_verdict"]
    out.append("## Result")
    out.append("")
    out.append("| verdict | paths |")
    out.append("|---|---:|")
    for verdict in VERDICT_ORDER:
        if verdict in counts:
            out.append(f"| `{verdict}` | {counts[verdict]} |")
    out.append("")
    coverage = result["coverage"]
    out.append(
        f"Assessment areas with at least one feasible path: "
        f"{len(coverage['areas_with_a_feasible_path'])} of "
        f"{len(coverage['assessment_areas'])}"
        + (
            " — " + ", ".join(coverage["areas_without_a_feasible_path"]) +
            " have none, and that is reported rather than filled in."
            if coverage["areas_without_a_feasible_path"]
            else "."
        )
    )
    out.append("")

    for verdict in VERDICT_ORDER:
        group = [r for r in result["paths"] if r["verdict"] == verdict]
        if not group:
            continue
        out.append(f"## {VERDICT_HEADINGS[verdict]}")
        out.append("")
        for record in group:
            baseline = record["baseline"]
            out.append(
                f"### `{record['path_id']}` — {record['assessment_area']} "
                f"({record['variant']})"
            )
            out.append("")
            out.append(f"*Profile:* `{record['profile_id']}` — {record['practice']}")
            out.append("")
            out.append(
                "**Baseline (assumed): "
                + (
                    "UNKNOWN"
                    if baseline["maturity_rank"] is None
                    else f"level {baseline['maturity_rank']} "
                    f"({baseline['maturity_label']})"
                )
                + "** — "
                + baseline["basis"]
            )
            out.append("")
            if baseline["supporting_evidence"]:
                out.append("Evidence assumptions this rests on:")
                out.append("")
                for evidence in baseline["supporting_evidence"]:
                    out.append(
                        f"- `{evidence['kind']}` (supports to level "
                        f"{evidence['supports_up_to_level']}) — "
                        f"{evidence['statement']}  \n"
                        f"  *basis:* {evidence['basis']}"
                    )
                out.append("")
            out.append(
                f"**Target: level {record['target_level']} "
                f"({record['target_label']})**"
                + (
                    f" — gain of {record['level_gain']}"
                    if record["level_gain"] is not None
                    else ""
                )
            )
            out.append("")
            out.append(f"**{record['verdict']}.** {record['reason']}")
            out.append("")
            if record.get("what_would_unblock_it"):
                out.append("What would unblock it:")
                out.append("")
                for item in record["what_would_unblock_it"]:
                    out.append(f"- {item}")
                out.append("")
            if record.get("evidence_kind_needed"):
                out.append(
                    "Evidence kinds that could reach the target: "
                    + ", ".join(f"`{k}`" for k in record["evidence_kind_needed"])
                )
                out.append("")
            if record["steps"]:
                out.append(
                    "| step | capability change | produces | to level | effort (d) | observable advancement |"
                )
                out.append("|---|---|---|---:|---:|---|")
                for step in record["steps"]:
                    out.append(
                        "| `{sid}` | {change} | `{kind}` | {cap} | {effort} | {obs} |".format(
                            sid=step["step_id"],
                            change=step["capability_change"],
                            kind=step["produces_evidence_kind"],
                            cap=step["supports_up_to_level"],
                            effort=(
                                "UNKNOWN"
                                if step["effort_person_days"] is None
                                else step["effort_person_days"]
                            ),
                            obs=step["observable_advancement"] or "**none stated**",
                        )
                    )
                out.append("")
            if record["verdict"] == FEASIBLE:
                out.append(f"- **Effort:** {record['effort_statement']}")
                out.append(
                    "- **Skills:** "
                    + (", ".join(record["skills_needed"]) or "none stated")
                )
                if record["external_prerequisites"]:
                    out.append(
                        "- **External prerequisites (not ours to deliver):** "
                        + ", ".join(
                            p.replace("EXTERNAL:", "")
                            for p in record["external_prerequisites"]
                        )
                    )
                out.append("")
            if record.get("rationale"):
                out.append(f"*Why this variant:* {record['rationale']}")
                out.append("")

    out.append("## Limits")
    out.append("")
    for limit in result["limits"]:
        out.append(f"- {limit}")
    out.append("")
    out.append("---")
    out.append("")
    out.append(
        "Generated offline by `progression.py` (Python standard library only). "
        "Synthetic throughout."
    )
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        prog="progression.py",
        description=(
            "Evaluate proposed one-to-two-level improvement paths against a "
            "stated practice profile, refusing any target the path's evidence "
            "cannot reach."
        ),
    )
    parser.add_argument(
        "--profiles", default=os.path.join(here, "fixtures", "profiles.json")
    )
    parser.add_argument(
        "--paths", default=os.path.join(here, "fixtures", "paths.json")
    )
    parser.add_argument("--json-out")
    parser.add_argument("--csv-out")
    parser.add_argument("--markdown-out")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        profiles = load_profiles(read_json(args.profiles))
        paths = load_paths(read_json(args.paths))
        result = evaluate_all(paths, profiles)
    except ProgressionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    markdown = render_markdown(result)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    if args.csv_out:
        write_csv(result, args.csv_out)
    if args.markdown_out:
        with open(args.markdown_out, "w", encoding="utf-8") as handle:
            handle.write(markdown)
    if not (args.json_out or args.csv_out or args.markdown_out):
        print(markdown)

    counts = result["counts_by_verdict"]
    print(
        "[progression] "
        + ", ".join(f"{v}={counts[v]}" for v in VERDICT_ORDER if v in counts)
        + f"; areas with a feasible path: "
        f"{len(result['coverage']['areas_with_a_feasible_path'])}/"
        f"{len(ASSESSMENT_AREAS)}.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
