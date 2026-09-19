#!/usr/bin/env python3
"""Execute equivalence/provenance challenges against the actual v1 identity mapper.

No network or provider actions. --mapper explicitly selects reviewed Python code;
it is imported and executed. An optional Git-blob pin checks its exact bytes.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
from itertools import combinations, permutations
import json
from pathlib import Path
import sys

try:
    from .equivalence_trace import ReportGraph, TraceError, canonical
except ImportError:
    from equivalence_trace import ReportGraph, TraceError, canonical

SCHEMA = "uiowa.identity-map.v1"
FIELDS = ("namespace", "kind", "id", "revision")


def record(label, *, namespace=None, kind="source", revision="v1", synthetic=True):
    return {"namespace": namespace or f"synthetic-{label}", "kind": kind, "id": "EVID-01",
            "revision": revision, "synthetic": synthetic,
            "source_locators": [f"synthetic://graph/{label}/{revision}#section=1"],
            "payload": {"case_label": label, "excerpt": f"Fictional evidence for {label}.",
                        "unmeasured": None}, "review_notes": {"interpretation": "synthetic fixture"}}


def select(row):
    return {field: row[field] for field in FIELDS}


def decision(did, left, right, relation="same_entity"):
    return {"decision_id": did, "left": select(left), "right": select(right),
            "relation": relation, "reason": f"Fictional crosswalk declaration {did}.",
            "evidence_locators": [f"synthetic://crosswalk/{did}#decision"],
            "review_record": {"owner_role": "Synthetic evidence reviewer", "note": None}}


def packet(records, decisions=(), links=()):
    return {"schema": SCHEMA, "records": deepcopy(records), "equivalences": deepcopy(list(decisions)),
            "links": deepcopy(list(links)), "case_notice": "SYNTHETIC — not University findings"}


def _case(name, document, groups=None, error=False, link_statuses=None):
    return {"name": name, "document": document, "groups": groups, "error": error,
            "link_statuses": link_statuses or {}}


def cases():
    a, b, c, d = [record(x) for x in "ABCD"]
    ab, bc, ca = decision("AB", a, b), decision("BC", b, c), decision("CA", c, a)
    result = [
        _case("same_spelling_is_not_equivalence", packet([a, b]), [["A"], ["B"]]),
        _case("explicit_pair", packet([a, b], [ab]), [["A", "B"]]),
        _case("transitive_chain", packet([a, b, c], [ab, bc]), [["A", "B", "C"]]),
        _case("redundant_symmetric_cycle", packet([a, b, c], [ab, bc, ca]), [["A", "B", "C"]]),
        _case("two_reasons_same_pair", packet([a, b], [ab, decision("AB-2", a, b)]), [["A", "B"]]),
        _case("self_equivalence", packet([a], [decision("SELF", a, a)]), [["A"]]),
        _case("disconnected_components", packet([a, b, c, d], [ab, decision("CD", c, d)]),
              [["A", "B"], ["C", "D"]]),
        _case("negative_constraint_does_not_union", packet([a, b], [decision("NOT-AB", a, b, "different_entity")]),
              [["A"], ["B"]]),
        _case("positive_component_with_external_negative", packet([a, b, c],
              [ab, decision("NOT-BC", b, c, "different_entity")]), [["A", "B"], ["C"]]),
    ]
    contrary = decision("NOT-AC", a, c, "different_entity")
    for n, order in enumerate(permutations([ab, bc, contrary])):
        result.append(_case(f"negative_after_full_closure_order_{n}", packet([a, b, c], order), error=True))
    result += [
        _case("negative_self", packet([a], [decision("NOT-SELF", a, a, "different_entity")]), error=True),
        _case("missing_endpoint", packet([a], [ab]), error=True),
        _case("duplicate_decision_id", packet([a, b], [ab, ab]), error=True),
    ]
    for kind in ["observation", "finding", "recommendation", "service"]:
        other = record("B", kind=kind)
        result.append(_case(f"no_source_to_{kind}_union", packet([a, other], [decision("MIX", a, other)]), error=True))
    other = record("B", synthetic=False)
    result.append(_case("no_synthetic_actual_union", packet([a, other], [decision("MIX", a, other)]), error=True))
    for field, value in [("reason", ""), ("evidence_locators", []), ("relation", "redirect")]:
        bad = deepcopy(ab)
        bad[field] = value
        result.append(_case(f"invalid_decision_{field}", packet([a, b], [bad]), error=True))
    bad = deepcopy(ab)
    bad["left"].pop("revision")
    result.append(_case("decision_cannot_guess_revision", packet([a, b], [bad]), error=True))
    a2 = record("A2", namespace=a["namespace"], revision="v2")
    link = {"link_id": "version-select", "relation": "cites",
            "from": select(b), "to": {"namespace": a["namespace"], "kind": "source", "id": a["id"]}}
    result += [
        _case("versions_stay_separate_without_decision", packet([a, a2]), [["A"], ["A2"]]),
        _case("explicit_revision_equivalence_retains_both", packet([a, a2], [decision("VERSIONS", a, a2)]), [["A", "A2"]]),
        _case("equivalence_does_not_pick_revision", packet([a, a2, b], [decision("VERSIONS", a, a2)], [link]),
              [["A", "A2"], ["B"]], link_statuses={"version-select": ("resolved", "ambiguous", "unresolved")}),
    ]
    exact = deepcopy(link)
    exact["to"] = select(a)
    result.append(_case("qualified_v1_citation_survives_equivalence", packet([a, a2, b],
                        [decision("VERSIONS", a, a2)], [exact]), [["A", "A2"], ["B"]],
                        link_statuses={"version-select": ("resolved", "resolved", "resolved")}))
    proposed = packet([a, b])
    proposed["proposed_equivalences"] = [{**ab, "status": "pending"}]
    result.append(_case("proposal_extension_is_not_active_equivalence", proposed, [["A"], ["B"]]))
    return result


def _groups(report):
    labels = {row["occurrence_id"]: row["original"]["payload"]["case_label"] for row in report["records"]}
    return {frozenset(labels[oid] for oid in group["members"]) for group in report["equivalence_groups"]}


def check_case(mapper, case):
    """Unexpected exceptions are failures, never substitutes for required rejection."""
    document = deepcopy(case["document"])
    before = canonical(document)
    try:
        report = mapper.reconcile(document)
    except mapper.MappingError:
        if not case["error"]:
            raise AssertionError("valid equivalence graph was rejected")
        if canonical(document) != before:
            raise AssertionError("rejection mutated the original input")
        return
    if case["error"]:
        raise AssertionError("invalid equivalence declaration was accepted")
    if canonical(document) != before:
        raise AssertionError("mapping mutated the original input")
    graph = ReportGraph(report)
    expected = {frozenset(group) for group in case["groups"]}
    if _groups(report) != expected:
        raise AssertionError("observed equivalence groups differ from the hand-worked expectation")
    originals = {tuple(row[k] for k in FIELDS): row for row in case["document"]["records"]}
    if len(report["records"]) != len(originals):
        raise AssertionError("source representations disappeared or were invented")
    for row in report["records"]:
        original = row["original"]
        if canonical(original) != canonical(originals[tuple(original[k] for k in FIELDS)]):
            raise AssertionError("source revision, original payload or provenance changed during grouping")
    if canonical(report["equivalences"]) != canonical(sorted(case["document"]["equivalences"], key=lambda row: row["decision_id"])):
        raise AssertionError("decision reason, locator or extension was lost")
    expected_links = {row["link_id"]: row for row in case["document"]["links"]}
    if len(report["links"]) != len(expected_links) or {row["link_id"] for row in report["links"]} != set(expected_links):
        raise AssertionError("reference checks cannot pass after dropping or inventing links")
    for row in report["links"]:
        if canonical(row["original"]) != canonical(expected_links[row["link_id"]]):
            raise AssertionError("the requested reference was changed before resolution")
        expectation = case["link_statuses"].get(row["link_id"])
        if expectation and (row["from"]["status"], row["to"]["status"], row["status"]) != expectation:
            raise AssertionError("equivalence changed revision-specific reference resolution")
        for side in ("from", "to"):
            resolution = row[side]
            if resolution["status"] == "resolved":
                target = graph.nodes[resolution["resolved_id"]]["original"]
                if any(target[field] != value for field, value in row["original"][side].items()):
                    raise AssertionError("resolved citation was substituted with another representation")
    # Walk every ordered pair in small cases; every returned step carries the
    # original declaration and each intermediate node retains its exact version.
    for left in graph.nodes:
        for right in graph.nodes:
            witness = graph.explain(left, right)
            connected = graph.components[left] == graph.components[right]
            if connected != (witness["status"] in {"same_occurrence", "declared_equivalent"}):
                raise AssertionError("explanation disagrees with graph connectivity")
            cursor = left
            for step in witness["steps"]:
                if step["from_occurrence_id"] != cursor:
                    raise AssertionError("broken witness path")
                cursor = step["to_occurrence_id"]
            if connected and cursor != right:
                raise AssertionError("witness path does not reach the requested revision")


def run_suite(mapper, exhaustive=True):
    outcomes = []
    for case in cases():
        try:
            check_case(mapper, case)
            outcomes.append({"case": case["name"], "status": "PASS"})
        except Exception as exc:  # A test harness must record all target failures, not hide crashes.
            outcomes.append({"case": case["name"], "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    graph_count = 0
    if exhaustive:
        # Every undirected graph on five vertices, not a sample from a random seed.
        vertices = [record(label) for label in "ABCDE"]
        pairs = list(combinations(range(5), 2))
        try:
            for mask in range(1 << len(pairs)):
                links, adjacent = [], {i: set() for i in range(5)}
                for bit, (a, b) in enumerate(pairs):
                    if mask & (1 << bit):
                        links.append(decision(f"D-{a}-{b}", vertices[a], vertices[b]))
                        adjacent[a].add(b)
                        adjacent[b].add(a)
                unseen, groups = set(range(5)), []
                while unseen:
                    pending, found = [min(unseen)], set()
                    while pending:
                        current = pending.pop()
                        if current not in found:
                            found.add(current)
                            pending.extend(adjacent[current] - found)
                    unseen -= found
                    groups.append(["ABCDE"[i] for i in sorted(found)])
                check_case(mapper, _case(f"graph-{mask}", packet(vertices, links), groups))
                graph_count += 1
            outcomes.append({"case": "all_1024_five_vertex_positive_graphs", "status": "PASS"})
        except Exception as exc:
            outcomes.append({"case": "all_1024_five_vertex_positive_graphs", "status": "FAIL",
                             "error": f"graph {graph_count}: {type(exc).__name__}: {exc}"})
    passed = sum(row["status"] == "PASS" for row in outcomes)
    return {"schema": "uiowa.identity-graph-checks.v1", "assessment_authority": False,
            "summary": {"checks": len(outcomes), "passed": passed, "failed": len(outcomes) - passed,
                        "exhaustive_graphs_executed": graph_count}, "checks": outcomes}


def load_mapper(path: Path, expected_blob=None):
    source = path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
    if expected_blob is not None and blob != expected_blob:
        raise ValueError(f"mapper Git blob mismatch: expected {expected_blob}; observed {blob}")
    # Compile the same bytes that were hashed; do not re-open a moving file via
    # importlib's execution loader and mistake it for the verified source.
    spec = importlib.util.spec_from_loader("uiowa_graph_review_target", loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    exec(compile(source, str(path), "exec"), module.__dict__)
    if module.SCHEMA != SCHEMA or not callable(module.reconcile):
        raise ValueError("target does not expose the published v1 mapper interface")
    if not isinstance(module.MappingError, type) or not issubclass(module.MappingError, ValueError):
        raise ValueError("target must expose MappingError as a ValueError subclass")
    return module, {"git_blob_sha1": blob, "sha256": hashlib.sha256(source).hexdigest(), "bytes": len(source)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapper", type=Path, default=Path(__file__).resolve().parents[1] /
                        "uiowa_rfq_18649_identity_map" / "identity_map.py")
    parser.add_argument("--expected-git-blob")
    parser.add_argument("--quick", action="store_true", help="omit exhaustive graph enumeration")
    parser.add_argument("--out", type=Path, help="new receipt file; never overwrite an existing file")
    args = parser.parse_args(argv)
    try:
        mapper, source = load_mapper(args.mapper, args.expected_git_blob)
        result = run_suite(mapper, exhaustive=not args.quick)
        result["mapper_source"] = source
        result["python"] = {"version": sys.version.split()[0], "optimization": sys.flags.optimize}
        body = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(body)
        else:
            print(body, end="")
        return 1 if result["summary"]["failed"] else 0
    except (OSError, ValueError, ImportError, AttributeError, SyntaxError) as exc:
        parser.exit(2, f"identity-graph-checks: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
