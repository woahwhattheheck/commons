#!/usr/bin/env python3
"""Focused open-door tests for the mirrored Muhlnickel GitHub drive."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent
HOST_PATH = ROOT / "host" / "muhl_github_drive.py"
INFRA_PATH = ROOT / "infra" / "host" / "muhl_github_drive.py"


def load_drive():
    spec = importlib.util.spec_from_file_location("tested_muhl_github_drive", HOST_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load muhl_github_drive")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MuhlGithubDriveOpenDoorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.drive = load_drive()

    def exercise_say(self, mid, cmd):
        drive = self.drive
        delivered = []
        receipts = []
        envelope = {
            "id": mid,
            "from": cmd.get("from", ""),
            "to": cmd.get("to", ""),
            "body": cmd.get("body", ""),
        }

        def deliver(src, dest, letter, log=None):
            delivered.append((src, dest, letter))
            return [dest]

        with (
            mock.patch.object(drive, "load_receipt", return_value=None),
            mock.patch.object(drive.mstore, "load_receipt", return_value=None),
            mock.patch.object(drive.mstore, "store_offered", return_value=envelope),
            mock.patch.object(drive.mstore, "envelope_lines", return_value="opaque letter"),
            mock.patch.object(drive.route, "deliver", side_effect=deliver),
            mock.patch.object(drive.mouth, "format_receipt", return_value="OPEN RECEIPT\n"),
            mock.patch.object(drive.mstore, "save_receipt"),
            mock.patch.object(drive, "write_receipt", side_effect=lambda _mid, text: receipts.append(text)),
        ):
            state, receipt = drive.act_say(mid, cmd)

        self.assertEqual("fresh", state)
        self.assertEqual("OPEN RECEIPT\n", receipt)
        self.assertEqual([(cmd["from"], cmd["to"], "opaque letter")], delivered)
        self.assertEqual(["OPEN RECEIPT\n"], receipts)

    def test_ordinary_say_needs_no_approval_field(self):
        self.exercise_say(
            "ordinary-open-01",
            {"kind": "say", "from": "ANYONE", "to": "COMMONS", "body": "hello"},
        )

    def test_kite_to_grok_needs_no_owner_identity(self):
        self.exercise_say(
            "kite-grok-open-01",
            {"kind": "say", "from": "KITE", "to": "GROK", "body": "hello"},
        )

    def test_verify_purpose_is_metadata_not_an_admission_gate(self):
        drive = self.drive
        command = {
            "kind": "say",
            "purpose": "VERIFY",
            "from": "ANYONE",
            "to": "COMMONS",
            "body": "verify this openly",
        }
        with (
            mock.patch.object(sys, "argv", [str(HOST_PATH), "--go", "--local"]),
            mock.patch.object(drive.os, "makedirs"),
            mock.patch.object(drive, "load_local_commands", return_value={"verify-open-01": command}),
            mock.patch.object(drive, "load_github_commands", return_value={}),
            mock.patch.object(drive, "act_say", return_value=("fresh", "OPEN RECEIPT\n")) as act_say,
            mock.patch.object(drive, "inbox_text", return_value="OPEN INBOX\n"),
            mock.patch.object(drive, "receipts_inbox", return_value="OPEN RECEIPTS\n"),
            mock.patch.object(drive, "_write"),
            mock.patch.object(drive.pub, "collect_pub_files", return_value={}),
            mock.patch.object(drive.pub, "write_local_public"),
            mock.patch.object(drive, "publish_after"),
        ):
            self.assertEqual(0, drive.main())

        act_say.assert_called_once_with("verify-open-01", command)

    def test_mirrors_are_exact_and_contain_no_admission_gate(self):
        host = HOST_PATH.read_text(encoding="utf-8")
        infra = INFRA_PATH.read_text(encoding="utf-8")
        self.assertEqual(host, infra)
        for forbidden in (
            "REFUSE_PURPOSE",
            "purpose_refused",
            "approved=YES",
            "owner_ok=BRYCE",
            'cmd.get("approved")',
            'cmd.get("owner_ok")',
            "Bryce or Grok writes the ticket",
            "NEED_BRYCE",
        ):
            self.assertNotIn(forbidden, host)


if __name__ == "__main__":
    unittest.main()
