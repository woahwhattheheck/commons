"""Hermetic: AGENTS.md Commercial ladder Autopsy $29 truth; Survival off agent-rescue."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AGENTS = ROOT / "AGENTS.md"

def test_agents_autopsy_first_rung():
    text = AGENTS.read_text(encoding="utf-8")
    assert "Agent Failure Autopsy · $29](./agent-rescue.html)" in text

def test_agents_survival_off_agent_rescue():
    text = AGENTS.read_text(encoding="utf-8")
    assert "[$2,500 same-day crash-resume proof](./revenue/production_survival/README.md)" in text
    assert "[$15,000 five-day recovery sprint](./revenue/production_survival/README.md)" in text
    assert "[$2,500 same-day crash-resume proof](./agent-rescue.html)" not in text
    assert "[$15,000 five-day recovery sprint](./agent-rescue.html)" not in text
