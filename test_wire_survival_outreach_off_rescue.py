"""Survival outreach templates must not link $2500 offer to agent-rescue.html."""
from pathlib import Path

TEXT = (
    Path(__file__).resolve().parent / "revenue/production_survival/outreach.md"
).read_text(encoding="utf-8")


def test_outreach_survival_links_readme_not_agent_rescue():
    assert "Same-Day Agent Survival Proof" in TEXT
    assert (
        "https://woahwhattheheck.github.io/commons/revenue/production_survival/README.md"
        in TEXT
    )
    # Survival Proof parentheticals must not point at Autopsy page
    assert (
        "Same-Day Agent Survival Proof (<https://woahwhattheheck.github.io/commons/agent-rescue.html>)"
        not in TEXT
    )
