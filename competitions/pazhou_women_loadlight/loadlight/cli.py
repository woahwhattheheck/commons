from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dashboard import write_dashboard
from .engine import analyze


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LoadLight cognitive-work visibility prototype")
    parser.add_argument("--input", required=True, help="loadlight-intake/v1 JSON")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    intake = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = analyze(intake)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    write_dashboard(report, out / "dashboard.html")
    print(json.dumps({
        "report_sha256": report["report_sha256"],
        "handoff_candidates": len(report["handoff_candidates"]),
        "raw_text_emitted": report["privacy"]["raw_text_emitted"],
        "dashboard": str(out / "dashboard.html"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
