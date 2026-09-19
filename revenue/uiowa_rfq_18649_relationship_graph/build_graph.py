#!/usr/bin/env python3
"""UIOWA-104 portable finding-to-source relationship graph."""
from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE_DIR = Path("revenue/uiowa_rfq_18649_traceability_rehearsal")

def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

def split_ids(value: str | None) -> list[str]:
    return [x.strip() for x in (value or "").replace(",", ";").split(";") if x.strip()]

def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value

def build_graph(
    repo: Path = REPO,
    annotations_path: Path | None = None,
    demo_links_path: Path | None = None,
) -> dict[str, Any]:
    root = repo / SOURCE_DIR
    evidence = load_csv(root / "evidence.csv")
    findings = load_csv(root / "findings.csv")
    recommendations = load_csv(root / "recommendations.csv")
    trace = load_csv(root / "trace-map.csv")
    annotations = load_json(annotations_path)
    demo = load_json(demo_links_path)

    ev_by_id = {r["evidence_id"]: r for r in evidence}
    f_by_id = {r["finding_id"]: r for r in findings}
    r_by_id = {r["recommendation_id"]: r for r in recommendations}
    if len(ev_by_id) != len(evidence) or len(f_by_id) != len(findings) or len(r_by_id) != len(recommendations):
        raise ValueError("duplicate canonical identifier")

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    def add_node(node: dict[str, Any]) -> None:
        node_id = node["id"]
        if node_id in nodes:
            raise ValueError(f"duplicate graph node {node_id}")
        nodes[node_id] = node

    def add_edge(source: str, target: str, relation: str, state: str = "supported") -> None:
        edges.append({"from": source, "to": target, "relation": relation, "state": state})

    report_by_finding: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in trace:
        for fid in split_ids(row["finding_ids"]):
            report_by_finding[fid].append({
                "statement_id": row["statement_id"],
                "report_location": row["report_location"],
                "statement_summary": row["statement_summary"],
            })

    for row in evidence:
        eid = row["evidence_id"]
        oid = "OBS:" + eid
        evid = "EV:" + eid
        sid = "SRC:" + eid
        add_node({
            "id": oid,
            "type": "observation",
            "label": eid + " observation",
            "service": row["service"],
            "state": row["evidence_state"],
            "details": {
                "observation": row["observation"],
                "evidence_state": row["evidence_state"],
            },
        })
        add_node({
            "id": evid,
            "type": "evidence",
            "label": eid,
            "service": row["service"],
            "state": row["evidence_state"],
            "details": {
                "source_type": row["source_type"],
                "source_name": row["source_name"],
                "locator": row["locator"],
                "evidence_state": row["evidence_state"],
            },
        })
        add_node({
            "id": sid,
            "type": "source",
            "label": row["source_name"],
            "service": row["service"],
            "state": "locator",
            "details": {
                "source_name": row["source_name"],
                "locator": row["locator"],
                "source_type": row["source_type"],
            },
        })
        add_edge(oid, evid, "observation_to_evidence")
        add_edge(evid, sid, "evidence_to_source")

    role_map = annotations.get("finding_evidence_roles", {})
    for row in findings:
        fid = row["finding_id"]
        node_id = "FND:" + fid
        add_node({
            "id": node_id,
            "type": "finding",
            "label": fid + " — " + row["title"],
            "service": row["service"],
            "state": row["type"],
            "details": {
                "statement": row["statement"],
                "confidence": row["confidence"],
                "limitation": row["limitation"],
                "evidence_ids": split_ids(row["evidence_ids"]),
                "report_references": sorted(report_by_finding.get(fid, []), key=lambda x: x["statement_id"]),
            },
        })
        for eid in split_ids(row["evidence_ids"]):
            if eid not in ev_by_id:
                add_node({
                    "id": "MISSING:" + eid,
                    "type": "missing",
                    "label": "Missing evidence " + eid,
                    "service": row["service"],
                    "state": "unsupported_reference",
                    "details": {"missing_id": eid},
                })
                add_edge(node_id, "MISSING:" + eid, "finding_to_observation", "unsupported")
                continue
            role = role_map.get(fid, {}).get(eid, "supporting")
            if role not in {"supporting", "counter_evidence", "context"}:
                raise ValueError(f"invalid evidence role {role!r} for {fid}/{eid}")
            add_edge(node_id, "OBS:" + eid, "finding_to_observation", role)

    for row in recommendations:
        rid = row["recommendation_id"]
        node_id = "REC:" + rid
        add_node({
            "id": node_id,
            "type": "recommendation",
            "label": rid + " — " + row["title"],
            "service": "CROSS",
            "state": "recommendation",
            "details": {
                "action": row["action"],
                "expected_outcome": row["expected_outcome"],
                "effort": row["effort"],
                "dependency": row["dependency"],
                "linked_findings": split_ids(row["linked_findings"]),
            },
        })
        for fid in split_ids(row["linked_findings"]):
            target = "FND:" + fid
            if fid not in f_by_id:
                target = "MISSING:" + fid
                if target not in nodes:
                    add_node({
                        "id": target,
                        "type": "missing",
                        "label": "Missing finding " + fid,
                        "service": "CROSS",
                        "state": "unsupported_reference",
                        "details": {"missing_id": fid},
                    })
                add_edge(node_id, target, "recommendation_to_finding", "unsupported")
            else:
                add_edge(node_id, target, "recommendation_to_finding")

    for link in demo.get("links", []):
        if not isinstance(link, dict):
            raise ValueError("demo link must be object")
        source_id = str(link.get("from") or "")
        target_id = str(link.get("to") or "")
        if not source_id or not target_id:
            raise ValueError("demo link requires from/to")
        if source_id not in nodes:
            add_node({
                "id": source_id,
                "type": str(link.get("from_type") or "recommendation"),
                "label": str(link.get("from_label") or source_id),
                "service": "DEMO",
                "state": "demo_only",
                "details": {
                    "demo_only": True,
                    "note": str(link.get("note") or "Deliberately unsupported demonstration link."),
                },
            })
        if target_id not in nodes:
            add_node({
                "id": target_id,
                "type": "missing",
                "label": str(link.get("to_label") or ("Missing target " + target_id)),
                "service": "DEMO",
                "state": "unsupported_reference",
                "details": {"demo_only": True, "missing_id": target_id},
            })
        add_edge(source_id, target_id, str(link.get("relation") or "demo_unsupported"), "unsupported")

    node_list = sorted(nodes.values(), key=lambda n: (n["type"], n["id"]))
    edge_list = sorted(edges, key=lambda e: (e["from"], e["to"], e["relation"], e["state"]))
    type_counts = Counter(n["type"] for n in node_list)
    state_counts = Counter(e["state"] for e in edge_list)
    return {
        "schema": "uiowa-104-relationship-graph-v1",
        "synthetic": True,
        "source_bundle": SOURCE_DIR.as_posix(),
        "nodes": node_list,
        "edges": edge_list,
        "summary": {
            "node_count": len(node_list),
            "edge_count": len(edge_list),
            "node_types": dict(sorted(type_counts.items())),
            "edge_states": dict(sorted(state_counts.items())),
        },
    }

def validate_graph(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ["nodes/edges must be arrays"]
    node_ids = [str(n.get("id") or "") for n in nodes if isinstance(n, dict)]
    if len(node_ids) != len(set(node_ids)):
        errors.append("duplicate node id")
    id_set = set(node_ids)
    for edge in edges:
        if edge.get("from") not in id_set:
            errors.append("dangling edge source: " + str(edge.get("from")))
        if edge.get("to") not in id_set:
            errors.append("dangling edge target: " + str(edge.get("to")))
        if edge.get("state") not in {"supported", "supporting", "counter_evidence", "context", "unsupported"}:
            errors.append("invalid edge state: " + str(edge.get("state")))
    for node in nodes:
        if node.get("type") == "source":
            details = node.get("details") or {}
            if not str(details.get("source_name") or "").strip():
                errors.append("source node missing source_name: " + str(node.get("id")))
            if not str(details.get("locator") or "").strip():
                errors.append("source node missing locator: " + str(node.get("id")))
    return errors

def render_html(graph: dict[str, Any]) -> str:
    payload = json.dumps(graph, sort_keys=True, separators=(",", ":")).replace("</", "<\/")
    title = "UIOWA-104 synthetic finding-to-source relationship graph"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ font-family: system-ui, sans-serif; }}
body {{ margin: 0; background: #fafafa; color: #111; }}
header {{ padding: 14px 18px; border-bottom: 1px solid #bbb; background: white; }}
header p {{ margin: 4px 0 0; max-width: 980px; }}
main {{ display: grid; grid-template-columns: minmax(760px, 1fr) 360px; min-height: 780px; }}
#stage {{ position: relative; overflow: auto; min-height: 780px; background: white; }}
#edges {{ position: absolute; inset: 0; width: 1300px; height: 900px; pointer-events: none; }}
.node {{ position: absolute; width: 178px; min-height: 54px; padding: 7px; border: 1px solid #555; border-radius: 7px; background: #fff; text-align: left; font-size: 12px; cursor: pointer; }}
.node[data-type="missing"] {{ border-style: dashed; }}
.node[data-state="gap"], .node[data-state="mixed"], .node[data-state="unsupported_reference"] {{ font-weight: 600; }}
.node:focus {{ outline: 3px solid #444; }}
#detail {{ border-left: 1px solid #bbb; padding: 16px; overflow-wrap: anywhere; background: #f6f6f6; }}
#detail pre {{ white-space: pre-wrap; font-size: 12px; }}
.legend {{ display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; margin-top: 8px; }}
.legend span::before {{ content: ""; display: inline-block; width: 24px; border-top: 2px solid #555; margin-right: 5px; vertical-align: middle; }}
.legend .counter::before {{ border-top-style: dashed; }}
.legend .unsupported::before {{ border-top-style: dotted; }}
svg line {{ stroke: #666; stroke-width: 1.5; }}
svg line.counter_evidence {{ stroke-dasharray: 7 5; stroke-width: 2.5; }}
svg line.unsupported {{ stroke-dasharray: 2 5; stroke-width: 3; }}
small {{ color: #444; }}
@media (max-width: 1000px) {{ main {{ grid-template-columns: 1fr; }} #detail {{ border-left: 0; border-top: 1px solid #bbb; }} }}
</style>
</head>
<body>
<header>
<strong>{html.escape(title)}</strong>
<p>SYNTHETIC rehearsal only. Click any node to inspect exact IDs, limits, report references, and source locators. Dashed edges are counter-evidence; dotted edges are deliberately unsupported demo links.</p>
<div class="legend"><span>supported</span><span class="counter">counter-evidence</span><span class="unsupported">unsupported demo</span></div>
</header>
<main>
<section id="stage" aria-label="Relationship graph"><svg id="edges" aria-hidden="true"></svg></section>
<aside id="detail"><strong>Node detail</strong><p>Select a node.</p></aside>
</main>
<script>
const GRAPH={payload};
const stage=document.getElementById("stage"), svg=document.getElementById("edges"), detail=document.getElementById("detail");
const layerOrder=["recommendation","finding","observation","evidence","source","missing"];
const xFor={{recommendation:30,finding:250,observation:470,evidence:690,source:910,missing:250}};
const byType=Object.fromEntries(layerOrder.map(t=>[t,GRAPH.nodes.filter(n=>n.type===t).sort((a,b)=>a.id.localeCompare(b.id))]));
const pos=new Map();
for(const type of layerOrder){{
  (byType[type]||[]).forEach((node,i)=>{{
    const x=xFor[type]??1130, y=35+i*92;
    pos.set(node.id,{{x,y}});
    const b=document.createElement("button");
    b.className="node"; b.type="button"; b.dataset.type=node.type; b.dataset.state=node.state||"";
    b.style.left=x+"px"; b.style.top=y+"px"; b.textContent=node.label;
    b.addEventListener("click",()=>show(node));
    stage.appendChild(b);
  }});
}}
function line(edge){{
 const a=pos.get(edge.from), b=pos.get(edge.to); if(!a||!b) return;
 const ns="http://www.w3.org/2000/svg", l=document.createElementNS(ns,"line");
 l.setAttribute("x1",a.x+178); l.setAttribute("y1",a.y+27);
 l.setAttribute("x2",b.x); l.setAttribute("y2",b.y+27);
 l.setAttribute("class",edge.state||"supported"); l.dataset.relation=edge.relation; svg.appendChild(l);
}}
GRAPH.edges.forEach(line);
function show(node){{
 detail.replaceChildren();
 const h=document.createElement("h2"); h.textContent=node.label; detail.appendChild(h);
 const meta=document.createElement("p"); meta.textContent=node.type+" · "+(node.service||"")+" · "+(node.state||""); detail.appendChild(meta);
 const pre=document.createElement("pre"); pre.textContent=JSON.stringify(node.details||{{}},null,2); detail.appendChild(pre);
 const outgoing=GRAPH.edges.filter(e=>e.from===node.id), incoming=GRAPH.edges.filter(e=>e.to===node.id);
 const p=document.createElement("p"); p.textContent="Incoming edges: "+incoming.length+" · Outgoing edges: "+outgoing.length; detail.appendChild(p);
}}
</script>
</body>
</html>
"""

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--annotations", type=Path, default=HERE / "graph_annotations.json")
    parser.add_argument("--demo-links", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    graph = build_graph(args.repo, args.annotations, args.demo_links)
    errors = validate_graph(graph)
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "graph.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "graph.html").write_text(render_html(graph), encoding="utf-8")
    print(f"PASS nodes={graph['summary']['node_count']} edges={graph['summary']['edge_count']} unsupported={graph['summary']['edge_states'].get('unsupported',0)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
