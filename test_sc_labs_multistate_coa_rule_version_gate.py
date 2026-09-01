#!/usr/bin/env python3
"""Acceptance tests for sc-labs-multistate-coa-rule-version-gate-01."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import sc_labs_multistate_coa_rule_version_gate as gate


class ScLabsMultistateCoaRuleVersionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = gate.build_acceptance_fixture()
        cls.fixture_before = deepcopy(cls.fixture)
        cls.result = gate.run_gate(cls.fixture)

    def test_fixture_is_exactly_150_across_five_rule_packs(self) -> None:
        self.assertEqual(150, len(self.fixture))
        self.assertEqual(
            Counter(row["jurisdiction"] for row in self.fixture),
            Counter({jurisdiction: 30 for jurisdiction in gate.RULE_PACKS}),
        )
        self.assertEqual(
            Counter(row["expected_status"] for row in self.fixture),
            Counter({"RELEASEABLE": 120, "HOLD": 30}),
        )
        self.assertEqual(
            Counter(
                row["expected_reason"]
                for row in self.fixture
                if row["expected_reason"] is not None
            ),
            Counter(gate.EXPECTED_REASON_COUNTS),
        )

    def test_acceptance_counts_and_reason_codes_are_exact(self) -> None:
        self.assertEqual([], gate.pass_contract(self.result))
        self.assertEqual(
            {"RELEASEABLE": 120, "HOLD": 30},
            self.result["status_counts"],
        )
        self.assertEqual(
            gate.EXPECTED_REASON_COUNTS,
            self.result["reason_counts"],
        )
        held = [row for row in self.result["records"] if row["status"] == "HOLD"]
        self.assertEqual(30, len(held))
        self.assertTrue(all(len(row["reason_codes"]) == 1 for row in held))

    def test_output_status_is_binary_and_never_releases(self) -> None:
        self.assertEqual(
            {"RELEASEABLE", "HOLD"},
            {row["status"] for row in self.result["records"]},
        )
        self.assertTrue(
            all(row["human_release_required"] for row in self.result["records"])
        )
        self.assertFalse(any(row["released"] for row in self.result["records"]))
        self.assertFalse(self.result["audit"]["release_executed"])

    def test_six_planted_defect_families_hold(self) -> None:
        for expected_reason in gate.ACCEPTANCE_REASON_CODES:
            with self.subTest(expected_reason=expected_reason):
                fixture_row = next(
                    row
                    for row in self.fixture
                    if row["expected_reason"] == expected_reason
                )
                result = gate.validate_records(
                    [fixture_row], evaluation_time=gate.EVALUATION_TIME
                )[0]
                expected = expected_reason
                if expected_reason == gate.DUPLICATE_RELEASE_ID:
                    original = next(
                        row
                        for row in self.fixture
                        if row["sample_id"] == fixture_row["sample_id"]
                        and row["coa_id"] == fixture_row["coa_id"]
                        and row["expected_status"] == "RELEASEABLE"
                    )
                    result = gate.validate_records(
                        [original, fixture_row],
                        evaluation_time=gate.EVALUATION_TIME,
                    )[1]
                self.assertEqual("HOLD", result["status"])
                self.assertIn(expected, result["reason_codes"])

    def test_rule_expiry_uses_explicit_evaluation_time(self) -> None:
        row = deepcopy(
            next(item for item in self.fixture if item["expected_status"] == "RELEASEABLE")
        )
        before_expiry = gate.validate_records(
            [row], evaluation_time="2027-08-31T23:59:59Z"
        )[0]
        after_expiry = gate.validate_records(
            [row], evaluation_time="2027-09-01T00:00:01Z"
        )[0]
        self.assertEqual("RELEASEABLE", before_expiry["status"])
        self.assertEqual("HOLD", after_expiry["status"])
        self.assertIn(gate.RULE_VERSION_EXPIRED, after_expiry["reason_codes"])

    def test_custody_requires_ordered_timestamped_events(self) -> None:
        row = deepcopy(
            next(item for item in self.fixture if item["expected_status"] == "RELEASEABLE")
        )
        row["collection_events"][1], row["collection_events"][2] = (
            row["collection_events"][2],
            row["collection_events"][1],
        )
        result = gate.validate_records(
            [row], evaluation_time=gate.EVALUATION_TIME
        )[0]
        self.assertEqual("HOLD", result["status"])
        self.assertIn(gate.CUSTODY_GAP, result["reason_codes"])

    def test_malformed_external_row_fails_closed_with_stable_code(self) -> None:
        result = gate.validate_records(
            [{"sample_id": "ONLY-A-SAMPLE"}],
            evaluation_time=gate.EVALUATION_TIME,
        )[0]
        self.assertEqual("HOLD", result["status"])
        self.assertIn(gate.INPUT_INVALID, result["reason_codes"])
        self.assertFalse(result["released"])

    def test_source_fixture_is_not_mutated(self) -> None:
        self.assertEqual(self.fixture_before, self.fixture)
        self.assertTrue(self.result["input_unchanged"])

    def test_csv_and_json_inputs_produce_identical_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_path = root / "fixture.json"
            csv_path = root / "fixture.csv"
            json_path.write_text(
                gate.canonical_json({"records": self.fixture}) + "\n",
                encoding="utf-8",
            )
            csv_path.write_bytes(gate.records_to_csv(self.fixture))
            json_records = gate.load_records(json_path)
            csv_records = gate.load_records(csv_path)
            json_result = gate.run_gate(json_records)
            csv_result = gate.run_gate(csv_records)
            self.assertEqual(json_result["bundle"], csv_result["bundle"])

    def test_outputs_are_byte_identical_and_manifest_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            gate.write_outputs(output, self.result["bundle"])
            first = {
                path.name: path.read_bytes()
                for path in sorted(output.iterdir())
                if path.is_file()
            }
            gate.write_outputs(output, self.result["bundle"])
            second = {
                path.name: path.read_bytes()
                for path in sorted(output.iterdir())
                if path.is_file()
            }
            self.assertEqual(first, second)

            extra = deepcopy(self.fixture[0])
            extra["sample_id"] = "SC-CA-APPEND-001"
            extra["coa_id"] = "SC-CA-COA-APPEND-001"
            appended = gate.run_gate(self.fixture + [extra])
            gate.write_outputs(output, appended["bundle"])
            manifest = (output / "evidence_manifest.jsonl").read_bytes()
            self.assertTrue(manifest.startswith(first["evidence_manifest.jsonl"]))
            self.assertGreater(len(manifest), len(first["evidence_manifest.jsonl"]))

    def test_manifest_rejects_rewrite_of_existing_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            gate.write_outputs(output, self.result["bundle"])
            changed = deepcopy(self.fixture)
            changed[0]["coa_revision"] = "2"
            changed_result = gate.run_gate(changed)
            with self.assertRaises(gate.ManifestConflict):
                gate.write_outputs(output, changed_result["bundle"])

    def test_manifest_chain_verifies_and_tampering_is_visible(self) -> None:
        manifest = gate.build_manifest(self.result["records"])
        self.assertTrue(gate.verify_manifest(manifest))
        tampered = deepcopy(manifest)
        tampered[10]["status"] = "HOLD"
        self.assertFalse(gate.verify_manifest(tampered))

    def test_override_history_requires_named_reviewer_reason_and_time(self) -> None:
        history: list[dict[str, object]] = []
        with self.assertRaises(ValueError):
            gate.append_override_event(
                history,
                sample_id="SC-CA-S025",
                coa_id="SC-CA-COA-025",
                reviewer="AUTONOMOUS",
                reason="not allowed",
                timestamp=gate.EVALUATION_TIME,
            )
        with self.assertRaises(ValueError):
            gate.append_override_event(
                history,
                sample_id="SC-CA-S025",
                coa_id="SC-CA-COA-025",
                reviewer="Jamie Reviewer",
                reason="",
                timestamp=gate.EVALUATION_TIME,
            )
        event = gate.append_override_event(
            history,
            sample_id="SC-CA-S025",
            coa_id="SC-CA-COA-025",
            reviewer="Jamie Reviewer",
            reason="documented rule-pack correction",
            timestamp=gate.EVALUATION_TIME,
        )
        self.assertFalse(event["release_executed"])
        self.assertTrue(gate.verify_override_history(history))
        frozen = deepcopy(history[0])
        gate.append_override_event(
            history,
            sample_id="SC-CO-S025",
            coa_id="SC-CO-COA-025",
            reviewer="Taylor Reviewer",
            reason="documented custody correction",
            timestamp="2026-09-01T00:01:00Z",
        )
        self.assertEqual(frozen, history[0])
        self.assertTrue(gate.verify_override_history(history))

    def test_external_cli_writes_all_five_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "fixture.json"
            output = root / "validated"
            input_path.write_text(
                gate.canonical_json({"records": self.fixture}) + "\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(gate.__file__)),
                    "--input",
                    str(input_path),
                    "--output-dir",
                    str(output),
                    "--evaluation-time",
                    gate.EVALUATION_TIME,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(
                {
                    "results.csv",
                    "results.json",
                    "exceptions.md",
                    "evidence_manifest.jsonl",
                    "audit.json",
                },
                {path.name for path in output.iterdir()},
            )
            report = (output / "exceptions.md").read_text(encoding="utf-8")
            self.assertIn("- HOLD: 30", report)
            self.assertIn("named-human decision", report)


if __name__ == "__main__":
    unittest.main()
