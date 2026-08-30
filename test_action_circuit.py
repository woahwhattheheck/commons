#!/usr/bin/env python3
"""Canary: Action Pad ordered circuits are real, additive, and add no gate."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import action_executor as ae

PYTHON_SHELL = ("& " if sys.platform.startswith("win") else "") + f'"{sys.executable}"'
ROOT = Path(__file__).resolve().parent


class ActionCircuitTests(unittest.TestCase):
    def init_repo(self, root):
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
        (root / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)

    def test_split_circuit_verbs_keeps_every_nonempty_token(self):
        self.assertEqual(
            ae.split_circuit_verbs("PUSH, MAKE IT SO | RUN\nWIBBLE"),
            ["PUSH", "MAKE IT SO", "RUN", "WIBBLE"],
        )
        self.assertEqual(ae.split_circuit_verbs(""), [])

    def test_parse_record_single_verb_payload_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "a.md"
            path.write_text(
                "from: SOL\nto: TOOLS\nid: sol-action-0001\nkind: ACTION\n"
                "act: MAKE IT SO\ntarget: out.txt\n\n---\n\n"
                "MAKE IT SO\ntarget: out.txt\n\nhello",
                encoding="utf-8",
            )
            rec = ae.parse_record(path)
            self.assertEqual(rec["verb"], "MAKE IT SO")
            self.assertEqual(rec["target"], "out.txt")
            self.assertEqual(rec["payload"], "hello")
            self.assertIsNone(ae.parse_circuit_steps(rec))

    def test_two_step_push_then_run_runs_in_order(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            results = root / "actions" / "results"
            script = root / "chain.py"
            script.write_text(
                "from pathlib import Path\n"
                "p = Path('out/first.txt')\n"
                "Path('out/second.txt').write_text(p.read_text() + 'second\\n', encoding='utf-8')\n",
                encoding="utf-8",
            )
            rec = {
                "meta": {
                    "id": "circuit-order-0001",
                    "from": "UNSEATED",
                    "circuit": "PUSH, RUN",
                },
                "verb": "CIRCUIT",
                "target": "",
                "payload": (
                    "---STEP---\n"
                    "target: out/first.txt\n"
                    "first-bytes\n"
                    "---STEP---\n"
                    f"{PYTHON_SHELL} chain.py"
                ),
            }
            with mock.patch.object(ae, "ROOT", root), mock.patch.object(ae, "RESULTS", results):
                result = ae.execute(rec, "github")
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["circuit"])
            self.assertIsNone(result["failed_step"])
            self.assertEqual([row["verb"] for row in result["steps"]], ["PUSH", "RUN"])
            self.assertEqual([row["step"] for row in result["steps"]], [1, 2])
            self.assertTrue(all(row["ok"] for row in result["steps"]))
            self.assertEqual((root / "out" / "first.txt").read_text(encoding="utf-8"), "first-bytes")
            self.assertEqual(
                (root / "out" / "second.txt").read_text(encoding="utf-8"),
                "first-bytessecond\n",
            )
            step1 = results / "circuit-order-0001-s01.json"
            step2 = results / "circuit-order-0001-s02.json"
            self.assertTrue(step1.is_file())
            self.assertTrue(step2.is_file())
            first = json.loads(step1.read_text(encoding="utf-8"))
            second = json.loads(step2.read_text(encoding="utf-8"))
            self.assertEqual(first["verb"], "PUSH")
            self.assertEqual(second["verb"], "RUN")
            self.assertEqual(first["step"], 1)
            self.assertEqual(second["step"], 2)
            self.assertIn("out/first.txt", result["action_outputs"])
            self.assertEqual(
                result["action_outputs"]["out/first.txt"],
                hashlib.sha256((root / "out" / "first.txt").read_bytes()).hexdigest(),
            )

    def test_verb_headed_circuit_paste_and_json_circuit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            results = root / "actions" / "results"
            headed = {
                "meta": {"id": "circuit-headed-0001", "circuit": "PUSH, RUN"},
                "verb": "ACTION",
                "target": "",
                "payload": (
                    "PUSH\n"
                    "target: headed.txt\n"
                    "from-lines\n"
                    "RUN\n"
                    f'{PYTHON_SHELL} -c "from pathlib import Path; Path(\'headed-ran.txt\').write_text(\'ok\')"'
                ),
            }
            json_rec = {
                "meta": {"id": "circuit-json-0001"},
                "verb": "CIRCUIT",
                "target": "",
                "payload": json.dumps([
                    {"verb": "PUSH", "target": "json.txt", "payload": "from-json\n"},
                    {
                        "verb": "WIBBLE",
                        "payload": f'{PYTHON_SHELL} -c "from pathlib import Path; Path(\'json-ran.txt\').write_text(\'free\')"',
                    },
                ]),
            }
            with mock.patch.object(ae, "ROOT", root), mock.patch.object(ae, "RESULTS", results):
                line_result = ae.execute(headed, "github")
                json_result = ae.execute(json_rec, "github")
            self.assertTrue(line_result["ok"], line_result)
            self.assertTrue(json_result["ok"], json_result)
            self.assertEqual((root / "headed.txt").read_text(encoding="utf-8"), "from-lines")
            self.assertEqual((root / "headed-ran.txt").read_text(encoding="utf-8"), "ok")
            self.assertEqual((root / "json.txt").read_text(encoding="utf-8"), "from-json\n")
            self.assertEqual((root / "json-ran.txt").read_text(encoding="utf-8"), "free")
            self.assertEqual([row["verb"] for row in json_result["steps"]], ["PUSH", "WIBBLE"])

    def test_single_verb_push_still_works(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            rec = {
                "meta": {"id": "single-verb-0001", "from": "UNSEATED"},
                "verb": "PUSH",
                "target": "solo.txt",
                "payload": "just-one\n",
            }
            with mock.patch.object(ae, "ROOT", root):
                result = ae.execute(rec, "github")
            self.assertTrue(result["ok"], result)
            self.assertNotIn("circuit", result)
            self.assertEqual((root / "solo.txt").read_text(encoding="utf-8"), "just-one\n")
            self.assertEqual(result["changed"], ["solo.txt"])

    def test_composition_adds_no_identity_approval_allowlist(self):
        source = (ROOT / "action_executor.py").read_text(encoding="utf-8")
        door = (ROOT / "ground" / "ACTION_DOOR.md").read_text(encoding="utf-8")
        html = (ROOT / "action.html").read_text(encoding="utf-8")
        circuit_fn = source[source.index("def parse_circuit_steps"):source.index("def execute_circuit")]
        runner = source[source.index("def execute_circuit"):source.index("def is_device_target")]
        for blob in (circuit_fn, runner):
            self.assertNotIn("ALLOWED_VERBS", blob)
            self.assertNotIn("verb allowlist", blob.lower())
            self.assertNotIn("approval required", blob.lower())
            self.assertNotIn("unauthorized", blob.lower())
            self.assertNotIn("permission denied", blob.lower())
            self.assertNotIn("identity required", blob.lower())
            self.assertNotIn("if verb not in", blob)
        self.assertIn("No identity/approval/allowlist", runner)
        self.assertIn("There is no verb allowlist", door)
        self.assertIn("Composition adds no identity", door)
        self.assertNotIn('<select id="verb"', html)
        self.assertNotIn('name="circuit" required', html)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            rec = {
                "meta": {"id": "circuit-open-0001", "from": "", "circuit": "PUSH, COMPUTE WHATEVER"},
                "verb": "CIRCUIT",
                "target": "",
                "payload": (
                    "---STEP---\n"
                    "target: open.txt\n"
                    "unseated\n"
                    "---STEP---\n"
                    f'{PYTHON_SHELL} -c "from pathlib import Path; Path(\'open-ran.txt\').write_text(\'yes\')"'
                ),
            }
            with mock.patch.object(ae, "ROOT", root):
                result = ae.execute(rec, "github")
            self.assertTrue(result["ok"], result)
            self.assertEqual([row["verb"] for row in result["steps"]], ["PUSH", "COMPUTE WHATEVER"])
            self.assertEqual((root / "open.txt").read_text(encoding="utf-8"), "unseated")
            self.assertEqual((root / "open-ran.txt").read_text(encoding="utf-8"), "yes")

    def test_circuit_failure_names_step_and_is_not_a_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            results = root / "actions" / "results"
            rec = {
                "meta": {"id": "circuit-fail-0001", "circuit": "PUSH, RUN, PUSH"},
                "verb": "CIRCUIT",
                "target": "",
                "payload": (
                    "---STEP---\n"
                    "target: kept.txt\n"
                    "survived\n"
                    "---STEP---\n"
                    f'{PYTHON_SHELL} -c "raise SystemExit(7)"\n'
                    "---STEP---\n"
                    "target: never.txt\n"
                    "should-not-write\n"
                ),
            }
            with mock.patch.object(ae, "ROOT", root), mock.patch.object(ae, "RESULTS", results):
                result = ae.execute(rec, "github")
            self.assertFalse(result["ok"])
            self.assertEqual(result["failed_step"], 2)
            self.assertIn("circuit step 2 (RUN) failed", result["error"])
            self.assertNotRegex(result["error"].lower(), r"permission|approval|allowlist|unauthorized|identity")
            self.assertEqual(len(result["steps"]), 2)
            self.assertTrue(result["steps"][0]["ok"])
            self.assertFalse(result["steps"][1]["ok"])
            self.assertEqual((root / "kept.txt").read_text(encoding="utf-8"), "survived")
            self.assertFalse((root / "never.txt").exists())

    def test_patch_payload_with_dashes_is_not_stolen_as_a_circuit(self):
        patch = """diff --git a/open.txt b/open.txt
new file mode 100644
--- /dev/null
+++ b/open.txt
@@ -0,0 +1 @@
+open door
"""
        rec = {
            "meta": {"id": "sol-action-patch-1", "from": "SOL"},
            "verb": "PATCH",
            "target": "repo",
            "payload": patch,
        }
        self.assertIsNone(ae.parse_circuit_steps(rec))
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            with mock.patch.object(ae, "ROOT", root):
                result = ae.execute(rec, "github")
            self.assertTrue(result["ok"])
            self.assertNotIn("circuit", result)
            self.assertEqual((root / "open.txt").read_text(encoding="utf-8"), "open door\n")


if __name__ == "__main__":
    unittest.main()
