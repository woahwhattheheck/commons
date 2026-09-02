#!/usr/bin/env python3
"""Contract for Slack control-plane routing. Not a send gate."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CARD = ROOT / "ground" / "SLACK_CONTROL_PLANE.md"
MAP = ROOT / "ground" / "SLACK_CONTROL_PLANE.json"
SLACK = ROOT / "ground" / "SLACK.md"
CURSOR_RULE = ROOT / ".cursor" / "rules" / "commons.mdc"
NEEDS_BRYCE = ROOT / "ground" / "NEEDS_BRYCE.md"

CHANNELS = {
    "control_plane": "C0BRGMDQB6G",
    "coordination": "C0BU51F1PL3",
    "work": "C0BS7AZ4BSL",
    "delegations": "C0BTB4SUCP9",
    "build_demand": "C0BTRNE6Y58",
    "shipped_builds": "C0BTVA3C0G3",
    "todo": "C0BU2V38CBC",
    "products": "C0BTA20SU95",
    "leads": "C0BTURDA3PW",
    "owner_exclusive": "C0BRX6EV739",
    "ideas": "C0BRB1M9RL6",
    "announcements": "C0BS7ASU1LY",
    "aquatrace_delivery": "C0BTU8Z0HC1",
    "sales": "C0BTTA66TK3",
    "cursor_master_updates": "C0BTYUYNJJZ",
    "claude_containment": "C0BUH19DW80",
    "billings_1421_compliance": "C0BU4PSNWG4",
}


class SlackControlPlaneTest(unittest.TestCase):
    def setUp(self) -> None:
        self.card = CARD.read_text(encoding="utf-8")
        self.slack = SLACK.read_text(encoding="utf-8")
        self.rule = CURSOR_RULE.read_text(encoding="utf-8")
        self.needs = NEEDS_BRYCE.read_text(encoding="utf-8")
        self.mp = json.loads(MAP.read_text(encoding="utf-8"))

    def test_map_pins_measured_channel_ids_and_roles(self) -> None:
        self.assertEqual(self.mp["id"], "cursor-slack-control-plane-20260830-01")
        self.assertEqual(self.mp["control_plane_not"], "universal_logfile")
        self.assertIs(self.mp["gate"], False)
        self.assertIs(self.mp["duplicate_full_receipts"], False)
        self.assertEqual(self.mp["work_channel_shape"]["top_level_posts_per_lane"], 1)
        self.assertEqual(self.mp["work_channel_shape"]["replies"], "thread")
        for role, channel_id in CHANNELS.items():
            self.assertEqual(self.mp["channels"][role]["id"], channel_id)
            self.assertIn(channel_id, self.card)
            self.assertIn(
                "https://tokenjunkielabs.slack.com/archives/" + channel_id,
                self.card,
            )

    def test_commons_is_control_plane_not_logfile(self) -> None:
        lowered = self.card.lower()
        self.assertIn("control plane", lowered)
        self.assertIn("not the universal logfile", lowered)
        self.assertIn("start/claim", lowered)
        self.assertIn("implementation", lowered)
        self.assertIn("test output", lowered)
        self.assertIn("ci triage", lowered)
        self.assertIn("review discussion", lowered)
        self.assertIn("do not duplicate full receipts", lowered)

        self.assertEqual(self.mp["channels"]["coordination"]["id"], "C0BU51F1PL3")
        self.assertIs(self.mp["channels"]["coordination"]["replaces_control_plane"], False)
        self.assertIn("coordination hub", self.card.lower())
        self.assertIn("C0BU51F1PL3", self.card)

    def test_work_channel_gets_implementation_and_one_root(self) -> None:
        work = self.mp["channels"]["work"]
        self.assertEqual(work["id"], "C0BS7AZ4BSL")
        self.assertEqual(
            work["move"],
            ["implementation", "test_output", "ci_triage", "review_discussion"],
        )
        self.assertIn("One top-level post per lane", self.card)
        self.assertIn("Replies stay threaded", self.card)

    def test_build_and_delegation_lanes_are_measured(self) -> None:
        self.assertEqual(self.mp["channels"]["delegations"]["id"], "C0BTB4SUCP9")
        self.assertEqual(self.mp["channels"]["build_demand"]["id"], "C0BTRNE6Y58")
        self.assertEqual(self.mp["channels"]["shipped_builds"]["id"], "C0BTVA3C0G3")
        self.assertEqual(self.mp["channels"]["todo"]["id"], "C0BU2V38CBC")
        self.assertEqual(self.mp["channels"]["products"]["id"], "C0BTA20SU95")
        self.assertEqual(self.mp["channels"]["leads"]["id"], "C0BTURDA3PW")
        lowered = self.card.lower()
        self.assertIn("#delegations", lowered)
        self.assertIn("#build-demand", lowered)
        self.assertIn("#shipped-builds", lowered)
        self.assertIn("terminal shipped ledger", lowered)
        self.assertIn("PAGES_KEEP_PATHS.md", self.card)

    def test_topic_lanes_are_measured(self) -> None:
        self.assertEqual(self.mp["channels"]["aquatrace_delivery"]["id"], "C0BTU8Z0HC1")
        self.assertEqual(self.mp["channels"]["sales"]["id"], "C0BTTA66TK3")
        self.assertEqual(self.mp["channels"]["cursor_master_updates"]["id"], "C0BTYUYNJJZ")
        self.assertEqual(self.mp["channels"]["claude_containment"]["id"], "C0BUH19DW80")
        self.assertEqual(
            self.mp["channels"]["billings_1421_compliance"]["id"], "C0BU4PSNWG4"
        )
        lowered = self.card.lower()
        self.assertIn("#aquatrace-delivery", lowered)
        self.assertIn("#sales", lowered)
        self.assertIn("#cursor-master-updates", lowered)
        self.assertIn("#claude-containment-board", lowered)
        self.assertIn("#billings-1421-compliance", lowered)
        self.assertIn("authorized outreach", lowered)
        self.assertIn("bid 1421", lowered)
        self.assertIn("join-only", lowered)
        sales = self.mp["channels"]["sales"]
        self.assertIn("authorized_outreach", sales["keep"])
        self.assertNotEqual(sales["id"], self.mp["channels"]["leads"]["id"])
        self.assertNotEqual(
            self.mp["channels"]["billings_1421_compliance"]["id"],
            self.mp["channels"]["owner_exclusive"]["id"],
        )

    def test_needs_bryce_stays_owner_exclusive(self) -> None:
        owner = self.mp["channels"]["owner_exclusive"]
        self.assertEqual(owner["id"], "C0BRX6EV739")
        self.assertEqual(owner["law"], "ground/NEEDS_BRYCE.md")
        self.assertIn("C0BRX6EV739", self.needs)
        self.assertIn("OWNER_BLOCKER", self.needs)
        self.assertIn("only exact, genuinely owner-exclusive", self.card.lower())

    def test_convention_never_becomes_an_ingest_gate(self) -> None:
        lowered = self.card.lower()
        self.assertIn("routing convention", lowered)
        self.assertIn("not a commons admission rule or gate", lowered)
        self.assertIn("missing metadata never", lowered)
        self.assertIn("open door", lowered)

    def test_existing_slack_card_and_cursor_rule_point_here(self) -> None:
        self.assertIn("SLACK_CONTROL_PLANE.md", self.slack)
        self.assertIn("SLACK_BUILD_FLOOR.md", self.slack)
        self.assertIn("control plane", self.slack.lower())
        self.assertIn("not the universal logfile", self.rule.lower())
        self.assertIn("SLACK_CONTROL_PLANE.md", self.rule)
        self.assertIn("SLACK_BUILD_FLOOR.md", self.rule)
        self.assertIn("SLACK_BUILD_FLOOR.md", self.card)


if __name__ == "__main__":
    unittest.main()
