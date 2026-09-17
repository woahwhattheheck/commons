from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
import unittest

from tools.exact_head_ship_fence import fence
from tools.exact_head_ship_fence import _core
from tools.exact_head_ship_fence.cli import _write_bundle
from tools.exact_head_ship_fence.fence import AUTHORITY, EvidenceError, compile_current
from tools.exact_head_ship_fence.test_fence import packet


class AuthoritySeal(unittest.TestCase):
    def test_public_authority_is_immutable_and_rebind_is_ignored(self):
        with self.assertRaises(TypeError):
            AUTHORITY["merge_authorized"] = True
        old = fence.AUTHORITY
        try:
            fence.AUTHORITY = {"merge_authorized": True}
            report = compile_current(packet())
            self.assertFalse(any(report["authority"].values()))
        finally:
            fence.AUTHORITY = old

    def test_core_authority_in_place_mutation_fails_closed(self):
        old = dict(_core.AUTHORITY)
        try:
            _core.AUTHORITY["merge_authorized"] = True
            with self.assertRaises(EvidenceError):
                compile_current(packet())
        finally:
            _core.AUTHORITY.clear(); _core.AUTHORITY.update(old)

    def test_core_authority_rebind_fails_closed(self):
        old = _core.AUTHORITY
        try:
            _core.AUTHORITY = {**old, "merge_authorized": True}
            with self.assertRaises(EvidenceError):
                compile_current(packet())
        finally:
            _core.AUTHORITY = old

    def test_core_builder_classifier_and_helper_rebind_fail_closed(self):
        for name in ("_build", "_class", "_sha"):
            with self.subTest(name=name):
                old = getattr(_core, name)
                try:
                    setattr(_core, name, lambda *a, **k: None)
                    with self.assertRaises(EvidenceError):
                        compile_current(packet())
                finally:
                    setattr(_core, name, old)

    def test_public_integrity_helper_rebind_does_not_change_semantics(self):
        old = fence._freeze
        try:
            fence._freeze = lambda value: ("forged",)
            report = compile_current(packet())
            self.assertEqual(report["verdict"], "READY_TO_MERGE_EVIDENCE")
            self.assertFalse(any(report["authority"].values()))
        finally:
            fence._freeze = old

    def test_reviewer_quorum_requires_distinct_identities(self):
        evidence = packet(); evidence["review_policy"]["min_passes"] = 2
        replay = deepcopy(evidence["reviews"][0]); replay["review_id"] = "review-2"
        evidence["reviews"].append(replay)
        with self.assertRaises(EvidenceError):
            compile_current(evidence)
        evidence["reviews"][1]["reviewer"] = "second-independent-reviewer"
        self.assertEqual(compile_current(evidence)["verdict"], "READY_TO_MERGE_EVIDENCE")

    def test_public_clock_rebind_cannot_supply_historical_time(self):
        old = fence._CURRENT_CLOCK
        try:
            fence._CURRENT_CLOCK = lambda: datetime(2000, 1, 1, tzinfo=timezone.utc)
            self.assertEqual(compile_current(packet())["verdict"], "READY_TO_MERGE_EVIDENCE")
            with self.assertRaises(TypeError):
                compile_current(packet(), _clock=fence._CURRENT_CLOCK)
        finally:
            fence._CURRENT_CLOCK = old


class OutputCustody(unittest.TestCase):
    def test_output_directory_remint_is_detected_and_foreign_dir_preserved(self):
        report = compile_current(packet())
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); out = root / "out"; displaced = root / "displaced"
            def remint(path: Path) -> None:
                os.rename(path, displaced)
                os.mkdir(path, 0o700)
            with self.assertRaises(EvidenceError):
                _write_bundle(out, report, _after_first=remint)
            self.assertTrue(out.is_dir())
            self.assertEqual(list(out.iterdir()), [])
            self.assertTrue(displaced.is_dir())

    def test_rollback_preserves_foreign_member_successor(self):
        report = compile_current(packet())
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            def replace_and_block(path: Path) -> None:
                os.rename(path / "report.json", path / "owned.old")
                (path / "report.json").write_text("FOREIGN", encoding="utf-8")
                (path / "report.md").write_text("BLOCK", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                _write_bundle(out, report, _after_first=replace_and_block)
            self.assertEqual((out / "report.json").read_text(encoding="utf-8"), "FOREIGN")
            self.assertEqual((out / "report.md").read_text(encoding="utf-8"), "BLOCK")
            self.assertTrue((out / "owned.old").exists())


if __name__ == "__main__":
    unittest.main()
