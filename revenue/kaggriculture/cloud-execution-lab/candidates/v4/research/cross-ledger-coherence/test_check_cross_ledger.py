from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import check_cross_ledger as cross

ROOT = cross.EXPECTED_ROOT


def fixture():
    canonical = {
        "canonical_branch": "main",
        "workspace": ROOT,
        "production_target": "revenue/kaggriculture/cloud-execution-lab",
        "production_archive": "revenue/kaggriculture/cloud-execution-lab/exports/titan-current.tar.gz",
        "entrypoint": "main.py::agent",
    }
    integration = {
        "schema": cross.INTEGRATION_SCHEMA,
        "canonical_branch": "main",
        "workspace": ROOT,
        "production_target": canonical["production_target"],
        "production_archive": canonical["production_archive"],
        "entrypoint": canonical["entrypoint"],
        "landed": [
            {
                "lane": "fast clone",
                "repair_path": "repairs/performance/fast-tape-clone",
                "status": "current_abi_port_component_tested_not_runtime_promoted",
            },
            {
                "lane": "row shed",
                "repair_path": "repairs/gameplay/row-shed-sell-order",
                "composition_intake_pr": 12777,
                "composition_state": "blocked",
                "status": "source_component_tested_not_runtime_materialized",
            },
        ],
        "negative_or_parked": [],
    }
    composition = {
        "schema": cross.COMPOSITION_SCHEMA,
        "canonical_branch": "main",
        "canonical_root": ROOT,
        "components": [
            {
                "id": "fast-tape-clone-current-runtime",
                "state": "compose",
                "package": "repairs/performance/fast-tape-clone",
            },
            {
                "id": "row-shed-sell-order",
                "state": "blocked",
                "package": "repairs/gameplay/row-shed-sell-order",
            },
        ],
    }
    return canonical, integration, composition


class CrossLedgerTests(unittest.TestCase):
    def test_coherent_fixture_passes(self):
        result = cross.audit(*fixture())
        self.assertTrue(result["ok"], result)
        self.assertEqual([], result["unmapped_compose_components"])
        self.assertEqual(2, len(result["mappings"]))
        self.assertFalse(result["policy"]["decision_authority"])

    def test_compose_without_landed_custody_fails(self):
        canonical, integration, composition = fixture()
        composition["components"].append({
            "id": "orphan-runtime-edge",
            "state": "compose",
            "package": "repairs/performance/orphan-runtime-edge",
        })
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertIn("orphan-runtime-edge", result["unmapped_compose_components"])
        self.assertTrue(any(e["code"] == "compose_without_landed_custody" for e in result["errors"]))

    def test_blocked_without_landed_path_is_warning_not_false_custody(self):
        canonical, integration, composition = fixture()
        composition["components"].append({
            "id": "research-hold",
            "state": "blocked",
            "package": "research/some-hold",
        })
        result = cross.audit(canonical, integration, composition)
        self.assertTrue(result["ok"], result)
        self.assertTrue(any(w["code"] == "noncompose_without_exact_landed_path" for w in result["warnings"]))

    def test_explicit_blocked_link_must_exist(self):
        canonical, integration, composition = fixture()
        composition["components"] = [c for c in composition["components"] if c["id"] != "row-shed-sell-order"]
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "landed_composition_link_missing_component" for e in result["errors"]))

    def test_explicit_state_split_brain_fails(self):
        canonical, integration, composition = fixture()
        integration["landed"][1]["composition_state"] = "compose"
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "composition_state_split_brain" for e in result["errors"]))

    def test_intake_pr_without_state_fails(self):
        canonical, integration, composition = fixture()
        del integration["landed"][1]["composition_state"]
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "composition_intake_without_state" for e in result["errors"]))

    def test_boolean_intake_pr_rejected(self):
        canonical, integration, composition = fixture()
        integration["landed"][1]["composition_intake_pr"] = True
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "bad_composition_intake_pr" for e in result["errors"]))

    def test_duplicate_landed_repair_path_fails(self):
        canonical, integration, composition = fixture()
        integration["landed"].append({
            "lane": "duplicate clone custody",
            "repair_path": "repairs/performance/fast-tape-clone",
            "status": "source_only",
        })
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "duplicate_landed_repair_path" for e in result["errors"]))

    def test_duplicate_component_package_fails(self):
        canonical, integration, composition = fixture()
        composition["components"].append({
            "id": "second-clone-owner",
            "state": "blocked",
            "package": "repairs/performance/fast-tape-clone",
        })
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "duplicate_component_package" for e in result["errors"]))

    def test_branch_split_brain_fails_even_if_two_agree(self):
        canonical, integration, composition = fixture()
        canonical["canonical_branch"] = "v4-next"
        integration["canonical_branch"] = "v4-next"
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        codes = {e["code"] for e in result["errors"]}
        self.assertIn("wrong_canonical_branch", codes)
        self.assertIn("branch_split_brain", codes)

    def test_root_split_brain_fails(self):
        canonical, integration, composition = fixture()
        composition["canonical_root"] = "revenue/kaggriculture/cloud-execution-lab/candidates/v4b"
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "root_split_brain" for e in result["errors"]))

    def test_production_coordinate_split_brain_fails(self):
        canonical, integration, composition = fixture()
        integration["production_archive"] = "exports/other.tar.gz"
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "production_coordinate_split_brain" and e["field"] == "production_archive" for e in result["errors"]))

    def test_negative_exact_package_cannot_be_composed(self):
        canonical, integration, composition = fixture()
        integration["negative_or_parked"] = [{
            "lane": "retired clone",
            "repair_path": "repairs/performance/fast-tape-clone",
            "disposition": "NO_BUILD",
        }]
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        self.assertTrue(any(e["code"] == "negative_lane_is_composed" for e in result["errors"]))

    def test_unsafe_paths_fail(self):
        canonical, integration, composition = fixture()
        integration["landed"][0]["repair_path"] = "../escape"
        composition["components"][0]["package"] = "/absolute"
        result = cross.audit(canonical, integration, composition)
        self.assertFalse(result["ok"])
        codes = {e["code"] for e in result["errors"]}
        self.assertIn("unsafe_landed_repair_path", codes)
        self.assertIn("unsafe_component_package", codes)

    def test_duplicate_json_keys_rejected_at_load(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(cross.AuditError):
                cross.load_json(path)

    def test_nonobject_json_rejected_at_load(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "x.json"
            path.write_text('[]', encoding="utf-8")
            with self.assertRaises(cross.AuditError):
                cross.load_json(path)

    def test_deterministic_error_order(self):
        canonical, integration, composition = fixture()
        canonical["canonical_branch"] = "z"
        composition["canonical_root"] = "x"
        a = cross.audit(canonical, integration, composition)
        b = cross.audit(canonical, integration, composition)
        self.assertEqual(a["errors"], b["errors"])


if __name__ == "__main__":
    unittest.main()
