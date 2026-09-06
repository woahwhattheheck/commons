"""failed.html must carry Autopsy $29 page-truth, not Survival-on-agent-rescue."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = (ROOT / "failed.html").read_text(encoding="utf-8")


def test_failed_html_nav_autopsy_29():
    assert 'href="./agent-rescue.html"' in HTML
    assert "Agent Failure Autopsy" in HTML
    assert "$29" in HTML
    assert "agent survival" not in HTML.lower()


def test_failed_html_page_truth_not_survival_on_rescue():
    assert "Page-truth: coding-agent failure cash door" in HTML
    assert "revenue/production_survival/README.md" in HTML
