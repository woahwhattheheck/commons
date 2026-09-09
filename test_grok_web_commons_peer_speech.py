#!/usr/bin/env python3
"""Peer-speech upgrade for grok-web-commons."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent
SKILL_DIR = ROOT / ".agents" / "skills" / "grok-web-commons"
SKILL = SKILL_DIR / "SKILL.md"
CONTRACT = SKILL_DIR / "references" / "connector-contract.md"
CHECKER = SKILL_DIR / "scripts" / "check_live_connector.py"
PEER = SKILL_DIR / "scripts" / "peer_speech.py"
PUBLIC_MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GrokWebCommonsPeerSpeechTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.contract = CONTRACT.read_text(encoding="utf-8")
        cls.peer = load_module("peer_speech", PEER)
        cls.checker = load_module("check_live_connector", CHECKER)

    def test_skill_and_contract_require_peer_speech(self):
        for marker in (
            "peer speech at the table",
            "Git keeps receipts",
            "TERMINAL_RECEIPT",
            "Do not mint a second Slack connector",
            "from= is a claim",
            "scripts/peer_speech.py",
        ):
            self.assertIn(marker, self.skill)
        self.assertIn("peer speech at the table", self.contract)
        self.assertIn("Git keeps receipts", self.contract)

    def test_helper_allows_speech_and_refuses_receipts(self):
        self.assertTrue(
            self.peer.is_peer_speech(
                "Sitting in #commons as a peer. Git keeps the file. Slack keeps the human."
            )
        )
        self.assertIsNotNone(
            self.peer.receipt_shape(
                "#commons TERMINAL_RECEIPT Disposition: MERGED starting main abc"
            )
        )
        self.assertIsNotNone(self.peer.receipt_shape(""))
        self.assertIsNotNone(
            self.peer.receipt_shape(
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
            )
        )
        self.assertIsNotNone(
            self.peer.receipt_shape(
                "https://github.com/woahwhattheheck/commons/pull/1 "
                "https://github.com/woahwhattheheck/commons/pull/2 "
                "https://github.com/woahwhattheheck/commons/pull/3"
            )
        )

    def test_write_canary_refuses_receipt_body_without_network(self):
        with mock.patch.object(self.checker, "rpc") as rpc:
            result = self.checker.write_canary(
                PUBLIC_MCP_URL,
                "x-canary-12345678",
                "#commons TERMINAL_RECEIPT Disposition: MERGED starting main abc",
            )
        rpc.assert_not_called()
        self.assertFalse(result.get("ok"))
        self.assertIn("receipt", (result.get("error") or "").lower())


if __name__ == "__main__":
    unittest.main()
