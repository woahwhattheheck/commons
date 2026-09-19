#!/usr/bin/env python3
"""Generate a synthetic, source-bound equivalence explanation using the real mapper."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from . import graph_cases as gc
    from .equivalence_trace import ReportGraph, render_markdown
except ImportError:
    import graph_cases as gc
    from equivalence_trace import ReportGraph, render_markdown


def build_example(mapper):
    a, b, c, d = [gc.record(x) for x in "ABCD"]
    a2 = gc.record("A-v2", namespace=a["namespace"], revision="v2")
    decisions = [gc.decision("AB", a, b), gc.decision("BC", b, c), gc.decision("CA", c, a),
                 gc.decision("NOT-CD", c, d, "different_entity")]
    links = [{"link_id": "exact-revision", "relation": "cites", "from": gc.select(c), "to": gc.select(a)},
             {"link_id": "unspecified-revision", "relation": "cites", "from": gc.select(c),
              "to": {"namespace": a["namespace"], "kind": "source", "id": a["id"]}}]
    packet = gc.packet([a, a2, b, c, d], decisions, links)
    report = mapper.reconcile(packet)
    graph = ReportGraph(report)
    ids = {node["original"]["payload"]["case_label"]: oid for oid, node in graph.nodes.items()}
    trace = graph.explain(ids["A"], ids["C"])
    negative = graph.explain(ids["A"], ids["D"])
    return packet, report, trace, negative


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapper", type=Path, default=Path(__file__).resolve().parents[1] /
                        "uiowa_rfq_18649_identity_map" / "identity_map.py")
    parser.add_argument("--expected-git-blob")
    parser.add_argument("--out", type=Path, required=True, help="new directory; existing paths are not overwritten")
    args = parser.parse_args(argv)
    try:
        mapper, source = gc.load_mapper(args.mapper, args.expected_git_blob)
        packet, report, trace, negative = build_example(mapper)
        values = {"packet.json": packet, "report.json": report, "trace.json": trace,
                  "negative-trace.json": negative}
        files = {name: json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
                 for name, value in values.items()}
        files["trace.md"] = render_markdown(trace)
        files["negative-trace.md"] = render_markdown(negative)
        manifest = {"schema": "uiowa.identity-graph-example.v1", "synthetic": True,
                    "assessment_authority": False, "mapper_source": source,
                    "report_snapshot_sha256": report["snapshot_sha256"],
                    "files": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                              for name, text in sorted(files.items())}}
        args.out.mkdir()
        for name, text in sorted(files.items()):
            with (args.out / name).open("x", encoding="utf-8", newline="\n") as output:
                output.write(text)
        # The manifest is a completion marker, not a promise of transactional
        # filesystem semantics. An interrupted partial directory is left intact.
        with (args.out / "manifest.json").open("x", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"summary": report["summary"], "left": trace["left"], "right": trace["right"],
                          "trace_steps": len(trace["steps"]), "supporting_decisions": len(trace["supporting_decisions"]),
                          "negative_constraints": len(negative["negative_constraints"]),
                          "mapper_source": source}, sort_keys=True))
        return 0
    except (OSError, ValueError, ImportError, AttributeError, SyntaxError) as exc:
        parser.exit(2, f"identity-graph-example: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
