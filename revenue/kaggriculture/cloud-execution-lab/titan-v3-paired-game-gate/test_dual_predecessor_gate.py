# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import dual_predecessor_gate as dual
from gate_common import GateError
from test_support import contract, evidence, rows, write_json, write_jsonl


A_BASELINE_SHA = "4" * 64
B_BASELINE_SHA = "5" * 64
CANDIDATE_SHA = "6" * 64


def _provenance(*, baseline_sha: str, candidate_sha: str = CANDIDATE_SHA):
    value = deepcopy(contract()["provenance"])
    value["baseline_artifact_sha256"] = baseline_sha
    value["candidate_artifact_sha256"] = candidate_sha
    return value


def _write_case(tmp_path: Path, *, predecessor_b_rows=None):
    baseline_rows, candidate_rows = rows()
    first_contract = contract(
        baseline_name="titan-v1",
        candidate_name="titan-v3",
        provenance=_provenance(baseline_sha=A_BASELINE_SHA),
    )
    second_contract = contract(
        baseline_name="titan-v2",
        candidate_name="titan-v3",
        provenance=_provenance(baseline_sha=B_BASELINE_SHA),
    )

    paths = {
        "predecessor_a_contract_path": tmp_path / "v1-contract.json",
        "predecessor_a_evidence_path": tmp_path / "v1-evidence.json",
        "predecessor_a_games_path": tmp_path / "v1-games.jsonl",
        "predecessor_b_contract_path": tmp_path / "v2-contract.json",
        "predecessor_b_evidence_path": tmp_path / "v2-evidence.json",
        "predecessor_b_games_path": tmp_path / "v2-games.jsonl",
        "candidate_games_path": tmp_path / "v3-games.jsonl",
    }
    write_json(paths["predecessor_a_contract_path"], first_contract)
    write_json(
        paths["predecessor_a_evidence_path"],
        evidence(first_contract["provenance"], panel_id=first_contract["panel_id"]),
    )
    write_jsonl(paths["predecessor_a_games_path"], baseline_rows)
    write_json(paths["predecessor_b_contract_path"], second_contract)
    write_json(
        paths["predecessor_b_evidence_path"],
        evidence(second_contract["provenance"], panel_id=second_contract["panel_id"]),
    )
    write_jsonl(
        paths["predecessor_b_games_path"],
        baseline_rows if predecessor_b_rows is None else predecessor_b_rows,
    )
    write_jsonl(paths["candidate_games_path"], candidate_rows)
    return paths, first_contract, second_contract, baseline_rows, candidate_rows


def _rewrite_contract_and_evidence(paths, slot, value):
    write_json(paths[f"predecessor_{slot}_contract_path"], value)
    write_json(
        paths[f"predecessor_{slot}_evidence_path"],
        evidence(value["provenance"], panel_id=value["panel_id"]),
    )


class DualPredecessorGateTests(unittest.TestCase):
    def setUp(self):
        self._directory = TemporaryDirectory(prefix="titan-v3-dual-gate-test-")
        self.addCleanup(self._directory.cleanup)
        self.tmp_path = Path(self._directory.name)

    def test_promotes_only_when_same_candidate_beats_both_predecessors(self):
        paths, _, _, _, _ = _write_case(self.tmp_path)

        report, code = dual.run_dual_gate(**paths)

        self.assertEqual(code, 0)
        self.assertEqual(report["verdict"], "PROMOTE")
        self.assertEqual(
            report["comparison_exit_codes"],
            {"predecessor_a": 0, "predecessor_b": 0},
        )
        candidate_digest = report["input_sha256"]["candidate_games"]
        self.assertEqual(report["shared"]["candidate_games_sha256"], candidate_digest)
        self.assertEqual(
            {
                report["comparisons"][slot]["input_sha256"]["candidate_games"]
                for slot in ("predecessor_a", "predecessor_b")
            },
            {candidate_digest},
        )
        self.assertEqual(
            report["comparisons"]["predecessor_a"]["baseline_name"],
            "titan-v1",
        )
        self.assertEqual(
            report["comparisons"]["predecessor_b"]["baseline_name"],
            "titan-v2",
        )

    def test_rejects_when_candidate_beats_only_one_predecessor(self):
        _, candidate_rows = rows()
        stronger_predecessor = deepcopy(candidate_rows)
        for row in stronger_predecessor:
            row["scores"][row["candidate_seat"]] += 20.0
        paths, _, _, _, _ = _write_case(
            self.tmp_path,
            predecessor_b_rows=stronger_predecessor,
        )

        report, code = dual.run_dual_gate(**paths)

        self.assertEqual(code, 3)
        self.assertEqual(report["verdict"], "REJECT")
        self.assertEqual(
            report["comparison_exit_codes"],
            {"predecessor_a": 0, "predecessor_b": 3},
        )
        self.assertEqual(
            report["comparisons"]["predecessor_a"]["verdict"],
            "PROMOTE",
        )
        self.assertEqual(
            report["comparisons"]["predecessor_b"]["verdict"],
            "REJECT",
        )

    def test_rejects_candidate_artifact_drift_between_comparisons(self):
        paths, _, second, _, _ = _write_case(self.tmp_path)
        second["provenance"]["candidate_artifact_sha256"] = "7" * 64
        _rewrite_contract_and_evidence(paths, "b", second)

        with self.assertRaisesRegex(GateError, "shared_provenance"):
            dual.run_dual_gate(**paths)

    def test_rejects_engine_or_runner_drift_between_comparisons(self):
        paths, _, second, _, _ = _write_case(self.tmp_path)
        second["provenance"]["engine_sha256"] = "8" * 64
        _rewrite_contract_and_evidence(paths, "b", second)

        with self.assertRaisesRegex(GateError, "shared_provenance"):
            dual.run_dual_gate(**paths)

    def test_rejects_two_labels_for_the_same_predecessor_artifact(self):
        paths, _, second, _, _ = _write_case(self.tmp_path)
        second["provenance"]["baseline_artifact_sha256"] = A_BASELINE_SHA
        _rewrite_contract_and_evidence(paths, "b", second)

        with self.assertRaisesRegex(GateError, "predecessor artifacts must be distinct"):
            dual.run_dual_gate(**paths)

    def test_rejects_candidate_aliasing_a_predecessor_artifact(self):
        paths, first, _, _, _ = _write_case(self.tmp_path)
        first["provenance"]["baseline_artifact_sha256"] = CANDIDATE_SHA
        _rewrite_contract_and_evidence(paths, "a", first)

        with self.assertRaisesRegex(GateError, "candidate_artifact_alias"):
            dual.run_dual_gate(**paths)

    def test_rejects_cached_or_wrong_inner_candidate_bytes(self):
        paths, _, _, _, _ = _write_case(self.tmp_path)
        original = dual.single_gate.run_gate

        def stale_gate(**kwargs):
            report, code = original(**kwargs)
            report = deepcopy(report)
            report["input_sha256"]["candidate_games"] = "f" * 64
            return report, code

        with patch.object(dual.single_gate, "run_gate", side_effect=stale_gate):
            with self.assertRaisesRegex(GateError, "input binding drift"):
                dual.run_dual_gate(**paths)

    def test_cli_writes_promote_report_with_stable_exit_code(self):
        paths, _, _, _, _ = _write_case(self.tmp_path)
        report_path = self.tmp_path / "dual-report.json"

        code = dual.main([
            "--predecessor-a-contract", str(paths["predecessor_a_contract_path"]),
            "--predecessor-a-evidence", str(paths["predecessor_a_evidence_path"]),
            "--predecessor-a-games", str(paths["predecessor_a_games_path"]),
            "--predecessor-b-contract", str(paths["predecessor_b_contract_path"]),
            "--predecessor-b-evidence", str(paths["predecessor_b_evidence_path"]),
            "--predecessor-b-games", str(paths["predecessor_b_games_path"]),
            "--candidate-games", str(paths["candidate_games_path"]),
            "--report", str(report_path),
            "--quiet",
        ])

        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertIs(payload["valid"], True)
        self.assertEqual(payload["verdict"], "PROMOTE")
        self.assertEqual(payload["mode"], "dual-predecessor")


if __name__ == "__main__":
    unittest.main()
