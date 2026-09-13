from __future__ import annotations

import copy

from .acceptance import EXPECTED_HOLD_COUNTS, packet, run_acceptance
from .gate import HOLD_STATUS, READY_STATUS, ReadinessError, canonical_json, verify_readiness_package
from .test_support import BatchReadinessTestBase


class BatchReadinessTestsB(BatchReadinessTestBase):

    def test_material_lot_mismatch_holds(self):
            raw = packet(9); raw["events"][1]["payload"]["lotId"] = "OTHER-LOT"
            self.assertIn("MATERIAL_LOT_MISMATCH", self.hold_codes(self.compile(raw)))
    def test_unreleased_material_holds(self):
            raw = packet(10); raw["events"][1]["payload"]["released"] = False
            self.assertIn("MATERIAL_NOT_RELEASED", self.hold_codes(self.compile(raw)))
    def test_missing_material_holds(self):
            raw = packet(11); raw["events"] = [row for row in raw["events"] if row["entityId"] != "MAT-B"]
            self.assertIn("MATERIAL_RELEASE_MISSING", self.hold_codes(self.compile(raw)))
    def test_equipment_not_ready_holds(self):
            raw = packet(12); raw["events"][3]["payload"]["status"] = "HOLD"
            self.assertIn("EQUIPMENT_NOT_READY", self.hold_codes(self.compile(raw)))
    def test_expired_calibration_holds(self):
            raw = packet(13); raw["events"][3]["payload"]["calibrationValidThrough"] = "2026-09-13T09:00:00Z"
            self.assertIn("CALIBRATION_EXPIRED", self.hold_codes(self.compile(raw)))
    def test_missing_equipment_holds(self):
            raw = packet(14); raw["events"] = [row for row in raw["events"] if row["entityId"] != "INSPECTOR-1"]
            self.assertIn("EQUIPMENT_STATUS_MISSING", self.hold_codes(self.compile(raw)))
    def test_environment_state_holds(self):
            raw = packet(15); raw["events"][5]["payload"]["isolatorState"] = "HOLD"
            self.assertIn("ENVIRONMENT_NOT_READY", self.hold_codes(self.compile(raw)))
    def test_stale_environment_holds(self):
            raw = packet(16); raw["events"][5]["observedAt"] = "2026-09-13T01:00:00Z"
            self.assertIn("ENVIRONMENT_EVIDENCE_STALE", self.hold_codes(self.compile(raw)))