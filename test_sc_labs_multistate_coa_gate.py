#!/usr/bin/env python3
"""Binary acceptance for sc-labs-multistate-coa-rule-version-gate-01."""

from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import sc_labs_multistate_coa_gate as gate


class ScLabsMultistateCoaGateTests(unittest.TestCase):
    def test_fixture_has_150_records_and_six_exact_fault_families(self) -> None:
        rows = gate.build_acceptance_fixture()
        counts: dict[str | None, int] = {}
        for row in rows:
            counts[row["exception_type"]] = counts.get(row["exception_type"], 0) + 1
        self.assertEqual(len(rows), 150)
        self.assertEqual(
            counts,
            {None: 120, **{code: 5 for code in gate.REASON_CODES}},
        )

    def test_binary_contract_is_120_releaseable_and_30_hold(self) -> None:
        result = gate.validate_records(gate.build_acceptance_fixture())
        self.assertEqual(gate.pass_contract(result), [])
        self.assertEqual(result["input_records"], 150)
        self.assertEqual(result["releaseable"], 120)
        self.assertEqual(result["held"], 30)
        self.assertEqual(
            result["hold_counts"], {code: 5 for code in gate.REASON_CODES}
        )

    def test_zero_defective_records_are_releaseable(self) -> None:
        result = gate.validate_records(gate.build_acceptance_fixture())
        held = [row for row in result["decisions"] if row["status"] == "HOLD"]
        releaseable = [
            row for row in result["decisions"] if row["status"] == "RELEASEABLE"
        ]
        self.assertEqual(len(held), 30)
        self.assertEqual(len(releaseable), 120)
        self.assertTrue(all(row["reason_code"] in gate.REASON_CODES for row in held))
        self.assertTrue(all(row["reason_code"] == "" for row in releaseable))
        self.assertTrue(all(not row["autonomous_release"] for row in result["decisions"]))

    def test_csv_and_json_round_trip_to_identical_decisions(self) -> None:
        source = gate.build_acceptance_fixture()
        csv_rows = gate.records_from_csv(gate.records_to_csv(source))
        json_rows = gate.records_from_json(gate.records_to_json(source))
        direct = gate.validate_records(source)
        from_csv = gate.validate_records(csv_rows)
        from_json = gate.validate_records(json_rows)
        self.assertEqual(from_csv["decisions"], direct["decisions"])
        self.assertEqual(from_json["decisions"], direct["decisions"])
        self.assertEqual(
            from_csv["evidence_manifest_sha256"],
            direct["evidence_manifest_sha256"],
        )
        self.assertEqual(
            from_json["evidence_manifest_sha256"],
            direct["evidence_manifest_sha256"],
        )

    def test_repeated_runs_are_byte_identical(self) -> None:
        rows = gate.build_acceptance_fixture()
        first = gate.validate_records(rows)
        second = gate.validate_records(deepcopy(rows))
        self.assertEqual(gate._canonical(first), gate._canonical(second))
        self.assertEqual(
            first["evidence_manifest_sha256"], second["evidence_manifest_sha256"]
        )
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])

    def test_manifest_is_append_only_hash_linked_and_preserves_sources(self) -> None:
        rows = gate.build_acceptance_fixture()
        result = gate.validate_records(rows)
        manifest = result["evidence_manifest"]
        self.assertEqual(len(manifest), 150)
        for index, entry in enumerate(manifest):
            self.assertEqual(entry["seq"], index + 1)
            self.assertEqual(entry["source_sha256"], gate.sha256_hex(rows[index]))
            self.assertEqual(len(entry["result_sha256"]), 64)
            expected_previous = gate.sha256_hex(manifest[index - 1]) if index else ""
            self.assertEqual(entry["previous_entry_sha256"], expected_previous)

    def test_human_readable_exception_report_is_exact_and_stable(self) -> None:
        result = gate.validate_records(gate.build_acceptance_fixture())
        report = result["exception_report"]
        self.assertIn("30 HOLD", report)
        self.assertIn("Named-human disposition required", report)
        for code in gate.REASON_CODES:
            self.assertEqual(report.count(code), 5)
        self.assertEqual(report, gate.exception_report_text(result["decisions"]))

    def test_override_history_requires_complete_named_human_evidence(self) -> None:
        result = gate.validate_records(gate.build_acceptance_fixture())
        hold = next(row for row in result["decisions"] if row["status"] == "HOLD")
        with self.assertRaises(ValueError):
            gate.append_override(
                [], hold, reviewer="", reason="documented", timestamp="2026-09-01T00:00:00Z"
            )
        with self.assertRaises(ValueError):
            gate.append_override(
                [], hold, reviewer="reviewer", reason="", timestamp="2026-09-01T00:00:00Z"
            )
        original: list[dict[str, object]] = []
        updated = gate.append_override(
            original,
            hold,
            reviewer="named-reviewer",
            reason="buyer-controlled evidence reconciled",
            timestamp="2026-09-01T00:00:00Z",
        )
        self.assertEqual(original, [])
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["seq"], 1)
        self.assertEqual(updated[0]["reviewer"], "named-reviewer")
        self.assertEqual(len(updated[0]["entry_sha256"]), 64)

    def test_release_receipt_is_named_human_only_and_hold_needs_override(self) -> None:
        result = gate.validate_records(gate.build_acceptance_fixture())
        ready = next(
            row for row in result["decisions"] if row["status"] == "RELEASEABLE"
        )
        hold = next(row for row in result["decisions"] if row["status"] == "HOLD")
        denied = gate.record_human_release(
            ready, reviewer="", timestamp="2026-09-01T00:00:00Z"
        )
        self.assertFalse(denied["ok"])
        self.assertEqual(denied["code"], "NAMED_HUMAN_REQUIRED")
        blocked = gate.record_human_release(
            hold,
            reviewer="named-reviewer",
            timestamp="2026-09-01T00:00:00Z",
        )
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked["code"], "HOLD_REQUIRES_RECORDED_OVERRIDE")
        history = gate.append_override(
            [],
            hold,
            reviewer="named-reviewer",
            reason="documented bounded override",
            timestamp="2026-09-01T00:00:00Z",
        )
        released = gate.record_human_release(
            hold,
            reviewer="named-reviewer",
            timestamp="2026-09-01T00:01:00Z",
            override_history=history,
        )
        self.assertTrue(released["ok"])
        self.assertEqual(released["receipt"]["validation_status"], "HOLD")
        self.assertEqual(len(released["receipt"]["receipt_sha256"]), 64)

    def test_artifact_writer_outputs_deterministic_csv_json_and_report(self) -> None:
        rows = gate.build_acceptance_fixture()
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = gate.write_artifacts(Path(first_dir), rows)
            second = gate.write_artifacts(Path(second_dir), deepcopy(rows))
            self.assertEqual(first, second)
            self.assertEqual(
                first["written"],
                [
                    "decisions.csv",
                    "decisions.json",
                    "evidence-manifest.json",
                    "exception-report.txt",
                    "fixture.csv",
                    "fixture.json",
                ],
            )
            for name in first["written"]:
                self.assertEqual(
                    (Path(first_dir) / name).read_bytes(),
                    (Path(second_dir) / name).read_bytes(),
                )

    def test_no_result_alteration_source_mutation_or_live_interface(self) -> None:
        result = gate.validate_records(gate.build_acceptance_fixture())
        self.assertEqual(result["result_alterations"], 0)
        self.assertEqual(result["source_mutations"], 0)
        self.assertEqual(result["autonomous_releases"], 0)
        self.assertFalse(result["interface_live"])
        self.assertEqual(result["pre_sale_transport"], "NONE")
        self.assertEqual(result["cash_usd"], 0)
        self.assertEqual(result["truth_gate"], "HOLD / BUILD-AND-VERIFY")


if __name__ == "__main__":
    unittest.main()
