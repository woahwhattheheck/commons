#!/usr/bin/env python3
"""ACK GOAT MATCH sidewalk door 200. TALLY bytes unread-as-write."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import goat_sidewalk_door_match as match  # noqa: E402


class GoatSidewalkDoorMatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = match.classify_match()
        self.receipt = (
            ROOT / "p" / "cursor-goat-match-sidewalk-door-200-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.helper = (ROOT / "host" / "goat_sidewalk_door_match.py").read_text(
            encoding="utf-8"
        )

    def test_helper_has_no_write_flag(self) -> None:
        self.assertNotIn("--write", self.helper)
        self.assertIn("unread-as-write", self.helper)
        self.assertIn("did not remint Pages/allowlist", self.receipt)

    def test_classify_is_unread_as_write(self) -> None:
        before = {
            row["path"]: (row["blob"], row["size"]) for row in self.result["files"]
        }
        again = match.classify_match()
        after = {row["path"]: (row["blob"], row["size"]) for row in again["files"]}
        self.assertEqual(before, after)
        self.assertTrue(self.result["unread_as_write"])
        self.assertTrue(self.result["did_not_write_pack"])
        self.assertTrue(self.result["did_not_remint_pages_allowlist"])

    def test_door_blob_and_checkout_not_minted(self) -> None:
        self.assertEqual(self.result["door_blob"], match.git_blob(match.DOOR_REL))
        self.assertEqual(self.result["door_baseline_blob"], "638e60b4")
        self.assertEqual(
            self.result["door_successors"],
            [
                "sold-once-css-v1",
                "sold-once-copy-v1",
                "live-cash-v1",
                "titanmcp-pad-pointer-v1",
            ],
        )
        self.assertGreater(self.result["door_size"], 6893)
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertTrue(self.result["match_ok"])
        door = (ROOT / match.DOOR_REL).read_text(encoding="utf-8")
        self.assertIn("NOT_MINTED", door)
        self.assertNotIn("buy.stripe.com", door)

    def test_tally_bytes_sum_disk(self) -> None:
        self.assertGreaterEqual(self.result["file_count"], 22)
        self.assertEqual(
            self.result["total_bytes"],
            sum(int(row["size"]) for row in self.result["files"]),
        )
        paths = {row["path"] for row in self.result["files"]}
        self.assertIn(match.DOOR_REL, paths)
        for row in self.result["files"]:
            data = (ROOT / row["path"]).read_bytes()
            digest = hashlib.sha1(
                b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            ).hexdigest()[:8]
            self.assertEqual(row["blob"], digest)
            self.assertEqual(row["size"], len(data))

    def test_tally_and_pages_ids_not_reminted(self) -> None:
        self.assertTrue(self.result["tally_ids_present"])
        self.assertTrue(self.result["pages_ids_present"])
        for pid in match.TALLY_IDS + match.PAGES_IDS:
            text = (ROOT / "p" / f"{pid}.md").read_text(encoding="utf-8")
            self.assertIn(f"id: {pid}", text)
            self.assertNotEqual(pid, match.RECEIPT_ID)
        self.assertIn("id: cursor-goat-match-sidewalk-door-200-20260902-01", self.receipt)
        self.assertIn("33601287295", self.receipt)
        self.assertIn("e86ff8f3", self.receipt)
        self.assertIn("HTTP 200", self.receipt)
        self.assertIn("unread-as-write", self.receipt)
        self.assertIn("NOT_MINTED", self.receipt)
        self.assertIn("337 NO", self.receipt)

    def test_pages_allowlist_blobs_untouched(self) -> None:
        self.assertEqual(
            self.result["pages_workflow_blob"],
            match.git_blob(".github/workflows/pages-deploy.yml"),
        )
        self.assertEqual(self.result["pages_workflow_baseline_blob"], "d3b298c2")
        self.assertEqual(self.result["pages_workflow_successors"], ["pages-cron-offset-v1"])
        self.assertEqual(match.git_blob("pages-deploy.json"), "475d5f24")
        self.assertEqual(match.git_blob("host/business_pack_desk_instance.py"), "1029faad")
        self.assertNotIn("authentication required", self.receipt.lower())
        self.assertNotIn("permission denied", self.receipt.lower())
        self.assertIs(self.result["gate"], False)
        self.assertIs(self.result["commons_admission"], False)
        self.assertIs(self.result["no_auth"], True)
        self.assertIs(self.result["agents_spend_ads"], False)

    def test_successor_normalization_is_exact_and_rejects_ambiguous_edits(self) -> None:
        base = b"head\nbody\n"
        successor = b"head\nknown\nbody\n"
        normalized, applied = match._normalize_successors(
            successor, (("known", b"known\n", b""),)
        )
        self.assertEqual(normalized, base)
        self.assertEqual(applied, ["known"])

        unknown, applied = match._normalize_successors(
            b"head\nother\nbody\n", (("known", b"known\n", b""),)
        )
        self.assertEqual(unknown, b"head\nother\nbody\n")
        self.assertEqual(applied, [])

        ambiguous, applied = match._normalize_successors(
            b"known\nknown\n", (("known", b"known\n", b""),)
        )
        self.assertEqual(ambiguous, b"known\nknown\n")
        self.assertEqual(applied, ["AMBIGUOUS:known"])

    def test_cli_json_and_no_write(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "goat_sidewalk_door_match.py"), "--json"],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["match_ok"])
        self.assertEqual(payload["pages_deploy_run"], "33601287295")
        self.assertEqual(
            payload["pages_deploy_sha"],
            "e86ff8f3e47fda6d56ee67ac304d8a3e3ce40747",
        )
        help_proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "goat_sidewalk_door_match.py"), "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertNotIn("--write", help_proc.stdout)


if __name__ == "__main__":
    unittest.main()
