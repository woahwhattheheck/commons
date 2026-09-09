#!/usr/bin/env python3
"""Survival sprint must not qualify via Autopsy page (agent-rescue.html)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "revenue" / "outcome_commerce" / "catalog.json"
SURVIVAL = "production-survival-sprint"
AUTOPSY = "agent-failure-autopsy-29"
README = "revenue/production_survival/README.md"
AUTOPSY_PAGE = "agent-rescue.html"


def test_survival_sprint_routes_off_autopsy_page() -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    funnel = data["funnels"][SURVIVAL]
    assert funnel["qualification"]["route"] == README
    assert funnel["qualification"]["route"] != AUTOPSY_PAGE
    assert "agent-rescue.html ladder" not in funnel["acquisition"]["alternate_channels"]
    assert any(README in c for c in funnel["acquisition"]["alternate_channels"])

    listing = next(x for x in data["listings"] if x["id"] == SURVIVAL)
    assert listing["routes"]["human"] == README
    assert listing["routes"]["human"] != AUTOPSY_PAGE

    autopsy = data["funnels"][AUTOPSY]
    assert autopsy["qualification"]["route"] == AUTOPSY_PAGE
    autopsy_listing = next(x for x in data["listings"] if x["id"] == AUTOPSY)
    assert autopsy_listing["routes"]["human"] == AUTOPSY_PAGE


if __name__ == "__main__":
    test_survival_sprint_routes_off_autopsy_page()
    print("ok")
