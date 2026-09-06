"""Root-level test_*.py must resolve repo root via Path(__file__).resolve().parent."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Code smell only — do not match prose/docstrings that name the banned form.
_BAD = re.compile(r"resolve\(\)\.parents\[1\]")


def test_root_tests_do_not_use_parents1_for_repo_root():
    bad = []
    for path in sorted(ROOT.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        if _BAD.search(text):
            bad.append(path.name)
    assert bad == [], f"root tests still use resolve().parents[1]: {bad[:12]}"
