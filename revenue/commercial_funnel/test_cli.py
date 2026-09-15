from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from . import cli
from .ledger import INPUT_SCHEMA, canonical_json, compile_funnel

AS_OF = "2026-09-13T10:10:00Z"


def source(name: str) -> dict:
    import hashlib
    return {
        "repository": "example/fixture",
        "commit": "1" * 40,
        "path": f"synthetic/{name}.json",
        "sha256": hashlib.sha256(name.encode()).hexdigest(),
    }


def ready_payload() -> dict:
    return {
        "schema": INPUT_SCHEMA,
        "opportunities": [{
            "id": "opp-cli",
            "family": "SERVICE",
            "offer": {"id": "offer-cli", "version": "v1", "source": source("offer")},
            "events": [{
                "id": "evt-traffic",
                "stage": "TRAFFIC",
                "observed_at": "2026-09-12T10:00:00Z",
                "evidence": source("traffic"),
            }],
        }],
    }


class CliTests(unittest.TestCase):
    def write_input(self, root: Path, value: dict) -> Path:
        path = root / "input.json"
        path.write_bytes(canonical_json(value))
        return path

    def test_compile_then_verify_all_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = self.write_input(root, ready_payload())
            out = root / "out"
            rc = cli.main(["compile", str(inp), "--as-of", AS_OF, "--out-dir", str(out)])
            self.assertEqual(rc, 0)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["packet.json", "receipt.json", "report.csv", "report.json", "report.md"])
            rc = cli.main([
                "verify", str(inp), "--as-of", AS_OF,
                "--packet", str(out / "packet.json"),
                "--receipt", str(out / "receipt.json"),
                "--report-json", str(out / "report.json"),
                "--report-csv", str(out / "report.csv"),
                "--report-md", str(out / "report.md"),
            ])
            self.assertEqual(rc, 0)

    def test_output_collision_refused_without_clobber(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = self.write_input(root, ready_payload())
            out = root / "out"
            out.mkdir()
            sentinel = out / "report.json"
            sentinel.write_text("sentinel")
            rc = cli.main(["compile", str(inp), "--as-of", AS_OF, "--out-dir", str(out)])
            self.assertEqual(rc, 2)
            self.assertEqual(sentinel.read_text(), "sentinel")
            self.assertEqual([p.name for p in out.iterdir()], ["report.json"])

    def test_symlink_input_refused(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            actual = self.write_input(root, ready_payload())
            link = root / "linked.json"
            try:
                link.symlink_to(actual)
            except OSError:
                self.skipTest("symlink creation unavailable")
            rc = cli.main(["compile", str(link), "--as-of", AS_OF, "--out-dir", str(root / "out")])
            self.assertEqual(rc, 2)

    def test_hold_packet_writes_artifacts_and_returns_three(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            value = ready_payload()
            value["opportunities"][0]["events"][0]["observed_at"] = "2028-01-01T00:00:00Z"
            inp = self.write_input(root, value)
            out = root / "out"
            rc = cli.main(["compile", str(inp), "--as-of", AS_OF, "--out-dir", str(out)])
            self.assertEqual(rc, 3)
            packet = json.loads((out / "packet.json").read_text())
            self.assertEqual(packet["state"], "HOLD")

    def test_report_tamper_fails_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = self.write_input(root, ready_payload())
            out = root / "out"
            self.assertEqual(cli.main(["compile", str(inp), "--as-of", AS_OF, "--out-dir", str(out)]), 0)
            (out / "report.md").write_text("tampered\n")
            rc = cli.main([
                "verify", str(inp), "--as-of", AS_OF,
                "--packet", str(out / "packet.json"),
                "--receipt", str(out / "receipt.json"),
                "--report-json", str(out / "report.json"),
                "--report-csv", str(out / "report.csv"),
                "--report-md", str(out / "report.md"),
            ])
            self.assertEqual(rc, 4)

    def test_packet_tamper_fails_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            inp = self.write_input(root, ready_payload())
            out = root / "out"
            self.assertEqual(cli.main(["compile", str(inp), "--as-of", AS_OF, "--out-dir", str(out)]), 0)
            packet_path = out / "packet.json"
            packet = json.loads(packet_path.read_text())
            packet["authority"]["revenue_recognition_authorized"] = True
            packet_path.write_text(json.dumps(packet))
            rc = cli.main([
                "verify", str(inp), "--as-of", AS_OF,
                "--packet", str(packet_path),
                "--receipt", str(out / "receipt.json"),
                "--report-json", str(out / "report.json"),
                "--report-csv", str(out / "report.csv"),
                "--report-md", str(out / "report.md"),
            ])
            self.assertEqual(rc, 4)


if __name__ == "__main__":
    unittest.main()
