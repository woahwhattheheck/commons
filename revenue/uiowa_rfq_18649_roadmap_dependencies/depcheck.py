#!/usr/bin/env python3
"""UIOWA-115 - Roadmap dependency consistency checker.

A graph check over recommendation prerequisites, shared dependencies and
proposed phases. It finds cycles, missing prerequisite references and phase
inversions, and names the exact edge to repair in each case.

Two design decisions do most of the work here:

  1. IT NEVER EMITS A LINEAR ORDER. Asked to check a roadmap, the obvious move
     is to return a topological sort - which is correct, and which silently
     converts "these three groups can go at once" into "do R-04, then R-05,
     then R-06". So this tool reports dependency LEVELS instead. If A is a
     prerequisite of B then level(B) > level(A), therefore two items at the
     same level have no path between them in either direction and are provably
     independent. Parallel work stays parallel because parallelism is the
     output, not a casualty of it.

  2. AN UNRESOLVABLE REFERENCE IS NEVER READ AS SATISFIED. A prerequisite
     pointing at an item nobody defined, an item with no phase, a
     prerequisites field that is not a list - each of these makes the
     surrounding feasibility UNKNOWN. Dropping what you cannot resolve turns a
     broken plan into a clean-looking one, which is the most expensive
     possible output.

Severities are `error`, `unknown`, `open_question` and `info`, kept apart so a
repaired roadmap can honestly read *zero errors, two unknowns still requiring
human input* rather than being rounded to "passed".

Python 3 standard library only. No network. Deterministic: no clock, no RNG,
sorted traversal, stable content digest.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import re
import sys

UNASSIGNED = "UNASSIGNED"
UNKNOWN = "UNKNOWN"

ERROR = "error"
UNKNOWN_SEV = "unknown"
OPEN_QUESTION = "open_question"
INFO = "info"

SEVERITY_ORDER = {ERROR: 0, UNKNOWN_SEV: 1, OPEN_QUESTION: 2, INFO: 3}

DEFAULT_FANIN_THRESHOLD = 3


def finding(severity, code, message, edge=None, items=None, repairs=None, detail=None):
    """One diagnostic. `edge` is (prerequisite_id, dependent_id) when the
    problem is an edge, because "there is a cycle somewhere" is not a repair
    instruction."""
    record = {"severity": severity, "code": code, "message": message}
    if edge is not None:
        record["edge"] = {"prerequisite_id": edge[0], "dependent_id": edge[1]}
    if items is not None:
        record["items"] = sorted(items)
    if repairs is not None:
        record["repairs"] = repairs
    if detail is not None:
        record["detail"] = detail
    return record


def repair(op, mechanical, detail, item_id=None, prerequisite_id=None,
           phase_id=None, choice_group=None):
    """A concrete, named repair. `mechanical` marks the ones a tool may apply
    on its own; anything needing a planner's judgement is mechanical=False and
    the rehearsal leaves it alone."""
    record = {"op": op, "mechanical": bool(mechanical), "detail": detail}
    if item_id is not None:
        record["item_id"] = item_id
    if prerequisite_id is not None:
        record["prerequisite_id"] = prerequisite_id
    if phase_id is not None:
        record["phase_id"] = phase_id
    if choice_group is not None:
        # Several repairs that are alternatives to each other: exactly one of
        # them is applied, and the tool does not pretend its pick is the right
        # one.
        record["choice_group"] = choice_group
    return record


def _nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_phases(obj):
    findings = []
    phases = {}
    order_seen = {}
    for entry in obj.get("phases", []):
        phase_id = entry.get("phase_id")
        if not _nonempty_str(phase_id):
            findings.append(finding(ERROR, "phase_missing_id",
                                    "A phase entry has no phase_id and was skipped."))
            continue
        if phase_id in phases:
            findings.append(finding(ERROR, "phase_duplicate_id",
                                    "Phase '%s' is defined more than once; the later "
                                    "definition was skipped." % phase_id))
            continue
        order = entry.get("order")
        if not _is_int(order):
            findings.append(finding(ERROR, "phase_order_invalid",
                                    "Phase '%s' has a non-integer order (%r) and was "
                                    "skipped; phase comparison would be undefined."
                                    % (phase_id, order)))
            continue
        if order in order_seen:
            findings.append(finding(
                ERROR, "phase_order_duplicate",
                "Phases '%s' and '%s' share order %d, so 'earlier than' is "
                "ambiguous between them." % (order_seen[order], phase_id, order)))
        else:
            order_seen[order] = phase_id
        phases[phase_id] = {"phase_id": phase_id, "order": order,
                            "label": entry.get("label", phase_id)}
    if not phases:
        findings.append(finding(ERROR, "no_phases_defined",
                                "The roadmap defines no usable phases, so no phase "
                                "check can be performed."))
    return phases, findings


def load_items(obj, phases):
    findings = []
    items = {}
    for entry in obj.get("items", []):
        if not isinstance(entry, dict):
            findings.append(finding(ERROR, "item_not_an_object",
                                    "An entry in items is not an object and was skipped."))
            continue
        item_id = entry.get("item_id")
        if not _nonempty_str(item_id):
            findings.append(finding(ERROR, "item_missing_id",
                                    "An item has no item_id and was skipped; it cannot "
                                    "be referenced or repaired."))
            continue
        if item_id in items:
            findings.append(finding(ERROR, "item_duplicate_id",
                                    "Item '%s' is defined more than once; the later "
                                    "definition was skipped rather than merged."
                                    % item_id))
            continue

        unreadable = False
        phase_id = entry.get("phase")
        if phase_id is None or (isinstance(phase_id, str) and not phase_id.strip()):
            phase_id = None
        elif not isinstance(phase_id, str):
            findings.append(finding(ERROR, "phase_reference_invalid",
                                    "Item '%s' has a non-string phase (%r); its phase "
                                    "is UNASSIGNED, not defaulted." % (item_id, phase_id)))
            phase_id = None
        elif phase_id not in phases:
            findings.append(finding(ERROR, "phase_undefined",
                                    "Item '%s' names phase '%s', which the phase list "
                                    "does not define. Its phase is UNASSIGNED, not "
                                    "defaulted to the first phase."
                                    % (item_id, phase_id)))
            phase_id = None

        raw = entry.get("prerequisites", [])
        prerequisites = []
        if raw is None:
            raw = []
        if not isinstance(raw, list):
            findings.append(finding(
                ERROR, "prerequisites_not_a_list",
                "Item '%s' supplies prerequisites as %s, not a list. Its "
                "prerequisites are unreadable, so its feasibility is UNKNOWN - "
                "it is not treated as having none." % (item_id, type(raw).__name__)))
            unreadable = True
            raw = []
        seen = set()
        for element in raw:
            if not _nonempty_str(element):
                findings.append(finding(
                    ERROR, "prerequisite_not_an_id",
                    "Item '%s' lists a prerequisite that is not an identifier "
                    "(%r). It was dropped and the item's feasibility is UNKNOWN."
                    % (item_id, element)))
                unreadable = True
                continue
            element = element.strip()
            if element in seen:
                findings.append(finding(
                    INFO, "duplicate_prerequisite",
                    "Item '%s' lists prerequisite '%s' more than once; the "
                    "repeat was removed and reported, not silently collapsed."
                    % (item_id, element), edge=(element, item_id)))
                continue
            seen.add(element)
            prerequisites.append(element)

        items[item_id] = {
            "item_id": item_id,
            "title": entry.get("title", ""),
            "recommendation_ref": entry.get("recommendation_ref", ""),
            "owner_group": entry.get("owner_group", ""),
            "phase": phase_id,
            "prerequisites": prerequisites,
            "prerequisites_unreadable": unreadable,
        }
    return items, findings


# --------------------------------------------------------------------------
# Graph primitives
# --------------------------------------------------------------------------

def strongly_connected_components(nodes, successors):
    """Tarjan. Returns components as sorted tuples, sorted.

    SCC rather than a DFS back-edge scan, because a back-edge scan names the
    one edge the traversal happened to close the loop on. A planner needs every
    edge inside the entangled set, since any one of them is a valid cut.
    """
    index = {}
    low = {}
    on_stack = {}
    stack = []
    result = []
    counter = [0]

    def strongconnect(root):
        work = [(root, 0)]
        while work:
            node, step = work[-1]
            if step == 0:
                index[node] = counter[0]
                low[node] = counter[0]
                counter[0] += 1
                stack.append(node)
                on_stack[node] = True
            recursed = False
            children = sorted(successors.get(node, []))
            for position in range(step, len(children)):
                child = children[position]
                if child not in index:
                    work[-1] = (node, position + 1)
                    work.append((child, 0))
                    recursed = True
                    break
                if on_stack.get(child):
                    low[node] = min(low[node], index[child])
            if recursed:
                continue
            if low[node] == index[node]:
                component = []
                while True:
                    member = stack.pop()
                    on_stack[member] = False
                    component.append(member)
                    if member == node:
                        break
                result.append(tuple(sorted(component)))
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])

    for node in sorted(nodes):
        if node not in index:
            strongconnect(node)
    return sorted(result)


def reachable_from(start, successors):
    seen = set()
    stack = [start]
    while stack:
        node = stack.pop()
        for child in sorted(successors.get(node, [])):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


# --------------------------------------------------------------------------
# The check
# --------------------------------------------------------------------------

def check(roadmap_obj, fanin_threshold=DEFAULT_FANIN_THRESHOLD):
    findings = []
    phases, phase_findings = load_phases(roadmap_obj)
    findings.extend(phase_findings)
    items, item_findings = load_items(roadmap_obj, phases)
    findings.extend(item_findings)

    phase_index = {pid: phases[pid]["order"] for pid in phases}
    phase_by_order = {}
    for pid in sorted(phases):
        phase_by_order.setdefault(phases[pid]["order"], pid)
    ordered_phase_ids = [phase_by_order[o] for o in sorted(phase_by_order)]

    def phase_at(index):
        """Phase id for an order index, or UNKNOWN. A roadmap with no usable
        phases must report UNKNOWN rather than crash or invent a phase - found
        by test_a_roadmap_with_items_but_no_phases_reports_unknown_not_pass."""
        if index is None or not (0 <= index < len(ordered_phase_ids)):
            return UNKNOWN
        return ordered_phase_ids[index]

    # ---- edges -----------------------------------------------------------
    successors = {item_id: [] for item_id in items}   # prerequisite -> dependents
    prereqs = {item_id: [] for item_id in items}
    unresolved = set()

    for item_id in sorted(items):
        for prerequisite in items[item_id]["prerequisites"]:
            if prerequisite == item_id:
                findings.append(finding(
                    ERROR, "self_dependency",
                    "Item '%s' lists itself as a prerequisite, so it can never "
                    "start." % item_id,
                    edge=(prerequisite, item_id),
                    repairs=[repair("remove_prerequisite", True,
                                    "Remove '%s' from its own prerequisites."
                                    % item_id,
                                    item_id=item_id, prerequisite_id=prerequisite)]))
                continue
            if prerequisite not in items:
                unresolved.add(item_id)
                findings.append(finding(
                    ERROR, "missing_prerequisite",
                    "Item '%s' requires '%s', which this roadmap does not "
                    "define. The reference is not treated as satisfied."
                    % (item_id, prerequisite),
                    edge=(prerequisite, item_id),
                    repairs=[
                        repair("define_item", False,
                               "Define '%s' as a roadmap item, if the dependency "
                               "is real." % prerequisite,
                               item_id=prerequisite),
                        repair("remove_prerequisite", True,
                               "Or remove the reference to '%s' from '%s', if it "
                               "was a typo or a dropped item."
                               % (prerequisite, item_id),
                               item_id=item_id, prerequisite_id=prerequisite),
                    ]))
                continue
            successors[prerequisite].append(item_id)
            prereqs[item_id].append(prerequisite)

    # ---- cycles ----------------------------------------------------------
    components = strongly_connected_components(sorted(items), successors)
    in_cycle = set()
    for component in components:
        if len(component) < 2:
            continue
        members = set(component)
        in_cycle |= members
        internal = sorted(
            (prerequisite, dependent)
            for prerequisite in component
            for dependent in successors[prerequisite]
            if dependent in members)
        group = "cycle:" + "|".join(component)
        cuts = [repair("remove_prerequisite", True,
                       "Remove prerequisite '%s' from '%s'." % (prerequisite, dependent),
                       item_id=dependent, prerequisite_id=prerequisite,
                       choice_group=group)
                for prerequisite, dependent in internal]
        findings.append(finding(
            ERROR, "dependency_cycle",
            "These %d items depend on each other in a loop, so none of them can "
            "start: %s. Every edge listed below is an equally valid cut - the "
            "checker will not choose which dependency is the wrong one."
            % (len(component), " -> ".join(component)),
            items=list(component), repairs=cuts,
            detail=[{"prerequisite_id": p, "dependent_id": d} for p, d in internal]))

    # ---- levels (the parallelism-preserving part) ------------------------
    # level(item) = 0 with no prerequisites, else 1 + max(level(prerequisite)).
    # Undefined when anything upstream is unresolved, unreadable or cyclic -
    # which is the honest answer, not zero.
    level = {}
    blocked = set(in_cycle)
    for item_id in items:
        if items[item_id]["prerequisites_unreadable"] or item_id in unresolved:
            blocked.add(item_id)

    def resolve_level(item_id, visiting):
        if item_id in level:
            return level[item_id]
        if item_id in blocked or item_id in visiting:
            return None
        visiting = visiting | {item_id}
        highest = -1
        for prerequisite in prereqs[item_id]:
            value = resolve_level(prerequisite, visiting)
            if value is None:
                blocked.add(item_id)
                return None
            highest = max(highest, value)
        level[item_id] = highest + 1
        return level[item_id]

    for item_id in sorted(items):
        resolve_level(item_id, frozenset())

    # ---- phase placement --------------------------------------------------
    assigned = {item_id: (phase_index[items[item_id]["phase"]]
                          if items[item_id]["phase"] in phase_index else None)
                for item_id in items}
    earliest = {}

    def resolve_earliest(item_id, visiting):
        """Earliest phase index this item could occupy given the whole chain."""
        if item_id in earliest:
            return earliest[item_id]
        if item_id in blocked or item_id in visiting:
            return None
        visiting = visiting | {item_id}
        highest = 0
        for prerequisite in prereqs[item_id]:
            upstream = resolve_earliest(prerequisite, visiting)
            if upstream is None or assigned[prerequisite] is None:
                return None
            highest = max(highest, upstream, assigned[prerequisite])
        earliest[item_id] = highest
        return highest

    for item_id in sorted(items):
        resolve_earliest(item_id, frozenset())

    for item_id in sorted(items):
        item = items[item_id]
        if item["phase"] is None:
            findings.append(finding(
                UNKNOWN_SEV, "unassigned_phase",
                "Item '%s' has no phase. It stays UNASSIGNED; the checker will "
                "not place it in the first phase or anywhere else." % item_id,
                items=[item_id],
                repairs=[repair("set_phase", False,
                                "A planner must assign a phase to '%s'." % item_id,
                                item_id=item_id)]))
            continue
        if item_id in in_cycle:
            continue
        if item_id in blocked or earliest.get(item_id) is None:
            if item["prerequisites_unreadable"] or item_id in unresolved:
                why = ("its own prerequisite list could not be fully read or "
                       "resolved")
            else:
                why = ("something it depends on is unassigned, unresolved or "
                       "caught in a loop")
            findings.append(finding(
                UNKNOWN_SEV, "feasibility_unknown",
                "Whether '%s' is placed consistently cannot be determined: %s. "
                "This is not the same as being placed correctly."
                % (item_id, why),
                items=[item_id]))
            continue

        floor = earliest[item_id]
        here = assigned[item_id]
        if here < floor:
            culprits = sorted(
                p for p in prereqs[item_id]
                if assigned[p] is not None and max(assigned[p], earliest.get(p, 0)) > here)
            target = phase_at(min(floor, len(ordered_phase_ids) - 1))
            for culprit in culprits:
                findings.append(finding(
                    ERROR, "phase_inversion",
                    "Item '%s' sits in '%s' but requires '%s', which cannot "
                    "complete before '%s'. No execution order satisfies this."
                    % (item_id, item["phase"], culprit,
                       phase_at(max(assigned[culprit],
                                    earliest.get(culprit, 0)))),
                    edge=(culprit, item_id),
                    repairs=[
                        repair("set_phase", True,
                               "Move '%s' to '%s' - the earliest phase consistent "
                               "with its prerequisites." % (item_id, target),
                               item_id=item_id, phase_id=target),
                        repair("set_phase", False,
                               "Or move '%s' to '%s' or earlier, if that work can "
                               "genuinely start sooner." % (culprit, item["phase"]),
                               item_id=culprit, phase_id=item["phase"]),
                    ]))
        elif here > floor:
            findings.append(finding(
                INFO, "schedule_slack",
                "Item '%s' is in '%s'; its prerequisites would allow '%s'. That "
                "is float, not an error - phases carry capacity and timing that "
                "the dependency graph does not know about."
                % (item_id, item["phase"], phase_at(floor)),
                items=[item_id]))

        for prerequisite in sorted(prereqs[item_id]):
            if assigned[prerequisite] == here:
                findings.append(finding(
                    OPEN_QUESTION, "same_phase_dependency",
                    "Item '%s' requires '%s' and both sit in '%s'. That can be "
                    "correct, but no phase boundary protects the ordering - "
                    "confirm the sequencing inside the phase."
                    % (item_id, prerequisite, item["phase"]),
                    edge=(prerequisite, item_id)))

    # ---- shared prerequisites and redundant edges -------------------------
    reach = {item_id: reachable_from(item_id, successors) for item_id in items}

    for item_id in sorted(items):
        dependents = sorted(successors[item_id])
        if len(dependents) >= fanin_threshold:
            findings.append(finding(
                OPEN_QUESTION, "shared_prerequisite",
                "Item '%s' is a prerequisite for %d other items (%s). It is a "
                "chokepoint: if it slips, all of them slip."
                % (item_id, len(dependents), ", ".join(dependents)),
                items=[item_id] + dependents))

    for item_id in sorted(items):
        if item_id in in_cycle:
            continue
        own = prereqs[item_id]
        for prerequisite in sorted(own):
            if prerequisite in in_cycle:
                continue
            implied_by = sorted(other for other in own
                                if other != prerequisite and other in reach[prerequisite])
            if implied_by:
                findings.append(finding(
                    INFO, "redundant_edge",
                    "Item '%s' lists '%s' directly, but already reaches it "
                    "through %s. The direct edge can be removed without changing "
                    "the plan." % (item_id, prerequisite, ", ".join(implied_by)),
                    edge=(prerequisite, item_id),
                    repairs=[repair("remove_prerequisite", False,
                                    "Optional tidy-up: remove '%s' from '%s'."
                                    % (prerequisite, item_id),
                                    item_id=item_id, prerequisite_id=prerequisite)]))

    # ---- parallel groups --------------------------------------------------
    # Items sharing a level have no dependency path between them in either
    # direction, so this is work that may genuinely proceed at the same time.
    parallel_groups = []
    for phase_id in ordered_phase_ids:
        by_level = {}
        for item_id in sorted(items):
            if items[item_id]["phase"] != phase_id or item_id not in level:
                continue
            by_level.setdefault(level[item_id], []).append(item_id)
        for depth in sorted(by_level):
            members = sorted(by_level[depth])
            parallel_groups.append({"phase_id": phase_id, "level": depth,
                                    "items": members, "size": len(members)})

    undetermined = sorted(item_id for item_id in items if item_id not in level)

    nodes = []
    for item_id in sorted(items):
        item = items[item_id]
        nodes.append({
            "item_id": item_id,
            "title": item["title"],
            "recommendation_ref": item["recommendation_ref"],
            "owner_group": item["owner_group"],
            "phase": item["phase"] if item["phase"] is not None else UNASSIGNED,
            "level": level.get(item_id, UNKNOWN),
            "earliest_feasible_phase": (phase_at(earliest[item_id])
                                        if item_id in earliest else UNKNOWN),
            "prerequisites": sorted(item["prerequisites"]),
            "dependents": sorted(successors[item_id]),
            "in_cycle": item_id in in_cycle,
        })

    edges = sorted(
        ({"prerequisite_id": prerequisite, "dependent_id": dependent}
         for prerequisite in items for dependent in successors[prerequisite]),
        key=lambda e: (e["prerequisite_id"], e["dependent_id"]))

    counts = {}
    for entry in findings:
        counts[entry["severity"]] = counts.get(entry["severity"], 0) + 1

    result = {
        "artifact": "UIOWA-115 roadmap dependency consistency check",
        "roadmap_id": roadmap_obj.get("roadmap_id", UNKNOWN),
        "fiction_notice": roadmap_obj.get(
            "fiction_notice",
            "Input not labelled. Treat every item as synthetic unless the source "
            "says otherwise; nothing here is a University roadmap."),
        "ordering_notice": (
            "This check reports dependency LEVELS, never a single execution "
            "order. Items sharing a level have no dependency path between them "
            "and may proceed in parallel. Serialising them would be a loss of "
            "real information, not a simplification."),
        "phases": [phases[pid] for pid in ordered_phase_ids],
        "nodes": nodes,
        "edges": edges,
        "parallel_groups": parallel_groups,
        "levels_undetermined": undetermined,
        "findings": sorted(findings, key=lambda f: (SEVERITY_ORDER[f["severity"]],
                                                    f["code"], f["message"])),
        "counts": {
            "items": len(items),
            "edges": len(edges),
            "errors": counts.get(ERROR, 0),
            "unknowns": counts.get(UNKNOWN_SEV, 0),
            "open_questions": counts.get(OPEN_QUESTION, 0),
            "info": counts.get(INFO, 0),
        },
    }
    result["content_digest"] = content_digest(result)
    return result


def content_digest(result):
    payload = {k: v for k, v in result.items() if k != "content_digest"}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Repair rehearsal
# --------------------------------------------------------------------------

def collect_mechanical_repairs(result):
    """Pick the repairs a tool may safely apply: at most one per choice group,
    chosen deterministically, and nothing marked as needing a planner."""
    chosen = []
    groups_taken = set()
    skipped_groups = {}
    for entry in result["findings"]:
        for item in entry.get("repairs", []):
            if not item["mechanical"]:
                continue
            group = item.get("choice_group")
            if group is not None:
                if group in groups_taken:
                    skipped_groups.setdefault(group, []).append(item)
                    continue
                groups_taken.add(group)
            chosen.append(item)
    return chosen, skipped_groups


def apply_repairs(roadmap_obj, repairs):
    """Return a NEW roadmap with the repairs applied. The input is never
    modified and never overwritten on disk - the checker reports, the planner
    decides."""
    proposed = copy.deepcopy(roadmap_obj)
    index = {}
    for entry in proposed.get("items", []):
        if isinstance(entry, dict) and _nonempty_str(entry.get("item_id")):
            index.setdefault(entry["item_id"], entry)
    applied = []
    for item in repairs:
        target = index.get(item.get("item_id"))
        if target is None:
            continue
        if item["op"] == "remove_prerequisite":
            existing = target.get("prerequisites")
            if isinstance(existing, list):
                target["prerequisites"] = [p for p in existing
                                           if p != item.get("prerequisite_id")]
                applied.append(item)
        elif item["op"] == "set_phase" and item.get("phase_id"):
            target["phase"] = item["phase_id"]
            applied.append(item)
    proposed["roadmap_id"] = "%s+proposed-repairs" % proposed.get("roadmap_id", UNKNOWN)
    proposed["proposal_notice"] = (
        "PROPOSAL, NOT A DECISION. This file is the original roadmap with the "
        "mechanically safe repairs applied so the result can be re-checked. "
        "Repairs that need a planner's judgement were NOT applied, and where "
        "several cuts were equally valid one was chosen deterministically. Read "
        "the rehearsal report before adopting any of it.")
    return proposed, applied


def rehearse(roadmap_obj, fanin_threshold=DEFAULT_FANIN_THRESHOLD):
    before = check(roadmap_obj, fanin_threshold)
    repairs, skipped = collect_mechanical_repairs(before)
    proposed, applied = apply_repairs(roadmap_obj, repairs)
    after = check(proposed, fanin_threshold)
    return {
        "before": before,
        "after": after,
        "proposed_roadmap": proposed,
        "applied_repairs": applied,
        "alternative_cuts_not_taken": sorted(
            (group for group in skipped), key=str),
        "needs_a_planner": [
            {"code": entry["code"], "message": entry["message"],
             "repairs": [r for r in entry.get("repairs", []) if not r["mechanical"]]}
            for entry in after["findings"]
            if entry["severity"] in (UNKNOWN_SEV,) or
            any(not r["mechanical"] for r in entry.get("repairs", []))],
    }


# --------------------------------------------------------------------------
# Renderers
# --------------------------------------------------------------------------

def _safe_node(item_id):
    return "N_" + re.sub(r"[^0-9A-Za-z]", "_", item_id)


def _phase_render_order(result):
    """Phases in their declared order, with UNASSIGNED last - so the picture
    reads left to right the way the roadmap does, not alphabetically."""
    order = [p["phase_id"] for p in result["phases"]]
    present = {node["phase"] for node in result["nodes"]}
    return [p for p in order if p in present] + sorted(present - set(order))


def render_dot(result):
    lines = ["digraph roadmap {", "  rankdir=LR;",
             '  node [shape=box, style=rounded, fontname="Helvetica"];',
             '  edge [fontname="Helvetica"];']
    by_phase = {}
    for node in result["nodes"]:
        by_phase.setdefault(node["phase"], []).append(node)
    for phase_id in _phase_render_order(result):
        lines.append('  subgraph "cluster_%s" {' % phase_id)
        lines.append('    label="%s";' % phase_id)
        for node in by_phase[phase_id]:
            style = ', color="red"' if node["in_cycle"] else ""
            lines.append('    %s [label="%s\\nlevel %s"%s];'
                         % (_safe_node(node["item_id"]), node["item_id"],
                            node["level"], style))
        lines.append("  }")
    cycle_edges = set()
    for entry in result["findings"]:
        if entry["code"] == "dependency_cycle":
            for edge in entry.get("detail", []):
                cycle_edges.add((edge["prerequisite_id"], edge["dependent_id"]))
    for edge in result["edges"]:
        pair = (edge["prerequisite_id"], edge["dependent_id"])
        style = ' [color="red"]' if pair in cycle_edges else ""
        lines.append("  %s -> %s%s;" % (_safe_node(pair[0]), _safe_node(pair[1]), style))
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_mermaid(result):
    """A Mermaid flowchart, which GitHub renders inline in Markdown - so the
    graph is visible without installing Graphviz."""
    lines = ["flowchart LR"]
    by_phase = {}
    for node in result["nodes"]:
        by_phase.setdefault(node["phase"], []).append(node)
    for phase_id in _phase_render_order(result):
        lines.append('  subgraph %s["%s"]' % (_safe_node(phase_id), phase_id))
        for node in by_phase[phase_id]:
            lines.append('    %s["%s<br/>level %s"]'
                         % (_safe_node(node["item_id"]), node["item_id"], node["level"]))
        lines.append("  end")
    for edge in result["edges"]:
        lines.append("  %s --> %s" % (_safe_node(edge["prerequisite_id"]),
                                      _safe_node(edge["dependent_id"])))
    return "\n".join(lines) + "\n"


def render_report(result, title="Roadmap dependency consistency check"):
    counts = result["counts"]
    lines = [
        "# %s" % title,
        "",
        "**Work order:** UIOWA-115  ",
        "**Roadmap:** `%s`  " % result["roadmap_id"],
        "**Content digest:** `%s`" % result["content_digest"],
        "",
        "> %s" % result["fiction_notice"],
        "",
        "> **On ordering.** %s" % result["ordering_notice"],
        "",
        "| items | edges | errors | unknown | open questions | info |",
        "|---|---|---|---|---|---|",
        "| %d | %d | **%d** | %d | %d | %d |"
        % (counts["items"], counts["edges"], counts["errors"], counts["unknowns"],
           counts["open_questions"], counts["info"]),
        "",
        "`errors` must reach zero. `unknown` means the roadmap does not contain "
        "enough information to decide - it is not a pass and it is not a "
        "failure, and no repair the checker can apply will clear it.",
        "",
    ]

    lines += ["## Work that can proceed in parallel", ""]
    concurrent = [g for g in result["parallel_groups"] if g["size"] > 1]
    if concurrent:
        lines += ["Items in the same row have no dependency path between them in "
                  "either direction. Scheduling them one after another would add "
                  "time the graph does not require.", "",
                  "| phase | level | items that may run at the same time |",
                  "|---|---|---|"]
        for group in concurrent:
            lines.append("| %s | %d | %s |" % (group["phase_id"], group["level"],
                                               ", ".join("`%s`" % i for i in group["items"])))
        lines.append("")
    else:
        lines += ["No two items in the same phase were found to be independent.", ""]
    if result["levels_undetermined"]:
        lines += ["Level could not be determined for %s - each depends on "
                  "something unresolved, unreadable or caught in a loop."
                  % ", ".join("`%s`" % i for i in result["levels_undetermined"]), ""]

    for severity, heading in ((ERROR, "Errors - exact edges to repair"),
                              (UNKNOWN_SEV, "Unknown - the roadmap does not say"),
                              (OPEN_QUESTION, "Open questions"),
                              (INFO, "Informational")):
        entries = [f for f in result["findings"] if f["severity"] == severity]
        if not entries:
            continue
        lines += ["## %s" % heading, ""]
        for entry in entries:
            edge = entry.get("edge")
            where = (" — edge `%s` → `%s`" % (edge["prerequisite_id"], edge["dependent_id"])
                     if edge else "")
            lines.append("**`%s`**%s" % (entry["code"], where))
            lines.append("")
            lines.append(entry["message"])
            lines.append("")
            for item in entry.get("repairs", []):
                mark = "applyable" if item["mechanical"] else "needs a planner"
                lines.append("- *(%s)* %s" % (mark, item["detail"]))
            if entry.get("repairs"):
                lines.append("")

    lines += ["## Dependency graph", "",
              "```mermaid", render_mermaid(result).rstrip(), "```", "",
              "A Graphviz version is written alongside this report as `graph.dot`.", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_rehearsal_report(rehearsal):
    before, after = rehearsal["before"], rehearsal["after"]
    lines = [
        "# Repair rehearsal",
        "",
        "> **This is a proposal, not a decision.** The mechanically safe repairs "
        "below were applied to a *copy* of the roadmap and the result re-checked. "
        "The original input file was not modified.",
        "",
        "| | errors | unknown | open questions | info |",
        "|---|---|---|---|---|",
        "| before | **%d** | %d | %d | %d |"
        % (before["counts"]["errors"], before["counts"]["unknowns"],
           before["counts"]["open_questions"], before["counts"]["info"]),
        "| after | **%d** | %d | %d | %d |"
        % (after["counts"]["errors"], after["counts"]["unknowns"],
           after["counts"]["open_questions"], after["counts"]["info"]),
        "",
        "## Repairs applied",
        "",
    ]
    for item in rehearsal["applied_repairs"]:
        lines.append("- `%s` — %s" % (item["op"], item["detail"]))
    lines += ["",
              "Where a loop offered several equally valid cuts, exactly one was "
              "taken, chosen deterministically so the rehearsal is reproducible. "
              "That choice is **not** a recommendation: the other cuts in the same "
              "loop are just as valid and a planner has to pick the dependency "
              "that is actually wrong.",
              "",
              "Any `remove_prerequisite` applied against an unresolvable reference "
              "removed a dependency the roadmap could not resolve. If one of those "
              "was a real dependency, defining the missing item is the correct "
              "repair instead.",
              "",
              "## Still requires a planner", ""]
    if rehearsal["needs_a_planner"]:
        for entry in rehearsal["needs_a_planner"]:
            lines.append("- **`%s`** %s" % (entry["code"], entry["message"]))
    else:
        lines.append("- Nothing.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _csv_cell(value):
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@"):
        return "'" + text
    return text


def write_findings_csv(path, result):
    header = ["severity", "code", "prerequisite_id", "dependent_id", "items",
              "message", "repair_ops", "repairs_needing_a_planner"]
    rows = []
    for entry in result["findings"]:
        edge = entry.get("edge", {})
        repairs = entry.get("repairs", [])
        rows.append([
            entry["severity"], entry["code"],
            edge.get("prerequisite_id", ""), edge.get("dependent_id", ""),
            "; ".join(entry.get("items", [])), entry["message"],
            "; ".join(sorted({r["op"] for r in repairs})),
            "; ".join(r["detail"] for r in repairs if not r["mechanical"]),
        ])
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([_csv_cell(cell) for cell in row])


def write_outputs(outdir, result):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "graph.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    with open(os.path.join(outdir, "graph.dot"), "w", encoding="utf-8") as handle:
        handle.write(render_dot(result))
    with open(os.path.join(outdir, "dependency_report.md"), "w", encoding="utf-8") as handle:
        handle.write(render_report(result))
    write_findings_csv(os.path.join(outdir, "findings.csv"), result)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _here(*parts):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--roadmap", default=_here("fixtures", "roadmap_consistent.json"))
    parser.add_argument("--outdir", default=_here("out"))
    parser.add_argument("--fanin-threshold", type=int, default=DEFAULT_FANIN_THRESHOLD)
    parser.add_argument("--rehearse-repairs", action="store_true",
                        help="Apply only the mechanically safe repairs to a COPY, "
                             "re-check it, and write the proposal beside the report.")
    args = parser.parse_args(argv)

    roadmap = load_json(args.roadmap)
    result = check(roadmap, args.fanin_threshold)
    write_outputs(args.outdir, result)

    counts = result["counts"]
    print("roadmap %s: %d items, %d edges" %
          (result["roadmap_id"], counts["items"], counts["edges"]))
    print("  errors=%d  unknown=%d  open_questions=%d  info=%d"
          % (counts["errors"], counts["unknowns"], counts["open_questions"],
             counts["info"]))
    for group in result["parallel_groups"]:
        if group["size"] > 1:
            print("  parallel in %-8s level %d: %s"
                  % (group["phase_id"], group["level"], ", ".join(group["items"])))
    for entry in result["findings"]:
        if entry["severity"] != ERROR:
            continue
        edge = entry.get("edge")
        where = ("%s -> %s" % (edge["prerequisite_id"], edge["dependent_id"])
                 if edge else ", ".join(entry.get("items", [])))
        print("  ERROR %-22s %s" % (entry["code"], where))
    print("  digest %s" % result["content_digest"])

    if args.rehearse_repairs:
        rehearsal = rehearse(roadmap, args.fanin_threshold)
        with open(os.path.join(args.outdir, "proposed_roadmap.json"), "w",
                  encoding="utf-8") as handle:
            json.dump(rehearsal["proposed_roadmap"], handle, indent=2,
                      ensure_ascii=False)
            handle.write("\n")
        with open(os.path.join(args.outdir, "rehearsal_report.md"), "w",
                  encoding="utf-8") as handle:
            handle.write(render_rehearsal_report(rehearsal))
        print("  rehearsal: errors %d -> %d, unknown %d -> %d (a planner must "
              "clear the rest)"
              % (rehearsal["before"]["counts"]["errors"],
                 rehearsal["after"]["counts"]["errors"],
                 rehearsal["before"]["counts"]["unknowns"],
                 rehearsal["after"]["counts"]["unknowns"]))
    print("  outputs in %s" % args.outdir)
    return 1 if counts["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
