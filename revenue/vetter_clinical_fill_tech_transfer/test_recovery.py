from __future__ import annotations

import importlib.util
import inspect
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import engine
import historical


class RecoveryBoundaryTests(unittest.TestCase):
    def _row(self, updated: datetime) -> dict[str, object]:
        stamp = engine.format_utc(updated)
        return {
            "project_id": "PROJECT-1",
            "molecule_id": "MOLECULE-1",
            "batch_id": "BATCH-1",
            "site_id": "SITE-CHI",
            "receiving_site_id": "SITE-RANK",
            "process_version": "PROC-1",
            "method_version": "METHOD-1",
            "container_configuration": "vial-config-1",
            "equipment_id": "EQ-1",
            "equipment_calibration_sha256": "1" * 64,
            "operator_qualification_sha256": "2" * 64,
            "qc_inspection_sha256": "3" * 64,
            "microbiology_evidence_sha256": "4" * 64,
            "storage_condition": "2-8C",
            "transfer_evidence_sha256": "5" * 64,
            "release_evidence_sha256": "6" * 64,
            "last_updated_utc": stamp,
        }

    def _snapshot(
        self,
        role: str,
        snapshot_id: str,
        row: dict[str, object],
        captured: datetime,
    ) -> dict[str, object]:
        rows = [dict(row)]
        return {
            "snapshot_id": snapshot_id,
            "system_role": role,
            "schema_revision": "SCHEMA-1",
            "transfer_generation": "GEN-1",
            "captured_at_utc": engine.format_utc(captured),
            "complete_export": True,
            "rows_sha256": engine.canonical_sha256(rows),
            "rows": rows,
        }

    def _pair(
        self,
        captured: datetime,
        updated: datetime | None = None,
    ) -> tuple[dict[str, object], dict[str, object]]:
        row = self._row(updated or captured)
        return (
            self._snapshot("SOURCE_SITE", "SNAP-SOURCE", row, captured),
            self._snapshot("RECEIVING_SITE", "SNAP-RECEIVING", row, captured),
        )

    def test_row_after_snapshot_capture_fails_closed_in_historical_lane(self) -> None:
        captured = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
        source, receiving = self._pair(captured, captured + timedelta(seconds=1))
        with self.assertRaisesRegex(engine.TransferError, "later than snapshot capture"):
            historical.compile_transfer(
                source,
                receiving,
                {"max_evidence_age_minutes": 60},
                as_of=engine.format_utc(captured + timedelta(minutes=1)),
            )

    def test_supported_current_compiler_has_no_as_of_parameter(self) -> None:
        params = tuple(inspect.signature(engine.compile_transfer).parameters)
        self.assertEqual(params, ("source", "receiving", "policy"))
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=2)
        source, receiving = self._pair(captured)
        with self.assertRaises(TypeError):
            engine.compile_transfer(
                source,
                receiving,
                {"max_evidence_age_minutes": 60},
                as_of=engine.format_utc(captured),
            )

    def test_supported_current_verifier_has_report_only(self) -> None:
        params = tuple(inspect.signature(engine.verify_report_current).parameters)
        self.assertEqual(params, ("report",))

    def test_current_module_does_not_expose_raw_core_or_authority_factory(self) -> None:
        for name in (
            "_impl",
            "_core",
            "_make_current_verifier",
            "_build_current_capabilities",
            "_load_private_core",
            "_install_snapshot_chronology",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(engine, name))
        self.assertIsNone(importlib.util.find_spec("_engine_v1"))

    def test_historical_explicit_time_is_distinct_noncurrent_authority(self) -> None:
        captured = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
        source, receiving = self._pair(captured)
        envelope = historical.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 60},
            as_of=engine.format_utc(captured + timedelta(seconds=1)),
        )
        self.assertEqual(
            envelope["schema"], historical.HISTORICAL_REPORT_SCHEMA
        )
        self.assertEqual(
            envelope["authority_mode"], "HISTORICAL_INTEGRITY_ONLY"
        )
        self.assertNotIn("state", envelope)
        self.assertNotIn("current_receipt_sha256", envelope)
        result = historical.verify_report(envelope)
        self.assertEqual(
            result["schema"], historical.HISTORICAL_VERIFY_SCHEMA
        )
        self.assertEqual(
            result["authority_mode"], "HISTORICAL_INTEGRITY_ONLY"
        )
        self.assertNotIn("state", result)
        self.assertIn("historical_decision_state", result)

    def test_current_compiler_emits_current_envelope_only_from_process_clock(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=2)
        source, receiving = self._pair(captured)
        report = engine.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 60},
        )
        self.assertEqual(report["schema"], engine.CURRENT_REPORT_SCHEMA)
        self.assertEqual(report["authority_mode"], "CURRENT_OWNER_REVIEW")
        self.assertEqual(report["evaluated_at_utc"], report["decision"]["as_of"])
        self.assertIn("current_receipt_sha256", report)
        self.assertNotIn("historical_receipt_sha256", report)

    def test_current_verifier_rejects_historical_envelope(self) -> None:
        captured = datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc)
        source, receiving = self._pair(captured)
        envelope = historical.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 60},
            as_of=engine.format_utc(captured + timedelta(seconds=1)),
        )
        with self.assertRaisesRegex(engine.TransferError, "current report key set"):
            engine.verify_report_current(envelope)

    def test_recent_current_report_verifies(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=2)
        source, receiving = self._pair(captured)
        report = engine.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 60},
        )
        result = engine.verify_report_current(report)
        self.assertTrue(result["verified"])
        self.assertEqual(result["authority_mode"], "CURRENT_OWNER_REVIEW")
        self.assertEqual(
            result["decision_state"], "TRANSFER_READY_FOR_OWNER_REVIEW"
        )

    def test_current_verifier_resamples_process_time_and_expires_ready(self) -> None:
        # 116 seconds old is still inside the inclusive 1-minute bucket because
        # the retained classifier floors age to whole minutes.  Five seconds of
        # real process time moves it past the >1-minute stale threshold without
        # any injectable clock or caller-selected as_of.
        now = datetime.now(timezone.utc).replace(microsecond=0)
        captured = now - timedelta(seconds=2)
        updated = now - timedelta(seconds=116)
        source, receiving = self._pair(captured, updated)
        report = engine.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 1},
        )
        self.assertEqual(
            report["decision"]["summary"]["state"],
            "TRANSFER_READY_FOR_OWNER_REVIEW",
        )
        time.sleep(5)
        with self.assertRaisesRegex(engine.TransferError, "no longer current"):
            engine.verify_report_current(report)

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "platform lacks O_NOFOLLOW")
    def test_final_input_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target.json"
            link = root / "input.json"
            target.write_bytes(b"{}")
            os.symlink(target, link)
            with self.assertRaisesRegex(engine.TransferError, "symlink|safely"):
                engine._read_bounded(link)

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "platform lacks O_NOFOLLOW")
    def test_same_size_path_replacement_cannot_swap_open_generation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "input.json"
            replacement = root / "replacement.json"
            original_bytes = b"A" * 8192
            replacement_bytes = b"B" * len(original_bytes)
            path.write_bytes(original_bytes)
            replacement.write_bytes(replacement_bytes)
            real_read = os.read
            swapped = False

            def read_after_swap(fd: int, size: int) -> bytes:
                nonlocal swapped
                if not swapped:
                    os.replace(replacement, path)
                    swapped = True
                return real_read(fd, size)

            with mock.patch.object(engine.os, "read", side_effect=read_after_swap):
                observed = engine._read_bounded(path)
            self.assertTrue(swapped)
            self.assertEqual(observed, original_bytes)
            self.assertEqual(path.read_bytes(), replacement_bytes)

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "platform lacks O_NOFOLLOW")
    def test_byte_cap_is_enforced_during_consumption(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "input.json"
            path.write_bytes(b"x")
            with mock.patch.object(engine, "MAX_JSON_BYTES", 32), mock.patch.object(
                engine.os, "read", return_value=b"x" * 33
            ):
                with self.assertRaisesRegex(engine.TransferError, "during read"):
                    engine._read_bounded(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
