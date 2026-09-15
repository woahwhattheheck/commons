from __future__ import annotations

import os
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import engine


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
        self, captured: datetime, updated: datetime | None = None
    ) -> tuple[dict[str, object], dict[str, object]]:
        row = self._row(updated or captured)
        return (
            self._snapshot("SOURCE_SITE", "SNAP-SOURCE", row, captured),
            self._snapshot("RECEIVING_SITE", "SNAP-RECEIVING", row, captured),
        )

    def test_row_after_snapshot_capture_fails_closed(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=3)
        source, receiving = self._pair(captured, captured + timedelta(minutes=1))
        as_of = engine.format_utc(captured + timedelta(minutes=2))
        with self.assertRaisesRegex(engine.TransferError, "later than snapshot capture"):
            engine.compile_transfer(source, receiving, {"max_evidence_age_minutes": 60}, as_of=as_of)

    def test_retained_compile_graph_uses_repaired_chronology_gate(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=3)
        source, receiving = self._pair(captured, captured + timedelta(minutes=1))
        with self.assertRaisesRegex(engine.TransferError, "later than snapshot capture"):
            engine._impl.compile_transfer(
                source,
                receiving,
                {"max_evidence_age_minutes": 60},
                as_of=engine.format_utc(captured + timedelta(minutes=2)),
            )

    def test_historical_replay_is_distinct_from_current_verification(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)
        source, receiving = self._pair(captured)
        report = engine.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 1},
            as_of=engine.format_utc(captured + timedelta(seconds=30)),
        )
        self.assertEqual(report["summary"]["state"], "TRANSFER_READY_FOR_OWNER_REVIEW")
        self.assertTrue(engine.verify_report(report)["verified"])
        with self.assertRaisesRegex(engine.TransferError, "report is no longer current"):
            engine.verify_report_current(report)

    def test_same_hold_state_with_changed_semantics_fails_current_verification(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)
        source, receiving = self._pair(captured)
        report = engine.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 1},
            as_of=engine.format_utc(captured + timedelta(minutes=2)),
        )
        self.assertEqual(report["summary"]["state"], "HOLD_FOR_OWNER_RECONCILIATION")
        self.assertEqual(report["results"][0]["classification"], "STALE_EVIDENCE")
        self.assertTrue(engine.verify_report(report)["verified"])
        with self.assertRaisesRegex(engine.TransferError, "decision semantics changed"):
            engine.verify_report_current(report)

    def test_recent_report_passes_current_verification(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=1)
        source, receiving = self._pair(captured)
        report = engine.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 60},
            as_of=engine.format_utc(datetime.now(timezone.utc).replace(microsecond=0)),
        )
        result = engine.verify_report_current(report)
        self.assertTrue(result["verified"])
        self.assertTrue(result["historical_replay_verified"])
        self.assertEqual(result["state"], "TRANSFER_READY_FOR_OWNER_REVIEW")
        self.assertIn("current_as_of", result)

    def test_current_verifier_clock_is_bound_against_module_global_rebind(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)
        source, receiving = self._pair(captured)
        historical_as_of = engine.format_utc(captured + timedelta(seconds=30))
        report = engine.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 1},
            as_of=historical_as_of,
        )
        with mock.patch.object(engine, "_process_utc_now", return_value=historical_as_of):
            with self.assertRaisesRegex(engine.TransferError, "report is no longer current"):
                engine.verify_report_current(report)

    def test_production_verify_cli_rechecks_freshness(self) -> None:
        captured = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=10)
        source, receiving = self._pair(captured)
        report = engine.compile_transfer(
            source,
            receiving,
            {"max_evidence_age_minutes": 1},
            as_of=engine.format_utc(captured + timedelta(seconds=30)),
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "report.json"
            path.write_bytes(engine.canonical_json_bytes(report))
            with self.assertRaisesRegex(engine.TransferError, "report is no longer current"):
                engine._verify_cli(Namespace(report=str(path), markdown=None))

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
