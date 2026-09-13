#!/usr/bin/env python3
"""Render scorer result JSON files into a dependency-free static comparison page."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


def _metric(value: Any) -> str:
    return f"{float(value):.4f}"


def render(results: list[dict[str, Any]]) -> str:
    if not results:
        raise ValueError("at least one result is required")
    benchmark_id = results[0]["benchmark_id"]
    benchmark_sha = results[0]["benchmark_sha256"]
    for row in results:
        if row["benchmark_id"] != benchmark_id or row["benchmark_sha256"] != benchmark_sha:
            raise ValueError("all results must bind the same benchmark id and digest")
    ordered = sorted(results, key=lambda row: (-float(row["metrics"]["accuracy"]), row["model_id"]))
    body_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(row['model_id']))}</td>"
        f"<td>{_metric(row['metrics']['accuracy'])}</td>"
        f"<td>{_metric(row['metrics']['macro_f1'])}</td>"
        f"<td>{_metric(row['metrics']['brier'])}</td>"
        f"<td>{_metric(row['metrics']['log_loss'])}</td>"
        "</tr>"
        for row in ordered
    )
    return f"""<!doctype html>
<meta charset=\"utf-8\">
<title>CAS perception benchmark demo</title>
<h1>CAS perception benchmark demo</h1>
<p>Benchmark: <code>{html.escape(str(benchmark_id))}</code></p>
<p>Exact benchmark SHA-256: <code>{html.escape(str(benchmark_sha))}</code></p>
<table>
<thead><tr><th>Model</th><th>Accuracy</th><th>Macro F1</th><th>Brier</th><th>Log loss</th></tr></thead>
<tbody>
{body_rows}
</tbody>
</table>
<p>Lower is better for Brier and log loss. This page contains synthetic demonstration data only.</p>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in args.results]
    args.output.write_text(render(documents), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
