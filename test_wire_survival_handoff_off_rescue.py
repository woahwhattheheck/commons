"""Survival handoff must not narrate Stripe/auth on agent-rescue.html."""
from pathlib import Path

TEXT = (
    Path(__file__).resolve().parent
    / "revenue/posted_work_discovery/handoff_agent_survival_proof.md"
).read_text(encoding="utf-8")


def test_handoff_survival_stripe_not_on_agent_rescue():
    assert "Same-Day Agent Survival Proof" in TEXT or "$2,500" in TEXT
    assert "revenue/production_survival/README.md" in TEXT
    assert "Stripe authorization on `agent-rescue.html`" not in TEXT
    assert "line already on `agent-rescue.html`" not in TEXT
    # Still may mention agent-rescue as Autopsy boundary — that's fine if README is present
    assert "Autopsy" in TEXT or "not" in TEXT.lower()
