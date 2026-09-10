#!/usr/bin/env python3
"""Restore leftover tools/builds/features cites after tests battery 34402627346.

Delayed pull_request battery on already-merged PR #11679
(head 236c87f0f877e00a76f36714bf439b064c54cbce, merge-ref
5256b978dd9ff228392b2138a51c2401cf865416) failed 210 files.
Later KEEP-lifts closed living KEEP dicts of reminted shared files.
Unique leftover test_coil_commands_goal_cite.py still passes.
Remaining graph: ingest rebuild reminted tools.html / builds.html /
features.html and dropped unique leftover cash-hook, DIGIT door, DIGIT
note, and DIGIT seat cites because living builders/splices did not emit
them. Emit those cites from board_ingest splices and builds_ledger so
rebuilds keep them. Do not remint leftover receipts. Historical
SOURCE_REV maps stay on their frozen trees. Hands off #8802.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import board_ingest
import builds_ledger
import hub_pages

ROOT = Path(__file__).resolve().parent
ORIGINALS = (
    "test_coil_commands_goal_cite.py",
    "test_coil_tools_html_cash_hook.py",
    "test_digit_tools_html_digit_door_20260909_01.py",
    "test_digit_builds_html_digit_note_20260909_02.py",
    "test_digit_features_html_digit_note_20260909_01.py",
    "test_coil_tools_cash_doors.py",
    "test_builds_ledger.py",
)
RECEIPT = ROOT / "p/grokbuild-tests-battery-34402627346-keep-lift-20260910-01.md"
DEDUPE = (
    "woahwhattheheck/commons:tests:"
    "236c87f0f877e00a76f36714bf439b064c54cbce:"
    "the whole battery, one failure fails the run"
)
TOOLS = "e8a088aa"
STALE_TOOLS = "3f632f0a"
BUILDS = "51c69d17"
STALE_BUILDS = "c1313e23"
FEATURES = "90d7e47b"
STALE_FEATURES = "5a37e0a8"
INGEST = "174bab0a"
LEDGER = "35a08aea"
HUB = "44bbd2ec"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTestsBattery34402627346KeepLift(unittest.TestCase):
    def test_live_tools_builds_features_match_lifted_prefixes(self) -> None:
        tools = git_blob("tools.html")
        builds = git_blob("builds.html")
        features = git_blob("features.html")
        ingest = git_blob("board_ingest.py")
        ledger = git_blob("builds_ledger.py")
        hub = git_blob("hub_pages.py")
        self.assertTrue(tools.startswith(TOOLS), tools)
        self.assertFalse(tools.startswith(STALE_TOOLS), tools)
        self.assertTrue(builds.startswith(BUILDS), builds)
        self.assertFalse(builds.startswith(STALE_BUILDS), builds)
        self.assertTrue(features.startswith(FEATURES), features)
        self.assertFalse(features.startswith(STALE_FEATURES), features)
        self.assertTrue(ingest.startswith(INGEST), ingest)
        self.assertTrue(ledger.startswith(LEDGER), ledger)
        self.assertTrue(hub.startswith(HUB), hub)

    def test_splices_and_ledger_emit_unique_leftover_cites(self) -> None:
        ingest = (ROOT / "board_ingest.py").read_text(encoding="utf-8")
        self.assertIn("TOOLS_CASH_HOOK", ingest)
        self.assertIn("TOOLS_DIGIT_DOOR", ingest)
        self.assertIn("FEATURES_DIGIT_SEAT", ingest)
        self.assertIn("splice_features_digit_seat()", ingest)
        self.assertIn("coil-tools-json-live-cash-20260905-01", ingest)
        ledger = (ROOT / "builds_ledger.py").read_text(encoding="utf-8")
        self.assertIn('id="digit-note"', ledger)
        self.assertIn("Builds ledger DIGIT note", ledger)
        self.assertIn('href="./wire.html"', ledger)
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertNotIn('id="cash-hook"', hub)
        self.assertNotIn('id="digit-door"', hub)
        self.assertNotIn('id="digit-seat"', hub)

    def test_rebuilds_keep_spliced_cites(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            catalog = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))
            (tmp / "tools.json").write_text(json.dumps(catalog), encoding="utf-8")
            (tmp / "share.json").write_text(
                json.dumps({"open": [], "done": [], "receipts": 0}),
                encoding="utf-8",
            )
            state = {"open": [], "done": [], "receipts": 0}
            with patch.object(board_ingest, "ROOT", str(tmp)):
                hub_pages.rebuild_tools(board_ingest, [], state)
                self.assertTrue(board_ingest.splice_tools_cash_doors())
                self.assertFalse(board_ingest.splice_tools_cash_doors())
            tools = (tmp / "tools.html").read_text(encoding="utf-8")
            self.assertIn('id="cash-hook"', tools)
            self.assertIn('id="digit-door"', tools)
            self.assertIn("coil-tools-json-live-cash-20260905-01", tools)
            self.assertNotIn("hygiene seat", tools)
            written = {}
            builds_ledger.project(str(tmp), lambda p, t: written.__setitem__(p, t))
            page = written[str(tmp / "builds.html")]
            self.assertIn('id="digit-note"', page)
            self.assertIn("Builds ledger DIGIT note", page)
            self.assertIn('href="./wire.html"', page)

    def test_originally_failing_unique_graph_contracts_pass(self) -> None:
        for name in ORIGINALS:
            with self.subTest(name=name):
                proc = subprocess.run(
                    ["python3", name],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=f"{name}\n{proc.stdout}\n{proc.stderr}",
                )

    def test_did_not_remint_leftover_receipts_or_hub_pages(self) -> None:
        leftover = ROOT / "p/coil-commands-goal-cite-20260909-01.md"
        self.assertTrue(leftover.is_file())
        self.assertTrue(
            git_blob("p/coil-commands-goal-cite-20260909-01.md").startswith("9b713589")
        )
        self.assertTrue(
            git_blob("p/digit-peer-coil-commands-goal-cite-20260909-01.md").startswith(
                "10df139c"
            )
        )
        self.assertTrue(git_blob("test_coil_commands_goal_cite.py").startswith("2f59d138"))
        self.assertTrue(git_blob("hub_pages.py").startswith(HUB))
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("34402627346", receipt)
        self.assertIn(DEDUPE, receipt)
        cites = "\n".join(
            (
                board_ingest.TOOLS_CASH_HOOK,
                board_ingest.TOOLS_DIGIT_DOOR,
                board_ingest.FEATURES_DIGIT_SEAT,
                (ROOT / "tools.html").read_text(encoding="utf-8"),
                (ROOT / "builds.html").read_text(encoding="utf-8"),
                (ROOT / "features.html").read_text(encoding="utf-8"),
                receipt,
            )
        )
        self.assertNotIn('type="password"', cites)
        self.assertNotIn("buy.stripe.com", cites)


if __name__ == "__main__":
    unittest.main()
