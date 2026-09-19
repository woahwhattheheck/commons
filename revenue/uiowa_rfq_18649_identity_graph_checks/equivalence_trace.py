#!/usr/bin/env python3
"""Explain a canonical identity-map report using its retained equivalence decisions.

This is an offline report consumer, not another identity mapper. It assigns no
IDs, replaces no records, and makes no claim about source truth or approval.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from copy import deepcopy
import hashlib
import html
import json
from pathlib import Path
from typing import Any

SCHEMA = "uiowa.identity-map.v1"
FIELDS = ("namespace", "kind", "id", "revision")
MAX_INPUT_BYTES = 16 * 1024 * 1024


class TraceError(ValueError):
    """The supplied report cannot support a faithful equivalence explanation."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def snapshot_digest(report: dict) -> str:
    body = {k: v for k, v in report.items() if k != "snapshot_sha256"}
    return hashlib.sha256((SCHEMA + "/report\0" + canonical(body)).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    def pairs(items):
        obj = {}
        for key, val in items:
            if key in obj:
                raise TraceError(f"duplicate JSON key: {key}")
            obj[key] = val
        return obj

    def bad_constant(value):
        raise TraceError(f"non-finite JSON constant: {value}")

    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise TraceError("report exceeds the 16 MiB reader limit")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=bad_constant)


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise TraceError(f"{label} must be nonempty text")
    return value


def _key(value):
    if not isinstance(value, dict):
        raise TraceError("occurrence selector must be an object")
    return tuple(_text(value.get(k), k) for k in FIELDS)


def _locators(value):
    if not isinstance(value, list) or not value:
        raise TraceError("missing retained provenance locators")
    for item in value:
        _text(item, "locator")


class ReportGraph:
    """Audit a report's graph and retain the exact source representation per node.

    Snapshot integrity is self-consistency only. No signature, independent root,
    assessment validity, or authenticity follows from a matching checksum.
    """

    def __init__(self, report: dict):
        try:
            self._build(report)
        except TraceError:
            raise
        except (KeyError, TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as exc:
            raise TraceError(f"malformed identity-map report: {exc}") from exc

    def _build(self, report):
        if not isinstance(report, dict) or report.get("schema") != SCHEMA:
            raise TraceError("expected uiowa.identity-map.v1 report")
        if report.get("assessment_authority") is not False:
            raise TraceError("report must retain assessment_authority=false")
        if report.get("snapshot_sha256") != snapshot_digest(report):
            raise TraceError("report snapshot digest mismatch")
        self.snapshot = report["snapshot_sha256"]
        self.nodes, by_key = {}, {}
        for node in report["records"]:
            oid = _text(node["occurrence_id"], "occurrence_id")
            original = node["original"]
            ident = _key(original)
            if oid in self.nodes or ident in by_key:
                raise TraceError("duplicate occurrence identity in report")
            if type(original.get("synthetic")) is not bool:
                raise TraceError("synthetic scope must be an explicit boolean")
            _locators(original["source_locators"])
            self.nodes[oid], by_key[ident] = deepcopy(node), oid
        self.edges = defaultdict(list)
        self.decisions, self.negatives = {}, []
        for decision in report["equivalences"]:
            did = _text(decision["decision_id"], "decision_id")
            if did in self.decisions:
                raise TraceError("duplicate equivalence decision ID")
            _text(decision["reason"], "equivalence reason")
            _locators(decision["evidence_locators"])
            left, right = _key(decision["left"]), _key(decision["right"])
            if set(decision["left"]) != set(FIELDS) or set(decision["right"]) != set(FIELDS):
                raise TraceError("decision endpoints must use exact qualified selectors")
            if left not in by_key or right not in by_key:
                raise TraceError("decision endpoint is absent from retained records")
            a, b = by_key[left], by_key[right]
            if left[1] != right[1]:
                raise TraceError("decision crosses entity kinds")
            if self.nodes[a]["original"]["synthetic"] != self.nodes[b]["original"]["synthetic"]:
                raise TraceError("decision crosses synthetic scopes")
            self.decisions[did] = deepcopy(decision)
            if decision["relation"] == "same_entity":
                self.edges[a].append((did, b))
                self.edges[b].append((did, a))
            elif decision["relation"] == "different_entity":
                self.negatives.append((did, a, b))
            else:
                raise TraceError("unsupported equivalence relation")
        # Independent breadth-first connected components; no mapper internals or
        # mapper-generated canonical IDs are used as the connectivity oracle.
        self.components, expected = {}, set()
        for start in sorted(self.nodes):
            if start in self.components:
                continue
            queue, members = deque([start]), {start}
            while queue:
                for _, nxt in self.edges[queue.popleft()]:
                    if nxt not in members:
                        members.add(nxt)
                        queue.append(nxt)
            component = frozenset(members)
            expected.add(component)
            for oid in component:
                self.components[oid] = component
        for did, a, b in self.negatives:
            if self.components[a] == self.components[b]:
                raise TraceError(f"negative decision contradicts positive closure: {did}")
        actual, covered, group_ids = set(), set(), set()
        for group in report["equivalence_groups"]:
            gid = _text(group["group_id"], "equivalence group ID")
            members = group["members"]
            if not isinstance(members, list) or not members or len(set(members)) != len(members):
                raise TraceError("empty or duplicate group membership")
            membership = frozenset(members)
            if gid in group_ids or covered.intersection(membership):
                raise TraceError("overlapping or duplicate equivalence groups")
            if not membership.issubset(self.nodes):
                raise TraceError("equivalence group contains an absent occurrence")
            for oid in membership:
                if self.nodes[oid]["equivalence_group"] != gid:
                    raise TraceError("record and group membership disagree")
            actual.add(membership)
            covered.update(membership)
            group_ids.add(gid)
        if covered != set(self.nodes) or actual != expected:
            raise TraceError("equivalence groups do not match retained decision closure")
        for oid in self.edges:
            self.edges[oid].sort()

    def explain(self, left: str, right: str) -> dict:
        """Give one deterministic shortest witness; retain other supporting edges.

        Absence of a path is not evidence that the underlying entities differ.
        A revision-equivalence declaration never chooses one source revision.
        """
        if left not in self.nodes or right not in self.nodes:
            raise TraceError("requested occurrence is absent from this report")
        result = {"schema": "uiowa.equivalence-trace.v1", "assessment_authority": False,
                  "snapshot_sha256": self.snapshot, "left": left, "right": right,
                  "status": "no_equivalence_path", "steps": [], "occurrences": [],
                  "supporting_decisions": [], "negative_constraints": [],
                  "interpretation": "Operator declarations only; not source truth or approval. "
                                    "No path does not establish different underlying entities."}
        ca, cb = self.components[left], self.components[right]
        if ca != cb:
            result["occurrences"] = [deepcopy(self.nodes[left]), deepcopy(self.nodes[right])]
            for did, a, b in sorted(self.negatives):
                if (a in ca and b in cb) or (a in cb and b in ca):
                    result["negative_constraints"].append(deepcopy(self.decisions[did]))
            return result
        result["status"] = "same_occurrence" if left == right else "declared_equivalent"
        queue, previous = deque([left]), {left: None}
        while queue and right not in previous:
            current = queue.popleft()
            for did, nxt in self.edges[current]:
                if nxt not in previous:
                    previous[nxt] = (current, did)
                    queue.append(nxt)
        path, current = [], right
        while previous[current] is not None:
            parent, did = previous[current]
            path.append({"from_occurrence_id": parent, "to_occurrence_id": current,
                         "decision": deepcopy(self.decisions[did])})
            current = parent
        result["steps"] = list(reversed(path))
        path_ids = [left] + [step["to_occurrence_id"] for step in result["steps"]]
        result["occurrences"] = [deepcopy(self.nodes[oid]) for oid in path_ids]
        support = {did for oid in ca for did, _ in self.edges[oid]}
        result["supporting_decisions"] = [deepcopy(self.decisions[did]) for did in sorted(support)]
        return result


def render_markdown(trace: dict) -> str:
    def safe(value):
        escaped = html.escape(str(value)).replace("\n", " ")
        return "".join(f"&#{ord(c)};" if c in "\\`*{}[]()#+-.!_|~" else c for c in escaped)
    out = ["# Equivalence justification trail", "", f"Status: **{safe(trace['status'])}**", "",
           trace["interpretation"], "", "## Exact retained source representations", "",
           "| Namespace | Kind | Original ID | Revision | Synthetic | Locators |",
           "|---|---|---|---|---|---|"]
    for node in trace["occurrences"]:
        record = node["original"]
        values = [record[k] for k in FIELDS] + [record["synthetic"], canonical(record["source_locators"])]
        out.append("| " + " | ".join(safe(v) for v in values) + " |")
    out += ["", "## One shortest declaration path", ""]
    for n, step in enumerate(trace["steps"], 1):
        d = step["decision"]
        out.append(f"{n}. {safe(d['decision_id'])}: {safe(d['reason'])}; locators: {safe(canonical(d['evidence_locators']))}")
    if not trace["steps"]:
        out.append("No declaration steps are used for this result.")
    out += ["", "## Retained negative constraints", ""]
    for d in trace["negative_constraints"]:
        out.append(f"- {safe(d['decision_id'])}: {safe(d['reason'])}; locators: {safe(canonical(d['evidence_locators']))}")
    if not trace["negative_constraints"]:
        out.append("No negative declaration connects these components.")
    out += ["", "All positive declarations in the component are retained in JSON, including redundant cycles.",
            "Negative constraints (when present) are retained separately, not traversed as positive links.", "",
            f"Report snapshot: `{trace['snapshot_sha256']}` (self-consistency, not independent authenticity).", ""]
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("report", type=Path)
    p.add_argument("left", help="exact occurrence_id from the report")
    p.add_argument("right", help="exact occurrence_id from the report")
    p.add_argument("--markdown", action="store_true")
    args = p.parse_args(argv)
    try:
        result = ReportGraph(load_json(args.report)).explain(args.left, args.right)
        print(render_markdown(result) if args.markdown else json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (TraceError, ValueError, OSError, UnicodeError, RecursionError) as exc:
        p.exit(2, f"equivalence-trace: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
