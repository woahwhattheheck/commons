"""Command-line entry point for the hosted-score bridge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

try:
    from .contracts import BridgeConfig, IntegrityError
    from .normalize import load_jsonl
    from .report import build_report, render_markdown
except ImportError:  # direct script execution
    from contracts import BridgeConfig, IntegrityError
    from normalize import load_jsonl
    from report import build_report, render_markdown


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare behavior-active local Titan evidence with a hosted replay cohort."
    )
    parser.add_argument("--local", required=True, type=Path, help="local official-engine JSONL")
    parser.add_argument("--hosted", required=True, type=Path, help="hosted replay/cohort JSONL")
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--submission-id", required=True)
    parser.add_argument("--min-active-local-cells", type=int, default=8)
    parser.add_argument("--min-hosted-episodes", type=int, default=8)
    parser.add_argument("--min-active-share", type=float, default=0.50)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument(
        "--require-supported",
        action="store_true",
        help="exit 3 unless promotion status is SUPPORTED",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = BridgeConfig(
            archive_sha256=args.archive_sha256,
            submission_id=args.submission_id,
            min_active_local_cells=args.min_active_local_cells,
            min_hosted_episodes=args.min_hosted_episodes,
            min_active_share=args.min_active_share,
        )
        report = build_report(load_jsonl(args.local), load_jsonl(args.hosted), config)
    except (IntegrityError, OSError) as exc:
        print(f"score-bridge integrity error: {exc}", file=sys.stderr)
        return 2

    json_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    markdown = render_markdown(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json_text, encoding="utf-8")
    else:
        sys.stdout.write(json_text)
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown, encoding="utf-8")

    if args.require_supported and report["promotion"]["status"] != "SUPPORTED":
        return 3
    return 0
