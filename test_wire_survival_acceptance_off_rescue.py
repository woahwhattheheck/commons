"""Survival acceptance_contract must not sell checkout on agent-rescue.html."""
from pathlib import Path

TEXT = (
    Path(__file__).resolve().parent
    / "revenue/production_survival/acceptance_contract.md"
).read_text(encoding="utf-8")


def test_acceptance_contract_survival_not_on_agent_rescue_checkout():
    assert "buyer-specific" in TEXT
    assert "README.md" in TEXT
    # Must explicitly refuse routing Survival checkout through Autopsy page
    assert "not" in TEXT.lower() and "agent-rescue.html" in TEXT
    assert "Agent Failure Autopsy" in TEXT or "Autopsy · $29" in TEXT
    # The old one-liner that treated agent-rescue as the Survival Buy surface must be gone
    assert "The buyer uses the provider-hosted link in [`../../agent-rescue.html`]" not in TEXT
