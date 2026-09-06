"""DIGIT: AGENTS.md commercial ladder Autopsy $29; Survival not on agent-rescue."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[0]
MD = (ROOT / "AGENTS.md").read_text(encoding="utf-8")


def test_agents_md_autopsy_on_agent_rescue():
    assert "[$29 Agent Failure Autopsy](./agent-rescue.html)" in MD
    assert "Agent Failure Autopsy" in MD


def test_agents_md_survival_not_on_agent_rescue():
    assert "[$2,500 same-day crash-resume proof](./agent-rescue.html)" not in MD
    assert "[$15,000 five-day recovery sprint](./agent-rescue.html)" not in MD
    assert "[$2,500 same-day crash-resume proof](./revenue/production_survival/README.md)" in MD
    assert "[$15,000 five-day recovery sprint](./revenue/production_survival/README.md)" in MD
