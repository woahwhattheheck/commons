from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import textwrap
import unittest

from clockwork_runtime_gate import GateError, compare_panels, normalize_row
from clockwork_source_audit import AuditError, audit_source_root, git_blob_sha1
from stage_clockwork_runtime import StageError, stage_runtime

H = "a" * 64
R = "b" * 64
E = "c" * 64
A = "d" * 64
S = "e" * 64


def row(**changes):
    base = {
        "candidate_sha256": H,
        "runtime_sha256": R,
        "engine_sha256": E,
        "opponent_id": "starter",
        "seed": 7,
        "seat": 0,
        "step": 42,
        "status": "completed",
        "fallback_stage": None,
        "action_sha256": A,
        "state_sha256": S,
        "elapsed_seconds": 0.1,
        "act_cpu_seconds": 0.09,
    }
    base.update(changes)
    return normalize_row(base, source="fixture", line=1)


class GateTests(unittest.TestCase):
    def test_stable_completed_passes(self):
        got = compare_panels([row()], [row()])
        self.assertTrue(got["passed"])
        self.assertEqual(got["rows"], 1)

    def test_action_mismatch_fails(self):
        got = compare_panels([row()], [row(action_sha256="f" * 64)])
        self.assertFalse(got["passed"])
        self.assertEqual(got["action_mismatch_count"], 1)

    def test_state_mismatch_fails(self):
        got = compare_panels([row()], [row(state_sha256="f" * 64)])
        self.assertFalse(got["passed"])
        self.assertEqual(got["state_mismatch_count"], 1)

    def test_loaded_only_selected_transform_fallback_fails(self):
        got = compare_panels(
            [row()],
            [row(status="deadline_fallback", fallback_stage="selected_transform")],
        )
        self.assertFalse(got["passed"])
        self.assertEqual(got["status_mismatch_count"], 1)
        self.assertEqual(got["loaded_fallbacks_by_stage"], {"selected_transform": 1})

    def test_symmetric_fallback_diagnostic_only(self):
        fallback = row(status="deadline_fallback", fallback_stage="selected_transform")
        self.assertFalse(compare_panels([fallback], [fallback])["passed"])
        self.assertTrue(compare_panels([fallback], [fallback], require_completed=False)["passed"])

    def test_duplicate_coordinate_rejected(self):
        with self.assertRaises(GateError):
            compare_panels([row(), row()], [row()])

    def test_coordinate_mismatch_rejected(self):
        with self.assertRaises(GateError):
            compare_panels([row()], [row(step=43)])

    def test_identity_mismatch_rejected(self):
        with self.assertRaises(GateError):
            compare_panels([row()], [row(candidate_sha256="f" * 64)])

    def test_nonfinite_telemetry_rejected(self):
        with self.assertRaises(GateError):
            row(elapsed_seconds=float("nan"))

    def test_bad_hash_rejected(self):
        with self.assertRaises(GateError):
            row(action_sha256="A" * 64)

    def test_bool_integer_rejected(self):
        with self.assertRaises(GateError):
            row(seed=True)


class SourceAuditTests(unittest.TestCase):
    def _fixture(self, root: Path):
        (root / "main.py").write_text("deadline marker\n", encoding="utf-8")
        blob = git_blob_sha1((root / "main.py").read_bytes())
        pins = root / "pins.json"
        pins.write_text(json.dumps({
            "schema": "titan-v4-clockwork-pins-v1",
            "canonical_branch": "main",
            "git_blobs": {"main.py": blob},
            "semantic_markers": {"main.py": ["deadline marker"]},
            "weave_output_git_blob": "f" * 40,
            "cutpoint": {"stage": "selected_transform"},
        }), encoding="utf-8")
        return pins

    def test_source_audit_accepts_exact_bytes_and_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); pins = self._fixture(root)
            self.assertTrue(audit_source_root(root, pins)["passed"])

    def test_source_audit_rejects_blob_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); pins = self._fixture(root)
            (root / "main.py").write_text("deadline marker changed\n", encoding="utf-8")
            got = audit_source_root(root, pins)
            self.assertFalse(got["passed"]); self.assertEqual(len(got["blob_mismatches"]), 1)

    def test_source_audit_rejects_unsafe_pinned_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); pins = self._fixture(root)
            raw = json.loads(pins.read_text())
            raw["git_blobs"] = {"../outside": "0" * 40}
            pins.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(AuditError):
                audit_source_root(root, pins)


class StageTests(unittest.TestCase):
    def _fake_composer(self, root: Path, suffix: bytes = b"optimized\n") -> Path:
        script = root / "composer.py"
        script.write_text(textwrap.dedent(f"""
            import pathlib, sys
            src=pathlib.Path(sys.argv[1]).read_bytes()
            pathlib.Path(sys.argv[2]).write_bytes(src+{suffix!r})
        """), encoding="utf-8")
        return script

    def test_stage_changes_only_selected_core(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "runtime"
            src.mkdir()
            selected = b"baseline\n"
            (src / "selected_sell_core.py").write_bytes(selected)
            (src / "main.py").write_text("main\n", encoding="utf-8")
            (src / "titan_runtime.py").write_text("runtime\n", encoding="utf-8")
            (src / "nested").mkdir()
            (src / "nested" / "x.txt").write_text("x\n", encoding="utf-8")
            composer = self._fake_composer(root)
            expected_out = git_blob_sha1(selected + b"optimized\n")
            out = root / "out"
            receipt = stage_runtime(
                input_runtime=src, output_runtime=out, composer=composer,
                expected_input_blob=git_blob_sha1(selected), expected_output_blob=expected_out,
                required_unchanged_blobs={
                    "main.py": git_blob_sha1((src / "main.py").read_bytes()),
                    "titan_runtime.py": git_blob_sha1((src / "titan_runtime.py").read_bytes()),
                },
            )
            self.assertTrue(receipt["passed"])
            self.assertEqual((out / "main.py").read_bytes(), (src / "main.py").read_bytes())
            self.assertEqual((out / "selected_sell_core.py").read_bytes(), selected + b"optimized\n")


    def test_stage_refuses_deadline_runtime_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "runtime"; src.mkdir()
            data = b"x"; (src / "selected_sell_core.py").write_bytes(data)
            (src / "main.py").write_text("stale", encoding="utf-8")
            with self.assertRaises(StageError):
                stage_runtime(input_runtime=src, output_runtime=root / "out",
                              composer=self._fake_composer(root), expected_input_blob=git_blob_sha1(data),
                              expected_output_blob="1"*40,
                              required_unchanged_blobs={"main.py": "0"*40})

    def test_stage_refuses_predecessor_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "runtime"; src.mkdir()
            (src / "selected_sell_core.py").write_text("x", encoding="utf-8")
            with self.assertRaises(StageError):
                stage_runtime(input_runtime=src, output_runtime=root / "out",
                              composer=self._fake_composer(root), expected_input_blob="0"*40,
                              expected_output_blob="1"*40)

    def test_stage_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "runtime"; src.mkdir(); out = root / "out"; out.mkdir()
            data = b"x"; (src / "selected_sell_core.py").write_bytes(data)
            with self.assertRaises(StageError):
                stage_runtime(input_runtime=src, output_runtime=out,
                              composer=self._fake_composer(root), expected_input_blob=git_blob_sha1(data),
                              expected_output_blob="1"*40)

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unavailable")
    def test_stage_refuses_symlink_member(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); src = root / "runtime"; src.mkdir()
            data = b"x"; (src / "selected_sell_core.py").write_bytes(data)
            target = root / "outside"; target.write_text("z", encoding="utf-8")
            os.symlink(target, src / "bad")
            with self.assertRaises(StageError):
                stage_runtime(input_runtime=src, output_runtime=root / "out",
                              composer=self._fake_composer(root), expected_input_blob=git_blob_sha1(data),
                              expected_output_blob="1"*40)


if __name__ == "__main__":
    unittest.main()
