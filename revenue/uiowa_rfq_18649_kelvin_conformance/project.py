#!/usr/bin/env python3
"""Project this seat's three lane outputs into the UIOWA-023 evidence register.

Why this exists: lanes 071, 107 and 108 each claim their output "joins" the
evidence register. That claim was made by matching field NAMES and ID shapes.
Field-shape conformance is not semantic conformance -- a projection can
satisfy every regex in a schema and still say something the source record
never said.

So this module writes the real 22-column rows, and conformance.py runs the
register's own validator over them. Where a semantic loss is unavoidable it
is DECLARED in divergences.json rather than absorbed; an undeclared
divergence fails.

All three sources are fictional rehearsal records. The projection carries
that forward; it does not launder synthetic rows into evidence.
"""

import json
import os

REGISTER_COLUMNS = [
    "evidence_id", "observation_id", "finding_id", "group", "area",
    "source_type", "source_ref", "captured_at", "represented_period",
    "claim", "scope_limit", "directness", "recency", "representativeness",
    "corroboration", "evidence_state", "confidence", "conflict_group",
    "universe_definition", "enumerator_authority", "completeness_basis",
    "follow_up",
]

SYNTHETIC_NOTE = "FICTIONAL rehearsal record; not a University finding"


class Counter(object):
    """Sequence numbers scoped to (group, area) so ids stay unique and carry
    the scope marker the register checks for."""

    def __init__(self):
        self._n = {}

    def next(self, group, area):
        key = (group, area)
        self._n[key] = self._n.get(key, 0) + 1
        return self._n[key]


def _row(**kw):
    row = dict((c, "") for c in REGISTER_COLUMNS)
    row.update(kw)
    return row


def _ids(group, area, kind, index):
    return (
        "EV-SYN-%s-%s-%s-%03d" % (group, area, kind, index),
        "OBS-SYN-%s-%s-%03d" % (group, area, index),
        "FND-SYN-%s-%s-%03d" % (group, area, index),
    )


# ---------------------------------------------------------------------------
# UIOWA-071 -- AI-use inventory
# ---------------------------------------------------------------------------

# Declared, not silent. Three inventory classifications land on the same
# register state because the register has no enum that separates them.
INVENTORY_STATE = {
    "ACTIVE_USE": ("SUPPORTING", "MODERATE"),
    "INFORMAL_EXPERIMENT": ("SUPPORTING", "LOW"),
    "PLANNED_USE": ("NO_EVIDENCE_OBSERVED", "NOT_EVIDENCED"),
    "UNSUPPORTED_CLAIM": ("NO_EVIDENCE_OBSERVED", "NOT_EVIDENCED"),
    "UNKNOWN": ("NO_EVIDENCE_OBSERVED", "NOT_EVIDENCED"),
}


def project_inventory(payload, counter):
    rows = []
    skipped = []
    for entry in payload["entries"]:
        group = entry["group"]
        if group not in ("ESS", "RIS", "IAM"):
            skipped.append({"id": entry["entry_id"],
                            "reason": "group %r is outside the register's vocabulary" % group})
            continue
        area = "AI"
        index = counter.next(group, area)
        ev, obs, fnd = _ids(group, area, "INV", index)

        classification = entry["classification"]
        state, confidence = INVENTORY_STATE[classification]
        conflict_group = ""
        gap_kinds = [g["gap"] for g in entry.get("gaps", [])]
        if "STATUS_EVIDENCE_MISMATCH" in gap_kinds:
            # The register does carry this one properly: a record declared
            # not-started that arrives with output is a conflict, and the
            # register's own rule then forces UNRESOLVED plus a conflict
            # group. Nothing is lost here.
            state, confidence = "CONFLICTING", "UNRESOLVED"
            conflict_group = "CG-071-%s" % entry["entry_id"]

        source_ref = (entry.get("evidence_refs") or
                      ["synthetic://uiowa-rfq18649/071/%s" % entry["entry_id"]])[0]
        follow_up = (entry.get("gaps") or [{"follow_up": "No outstanding request for this row."}])[0]["follow_up"]

        rows.append(_row(
            evidence_id=ev, observation_id=obs, finding_id=fnd,
            group=group, area=area,
            source_type="interview",
            source_ref=source_ref,
            captured_at=entry.get("captured_at") or "UNKNOWN",
            represented_period=entry.get("captured_at") or "UNKNOWN",
            claim="%s: %s" % (entry["entry_id"], entry["task"]),
            # The source classification is preserved verbatim here because the
            # evidence_state enum cannot hold it. Losing it would be the whole
            # failure this projection exists to avoid.
            scope_limit="%s; source classification %s (declared %s); %s"
                        % (SYNTHETIC_NOTE, classification, entry["declared_status"],
                           "one team, one captured use"),
            directness="DIRECT" if entry.get("evidence_refs") else "INDIRECT",
            recency="CURRENT" if entry.get("captured_at") not in (None, "", "UNKNOWN") else "UNKNOWN",
            representativeness="SINGLE",
            corroboration="NO_CORROBORATION",
            evidence_state=state, confidence=confidence,
            conflict_group=conflict_group,
            follow_up=follow_up,
        ))
    return rows, skipped


# ---------------------------------------------------------------------------
# UIOWA-108 -- contractor transition
# ---------------------------------------------------------------------------

# This mapping loses nothing. The register distinguishes EVIDENCE_OF_ABSENCE
# (we looked across a bounded universe and it is not there) from
# NO_EVIDENCE_OBSERVED (we have no record either way) -- which is exactly the
# distinction 108 makes between unresolved ownership and missing evidence.
TRANSITION_STATE = {
    "COMPLETED": ("SUPPORTING", "MODERATE"),
    "UNRESOLVED_OWNERSHIP": ("EVIDENCE_OF_ABSENCE", "LOW"),
    "NO_EVIDENCE": ("NO_EVIDENCE_OBSERVED", "NOT_EVIDENCED"),
}


def project_transition(payload, counter):
    rows = []
    skipped = []
    departing = payload["meta"]["departing_ref"]
    packet = payload["meta"]["packet_id"]
    for item in payload["items"]:
        group = item["service"]
        if group not in ("ESS", "RIS", "IAM"):
            skipped.append({"id": item["item_id"],
                            "reason": "service %r is outside the register's vocabulary" % group})
            continue
        area = "SEC"
        index = counter.next(group, area)
        ev, obs, fnd = _ids(group, area, "TRN", index)
        state, confidence = TRANSITION_STATE[item["state"]]

        universe = enumerator = completeness = ""
        if state == "EVIDENCE_OF_ABSENCE":
            universe = ("every application, service identity and runbook recorded as owned by %s "
                        "in packet %s" % (departing, packet))
            enumerator = "the synthetic transition packet itself"
            completeness = "packet enumeration only; not a system export"

        source_ref = (item.get("evidence_refs") or
                      ["synthetic://uiowa-rfq18649/108/%s" % item["item_id"]])[0]
        rows.append(_row(
            evidence_id=ev, observation_id=obs, finding_id=fnd,
            group=group, area=area,
            source_type="artifact" if item.get("evidence_refs") else "interview",
            source_ref=source_ref,
            captured_at="2026-09-18", represented_period="2026-09-18",
            claim="%s (%s): %s" % (item["item_id"], item["kind"], item["label"]),
            scope_limit="%s; source state %s; one departing contractor, one packet"
                        % (SYNTHETIC_NOTE, item["state"]),
            directness="DIRECT" if item.get("evidence_refs") else "INDIRECT",
            recency="CURRENT",
            representativeness="POPULATION_BOUNDED" if state == "EVIDENCE_OF_ABSENCE" else "SINGLE",
            corroboration="NO_CORROBORATION",
            evidence_state=state, confidence=confidence,
            universe_definition=universe,
            enumerator_authority=enumerator,
            completeness_basis=completeness,
            follow_up=item["next_action"],
        ))
    return rows, skipped


# ---------------------------------------------------------------------------
# UIOWA-107 -- deadline continuity assumptions
# ---------------------------------------------------------------------------

# Declared loss: ASSUMED (a working figure with nothing behind it) and
# UNKNOWN (no figure at all) both land on NO_EVIDENCE_OBSERVED.
ASSUMPTION_STATE = {
    "MEASURED": ("SUPPORTING", "MODERATE"),
    "ESTIMATED": ("SUPPORTING", "LOW"),
    "ASSUMED": ("NO_EVIDENCE_OBSERVED", "NOT_EVIDENCED"),
    "UNKNOWN": ("NO_EVIDENCE_OBSERVED", "NOT_EVIDENCED"),
}


def project_continuity(payload, counter):
    rows = []
    skipped = []
    group = payload["meta"]["service"]
    if group not in ("ESS", "RIS", "IAM"):
        return rows, [{"id": payload["meta"]["scenario_id"],
                       "reason": "service %r is outside the register's vocabulary" % group}]
    area = "DEP"
    for assumption in payload["assumptions"]:
        index = counter.next(group, area)
        ev, obs, fnd = _ids(group, area, "ASM", index)
        state, confidence = ASSUMPTION_STATE[assumption["basis"]]
        source_ref = assumption.get("source_ref") or \
            "synthetic://uiowa-rfq18649/107/%s" % assumption["id"]
        rows.append(_row(
            evidence_id=ev, observation_id=obs, finding_id=fnd,
            group=group, area=area,
            source_type="metric" if assumption["basis"] == "MEASURED" else "interview",
            source_ref=source_ref,
            captured_at="2026-09-19", represented_period="2026-09-19",
            claim="%s: %s" % (assumption["id"], assumption["statement"]),
            scope_limit="%s; source basis %s; one scenario, one reporting window"
                        % (SYNTHETIC_NOTE, assumption["basis"]),
            directness="DIRECT" if assumption.get("source_ref") else "INDIRECT",
            recency="CURRENT",
            representativeness="SINGLE",
            corroboration="NO_CORROBORATION",
            evidence_state=state, confidence=confidence,
            follow_up="Resolve or bound this input before it carries a conclusion."
                      if not assumption["resolved"] else
                      "Confirm the stated range against the cited record.",
        ))
    return rows, skipped


SOURCES = (
    ("UIOWA-071", "uiowa_rfq_18649_ai_use_inventory",
     "sample_output/ai_use_inventory.json", project_inventory),
    ("UIOWA-107", "uiowa_rfq_18649_deadline_continuity",
     "sample_output/continuity_analysis.json", project_continuity),
    ("UIOWA-108", "uiowa_rfq_18649_contractor_transition",
     "sample_output/transition_report.json", project_transition),
)


def project_all(revenue_root):
    """Returns (rows, skipped, absent). A missing sibling lane is reported,
    never treated as a pass."""
    counter = Counter()
    rows, skipped, absent = [], [], []
    for order, lane, rel, fn in SOURCES:
        path = os.path.join(revenue_root, lane, rel)
        if not os.path.exists(path):
            absent.append({"order": order, "lane": lane, "path": rel,
                           "reason": "sibling lane output not present; nothing projected"})
            continue
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        lane_rows, lane_skipped = fn(payload, counter)
        for r in lane_rows:
            r["_order"] = order
        rows.extend(lane_rows)
        for s in lane_skipped:
            s["order"] = order
        skipped.extend(lane_skipped)
    return rows, skipped, absent
