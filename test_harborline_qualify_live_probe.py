#!/usr/bin/env python3
"""Pin Harborline /qualify live-probe leftover. Do not remint peer AutoGTM files."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_qualify_live_probe.py"

KEEP = {
    "p/cursor-explee-qualify-clone-20260902-01.md": "aceb4aead",
    "autogtm.html": "9d8b3e85",
    "p/cursor-autogtm-door-live-probe-20260902-01.md": "c71c57a0",
    "p/cursor-explee-skills-adopt-20260902-01.md": "20db155c",
    "host/explee_autogtm_local.py": "5407261c",
    "test_autogtm_same_loop.py": "70b8413e",
    "p/cursor-autogtm-peer-ack-lead-landed-20260902-01.md": "68fa5493",
    "p/cursor-autogtm-peer-ack-lead-landed-readback-20260902-01.md": "d3be87c2",
    "p/cursor-autogtm-peer-readback-ack-20260902-01.md": "d9d1008e",
    "p/cursor-autogtm-explee-same-loop-20260902-01.md": "c437f4d6",
    "packs/desk-website-service-20260902-01/door.html": "d3d6fcc7",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": "7a8987b5",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(*flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestHarborlineQualifyLiveProbe(unittest.TestCase):
    def test_keep_main_unique_paths_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_exists_and_does_not_steal(self) -> None:
        receipt = (
            ROOT / "p/cursor-harborline-qualify-live-probe-20260902-01.md"
        ).read_text(encoding="utf-8")
        self.assertIn("aceb4aead", receipt)
        self.assertIn("9d8b3e85", receipt)
        self.assertIn("c71c57a0", receipt)
        self.assertIn("20db155c", receipt)
        self.assertIn("d9d1008e", receipt)
        self.assertIn("credentials=omit", receipt)
        self.assertIn("FINDER-FAILED", receipt)
        self.assertIn("Did not remint", receipt)
        self.assertNotIn("qualify.html", receipt)
        src = HELPER.read_text(encoding="utf-8")
        self.assertNotIn("EXPLEE_API_KEY", src)
        self.assertNotIn("Bearer", src)
        self.assertNotIn("type=\"password\"", src)
        self.assertNotIn("add_header", src)

    def test_send_apply_go_autopilot_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot"):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["booked"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)

    def test_unknown_args_finder_failed_not_zero(self) -> None:
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")

    def test_live_explee_projects_is_finder_failed_not_zero(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")
        self.assertEqual(payload["credentials"], "omit")
        self.assertEqual(payload["authorization"], "absent")
        if payload["http"] == "FINDER-FAILED":
            self.assertTrue(payload["detail"], msg="network miss must carry search space")
            return
        self.assertEqual(payload["http"], 401)
        self.assertIn("Missing API key", payload["detail"])
        self.assertNotEqual(payload["http"], 0)


if __name__ == "__main__":
    unittest.main()
