#!/usr/bin/env python3
"""The canonical issue publisher must load current code, not event-time code."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github" / "workflows" / "commons-board.yml"


def main():
    raw = WORKFLOW.read_text(encoding="utf-8")
    checkout = re.search(
        r"- uses: actions/checkout@v4\s+with:\s+(.*?)(?=\n\s+- (?:name|uses):)",
        raw,
        re.S,
    )
    assert checkout, "commons-board checkout block missing"
    block = checkout.group(1)
    assert re.search(r"^\s*ref:\s*main\s*$", block, re.M), block
    assert re.search(r"^\s*fetch-depth:\s*0\s*$", block, re.M), block
    assert re.search(r"^\s*issues:\s*$", raw, re.M), "issues event trigger missing"
    assert "python3 board_ingest.py --publish" in raw, "canonical publisher call missing"
    print("BOARD CHECKOUT HEAD TEST: current main publisher + preserved issue event")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
