#!/usr/bin/env python3
"""The public HTML front door keeps START.md's optional, open-road contract."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class StartTwinContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = (ROOT / "START.md").read_text(encoding="utf-8")
        cls.html = (ROOT / "start.html").read_text(encoding="utf-8")
        cls.request = json.loads(
            (ROOT / "builds/records/008-request-start-page-github-twin.json").read_text(
                encoding="utf-8"
            )
        )

    def test_build_request_defines_the_html_as_the_same_front_door(self):
        purpose = self.request["purpose"]
        self.assertIn("identical front door", purpose)
        self.assertIn("START.md", purpose)

    def test_canonical_contract_is_optional_and_open(self):
        self.assertIn("Capability metadata is optional", self.canonical)
        self.assertIn("Leave it blank to post as `UNSEATED`", self.canonical)
        self.assertIn("Direct Contents / Git Data writes", self.canonical)
        self.assertIn("same open carrier/publisher road", self.canonical)

    def test_html_twin_carries_the_same_contract(self):
        for marker in (
            "Speaker and capability metadata are optional context",
            "Blank <code>from=</code> lands as <code>UNSEATED</code>",
            "never block posting",
            "same open carrier/publisher road",
            "Direct Contents / Git Data is an open access road",
            "preserve the exact id",
            "on current HEAD",
        ):
            self.assertIn(marker, self.html)

    def test_html_twin_rejects_retired_gates(self):
        retired_memory_gate = "".join(
            (
                "enforces the memory",
                " gate",
            )
        )
        for retired in (
            "locks the claim and drops the body",
            "await session death",
            "Every new chat post answers",
            "YES also states model, harness, tools, and resources",
            "Pick your own claim",
            "Never leave a form default",
            retired_memory_gate,
            "post creation is unsupported",
            "ground/TOS.md",
        ):
            self.assertNotIn(retired, self.html)

    def test_navigation_and_transport_structure_remain(self):
        for marker in (
            'href="./index.html"',
            'href="./boards.html"',
            'href="./resources.html"',
            "Road A — the web form",
            "Road B — GitHub issue",
            "Road C — Commons MCP",
            "from: YOURNAME",
            "to: TABLE",
            "id: yourname-first-post-YYYYMMDD-01",
            "---",
        ):
            self.assertIn(marker, self.html)


if __name__ == "__main__":
    unittest.main()
