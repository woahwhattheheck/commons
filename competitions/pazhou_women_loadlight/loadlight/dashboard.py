from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def render(report: dict[str, Any]) -> str:
    actors = report["actors"]
    rows = []
    for actor in actors:
        metric = report["actor_metrics"][actor]
        rows.append(
            f"<tr><td>{html.escape(actor)}</td><td>{metric['cognitive_share']:.1%}</td>"
            f"<td>{metric['cognitive_units']:.1f}</td><td>{metric['execution_units']:.1f}</td>"
            f"<td>{metric['item_count']}</td></tr>"
        )
    handoffs = []
    for item in report["handoff_candidates"]:
        handoffs.append(
            "<li><strong>{task}</strong>: offer <code>{stage}</code> from {source} to {target} "
            "(current cognitive share {share:.0%}).</li>".format(
                task=html.escape(item["task"]),
                stage=html.escape(item["candidate_stage"]),
                source=html.escape(item["from_actor"]),
                target=html.escape(item["to_actor"]),
                share=item["current_cognitive_share"],
            )
        )
    if not handoffs:
        handoffs.append("<li>No concentrated multi-stage cognitive task met the suggestion threshold.</li>")
    report_json = html.escape(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
    return f"""<!doctype html>
<html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>
<title>LoadLight — invisible work made handoffable</title>
<style>
body{{font:16px/1.45 system-ui,sans-serif;max-width:980px;margin:40px auto;padding:0 20px;color:#17202a}}
h1{{font-size:2.3rem;margin-bottom:.2rem}} .tag{{color:#566573}} table{{border-collapse:collapse;width:100%}}
th,td{{border-bottom:1px solid #ddd;text-align:left;padding:10px}} .note{{background:#f5f5f5;padding:14px;border-radius:10px}}
code{{background:#f2f2f2;padding:2px 4px;border-radius:4px}} details{{margin-top:24px}}
</style></head><body>
<h1>LoadLight</h1><p class='tag'>Make invisible planning work visible — then make it handoffable.</p>
<div class='note'><strong>Interpretation boundary:</strong> These are workload visibility metrics, not a verdict on fairness or relationship quality. No raw message text is emitted; no health or safety inference is performed.</div>
<h2>Cognitive-work share</h2><table><thead><tr><th>Actor</th><th>Cognitive share</th><th>Cognitive units</th><th>Execution units</th><th>Items</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Handoff candidates</h2><ul>{''.join(handoffs)}</ul>
<h2>How it works</h2><ol><li>Classify each coordination item into anticipate / plan / decide / monitor / execute.</li><li>Weight cognitive stages separately from physical execution.</li><li>Surface task-level concentration and suggest explicit stage handoffs.</li><li>Keep the final assignment decision with the household.</li></ol>
<details><summary>Machine-readable report (raw source text excluded)</summary><pre>{report_json}</pre></details>
</body></html>"""


def write_dashboard(report: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(render(report), encoding="utf-8")
