from __future__ import annotations

import copy

from .acceptance import EXPECTED_HOLD_COUNTS, packet, run_acceptance
from .gate import HOLD_STATUS, READY_STATUS, ReadinessError, canonical_json, verify_readiness_package
from .test_support import BatchReadinessTestBase


class BatchReadinessTestsC(BatchReadinessTestBase):

    def test_fill_lineage_holds(self):
            raw = packet(17); raw["events"][6]["payload"]["lineageBatchId"] = "OTHER-BATCH"
            self.assertIn("FILL_LINEAGE_MISMATCH", self.hold_codes(self.compile(raw)))
    def test_stale_fill_evidence_holds(self):
            raw = packet(18); raw["events"][6]["observedAt"] = "2026-09-12T09:00:00Z"
            self.assertIn("FILL_INSPECTION_EVIDENCE_STALE", self.hold_codes(self.compile(raw)))
    def test_packaging_bom_holds(self):
            raw = packet(19); raw["events"][7]["payload"]["bomRevision"] = "BOM-OLD"
            self.assertIn("PACKAGING_BOM_MISMATCH", self.hold_codes(self.compile(raw)))
    def test_label_revision_holds(self):
            raw = packet(20); raw["events"][7]["payload"]["labelRevision"] = "LBL-OLD"
            self.assertIn("LABEL_REVISION_MISMATCH", self.hold_codes(self.compile(raw)))
    def test_device_assembly_holds(self):
            raw = packet(21); raw["events"][7]["payload"]["deviceAssemblyStatus"] = "HOLD"
            self.assertIn("DEVICE_ASSEMBLY_NOT_READY", self.hold_codes(self.compile(raw)))
    def test_open_deviation_holds(self):
            raw = packet(22); raw["events"][8]["payload"]["status"] = "OPEN"
            self.assertIn("OPEN_DEVIATION", self.hold_codes(self.compile(raw)))
    def test_missing_plan_holds(self):
            raw = packet(23); raw["events"] = [row for row in raw["events"] if row["kind"] != "BATCH_PLAN"]
            self.assertIn("BATCH_PLAN_MISSING", self.hold_codes(self.compile(raw)))
    def test_ambiguous_latest_state_holds(self):
            raw = packet(24); other = copy.deepcopy(raw ["events"][1]); other["eventId"] = "E-024-MA-OTHER"; other["payload"]["released"] = False; raw["events"].append(other)
            self.assertIn("AMBIGUOUS_LATEST_STATE", self.hold_codes(self.compile(raw)))