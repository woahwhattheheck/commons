"""Root-level test_*.py must use Path(__file__).resolve().parent (repo root), not parents[1]."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_root_tests_do_not_use_parents1_for_repo_root():
    bad = []
    for path in ROOT.glob("test_*.py"):
        text = path.read_text(encoding="utf-8")
        if "parents[1]" in text:
            bad.append(path.name)
    assert bad == [], f"root tests still use parents[1]: {bad[:12]}"
