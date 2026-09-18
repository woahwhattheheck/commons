#!/usr/bin/env python3
"""Muhlnickel measurements never become host-side permission gates."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class MuhlnickelActivityOpenTest(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_active_policy_keeps_muhlnickel_activity_open(self):
        agents = self.read("AGENTS.md")
        host = self.read("host/README.md")
        skill = self.read(".agents/skills/pfc-spec/SKILL.md")
        directives = self.read("DIRECTIVES.md")
        swarm_host = self.read("host/muhl_swarm_dc.py")
        swarm_card = self.read("ground/SWARM_DC.md")
        swarm_door = self.read("swarm-dc.html")

        for source in (agents, host, skill, directives, swarm_door):
            self.assertIn("Address, inject, fire, run, and surface", source)
        self.assertIn("not permission gates", agents)
        self.assertIn("not a gate", directives)
        self.assertNotIn("Do not fire 337", host)
        self.assertNotIn("Fire 337.", skill)
        self.assertNotIn("Never fire 337", directives)
        self.assertNotIn("LIVE_DC NEED_OWNER", directives)
        for source in (swarm_host, swarm_card, swarm_door):
            self.assertNotIn("NEED_OWNER", source)
            self.assertNotIn("Never fire 337", source)

    def test_only_host_compute_remains_closed(self):
        agents = self.read("AGENTS.md")
        host = self.read("host/README.md")
        skill = self.read(".agents/skills/pfc-spec/SKILL.md")

        self.assertIn("host laptop must never perform inference", agents)
        self.assertIn("host computes zero inference", host.lower())
        self.assertIn("Host-compute inference or gate evaluation", skill)

    def test_historical_false_measurement_is_preserved(self):
        swarm = self.read("ground/SWARM_DC.json")
        self.assertIn('"fire_337": false', swarm)
        self.assertIn('"host_inference": false', swarm)


if __name__ == "__main__":
    unittest.main()
