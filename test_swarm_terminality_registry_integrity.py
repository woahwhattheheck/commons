from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.swarm_terminality_registry.core import (
    AUTHORITY_CEILING,
    RegistryError,
    compile_snapshot,
    load_strict_json,
    verify_bundle,
)

ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / "tools" / "swarm_terminality_registry" / "example.json"


def candidate():
    return load_strict_json(EXAMPLE.read_text(encoding="utf-8"))


def by_id(report, item_id):
    return next(x for x in report["items"] if x["item_id"] == item_id)


class TerminalityRegistryTests(unittest.TestCase):
    def test_impossible_merged_issue_rejected(self):
        data = candidate()
        obs = next(x for x in data["provider_observations"] if x["id"] == "obs-issue-old")
        obs["provider_state"] = "MERGED"
        obs["merged_sha"] = "2" * 40
        with self.assertRaisesRegex(RegistryError, "impossible provider state"):
            compile_snapshot(data)

    def test_merged_requires_sha(self):
        data = candidate()
        next(x for x in data["provider_observations"] if x["id"] == "obs-pr-merged")["merged_sha"] = None
        with self.assertRaisesRegex(RegistryError, "requires merged_sha"):
            compile_snapshot(data)

    def test_present_branch_requires_head(self):
        data = candidate()
        obs = next(x for x in data["provider_observations"] if x["id"] == "obs-branch-unknown")
        obs["provider_state"] = "PRESENT"
        obs["head_sha"] = None
        with self.assertRaisesRegex(RegistryError, "requires head_sha"):
            compile_snapshot(data)

    def test_bool_age_rejected(self):
        data = candidate()
        data["max_provider_age_seconds"] = True
        with self.assertRaisesRegex(RegistryError, "bool rejected"):
            compile_snapshot(data)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(RegistryError, "duplicate JSON key"):
            load_strict_json('{"a":1,"a":2}')

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(RegistryError, "non-finite"):
            load_strict_json('{"a":NaN}')

    def test_unknown_root_field_rejected(self):
        data = candidate()
        data["magic"] = True
        with self.assertRaisesRegex(RegistryError, "unknown fields"):
            compile_snapshot(data)

    def test_unsafe_source_url_rejected(self):
        data = candidate()
        data["provider_observations"][0]["source_url"] = "https://user:pass@example.com/x"
        with self.assertRaisesRegex(RegistryError, "without userinfo"):
            compile_snapshot(data)

    def test_input_order_canonical(self):
        a = candidate()
        b = copy.deepcopy(a)
        for key in ("items", "provider_observations", "heartbeats", "successors"):
            b[key] = list(reversed(b[key]))
        ba, bb = compile_snapshot(a), compile_snapshot(b)
        self.assertEqual(ba.report_json, bb.report_json)
        self.assertEqual(ba.report_markdown, bb.report_markdown)
        self.assertEqual(ba.receipt_json, bb.receipt_json)

    def test_resealed_report_tamper_rejected(self):
        data = candidate()
        bundle = compile_snapshot(data)
        report = json.loads(bundle.report_json)
        by_id(report, "op-recover")["classification"] = "ACTIVE_CUSTODY"
        forged = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        receipt = json.loads(bundle.receipt_json)
        receipt["report_json_sha256"] = hashlib.sha256(forged.encode()).hexdigest()
        resealed = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        with self.assertRaisesRegex(RegistryError, "semantic recompile"):
            verify_bundle(data, forged, bundle.report_markdown, resealed)

    def test_markdown_tamper_rejected(self):
        data = candidate(); bundle = compile_snapshot(data)
        with self.assertRaisesRegex(RegistryError, "Markdown"):
            verify_bundle(data, bundle.report_json, bundle.report_markdown + "tamper\n", bundle.receipt_json)

    def test_cli_roundtrip_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "snapshot.json"
            src.write_bytes(EXAMPLE.read_bytes())
            prefix = Path(td) / "out"
            cmd = [sys.executable, "-m", "tools.swarm_terminality_registry.cli"]
            first = subprocess.run(cmd + ["compile", str(src), str(prefix)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            verify = subprocess.run(cmd + ["verify", str(src), str(prefix.with_suffix('.report.json')), str(prefix.with_suffix('.report.md')), str(prefix.with_suffix('.receipt.json'))], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertIn("VALID", verify.stdout)
            second = subprocess.run(cmd + ["compile", str(src), str(prefix)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(second.returncode, 2)
            self.assertIn("File exists", second.stderr)



if __name__ == "__main__":
    unittest.main()
