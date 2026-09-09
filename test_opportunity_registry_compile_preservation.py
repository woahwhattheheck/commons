#!/usr/bin/env python3
"""Compile real opportunity inputs without replacing outputs on validation errors."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "host/opportunity_registry.py"
SPEC = importlib.util.spec_from_file_location("opportunity_compile_preservation", SCRIPT)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


class OpportunityCompilePreservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        seed = json.loads((ROOT / mod.SEED_PATH).read_text(encoding="utf-8"))
        # Copy real compiler inputs and receipt bytes; no network or mocked compiler.
        sources = {mod.SEED_PATH, mod.SCHEMA_PATH, Path("titan-hour.html")}
        sources.update(Path(item["path"]) for item in seed["compose"])
        for capability in seed["capabilities"]:
            sources.update(Path(path) for path in capability["receipts"])
        for relative in sorted(sources):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)

    def run_cli(self, command="compile"):
        return subprocess.run(
            [sys.executable, str(SCRIPT), command, "--root", str(self.root)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): (
                "directory" if path.is_dir()
                else hashlib.sha256(path.read_bytes()).hexdigest()
            )
            for path in sorted(self.root.rglob("*"))
        }

    def seed_prior_outputs(self):
        registry = mod.compile_registry(self.root)
        outputs = [mod.REGISTRY_PATH, mod.HTML_PATH, mod.PROOF_PATH]
        outputs += [mod.PACKET_DIR / "README.md"]
        outputs += [
            mod.PACKET_DIR / (row["packet_id"] + ".md")
            for row in registry["opportunities"]
        ]
        for relative in outputs:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(("prior output: " + relative.as_posix() + "\n").encode())

    def invalidate_url(self):
        path = self.root / "revenue/ip/grants_ledger.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["programs"][0]["official_urls"] = ["http://example.invalid/not-https"]
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    def assert_rejected_without_writes(self, expected_error):
        before = self.snapshot()
        result = self.run_cli()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(expected_error, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.snapshot(), before, "rejected compilation changed the tree")

    def test_invalid_candidate_preserves_existing_outputs(self):
        self.seed_prior_outputs()
        self.invalidate_url()
        self.assert_rejected_without_writes("must be HTTPS")

    def test_invalid_candidate_creates_no_outputs(self):
        self.invalidate_url()
        self.assertFalse((self.root / mod.REGISTRY_PATH).exists())
        self.assertFalse((self.root / mod.PACKET_DIR).exists())
        self.assert_rejected_without_writes("must be HTTPS")

    def test_invalid_schema_preserves_existing_outputs(self):
        self.seed_prior_outputs()
        path = self.root / mod.SCHEMA_PATH
        data = json.loads(path.read_text(encoding="utf-8"))
        data["$schema"] = "unsupported-schema"
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")
        self.assert_rejected_without_writes("schema draft mismatch")

    def test_valid_compile_replaces_all_generated_outputs(self):
        self.seed_prior_outputs()
        expected = mod.compile_registry(self.root)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(result.stdout)
        self.assertEqual(status["status"], "COMPILED")
        self.assertEqual(status["validation"], "VALID")
        self.assertEqual(status["opportunities"], len(expected["opportunities"]))
        self.assertEqual(
            (self.root / mod.REGISTRY_PATH).read_text(encoding="utf-8"),
            json.dumps(expected, indent=2, ensure_ascii=False) + "\n",
        )
        self.assertEqual(
            (self.root / mod.HTML_PATH).read_text(encoding="utf-8"),
            mod.render_opportunity_html(expected),
        )
        self.assertEqual(
            (self.root / mod.PROOF_PATH).read_text(encoding="utf-8"),
            mod.render_proof_html(expected),
        )
        index = (self.root / mod.PACKET_DIR / "README.md").read_text(encoding="utf-8")
        for row in expected["opportunities"]:
            relative = mod.PACKET_DIR / (row["packet_id"] + ".md")
            self.assertEqual(
                (self.root / relative).read_text(encoding="utf-8"),
                mod.render_packet(row, expected["capabilities"]),
            )
            self.assertIn("./" + row["packet_id"] + ".md", index)

    def test_valid_compile_is_repeatable_and_keeps_unrelated_files(self):
        unrelated = self.root / mod.PACKET_DIR / "unrelated-existing-note.md"
        unrelated.parent.mkdir(parents=True, exist_ok=True)
        unrelated.write_bytes(b"keep this independent note\n")
        first = self.run_cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.snapshot()
        second = self.run_cli()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout, first.stdout)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(unrelated.read_bytes(), b"keep this independent note\n")

    def test_read_commands_remain_read_only(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.snapshot()
        for command in ("validate", "list", "due", "next"):
            with self.subTest(command=command):
                result = self.run_cli(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIsInstance(json.loads(result.stdout), dict)
                self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
