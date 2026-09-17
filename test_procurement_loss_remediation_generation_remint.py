from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tools.procurement_loss_remediation import compile_plan
from tools.procurement_win_loss import compile_record

ROOT = Path(__file__).resolve().parent
FIXTURES = json.loads(
    (ROOT / "tools" / "procurement_loss_remediation" / "fixtures.json").read_text(
        encoding="utf-8"
    )
)


def _packet() -> dict:
    fixture = copy.deepcopy(FIXTURES["unknown_reason_internal_hypothesis"])
    source = fixture.pop("outcome_record")
    return {
        "schema": "procurement-loss-remediation-input/v1",
        "outcome_record": source,
        "outcome_receipt": compile_record(source),
        **fixture,
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _exercise_generation_remint() -> None:
    raw = _packet()
    hypothesis = raw["internal_hypotheses"][0]
    old_basis = copy.deepcopy(hypothesis["evidence_basis"][0])

    # Legitimately create a new upstream evidence generation under the same
    # evidence_id, then recompile the upstream receipt.  The downstream
    # hypothesis is intentionally left on its old exact source generation.
    fact = raw["outcome_record"]["evidence"][0]
    _require(fact["evidence_id"] == old_basis["evidence_id"], "fixture evidence id drift")
    _require(fact["source_digest_sha256"] == old_basis["source_digest_sha256"], "fixture digest drift")
    fact["source_digest_sha256"] = "9" * 64
    raw["outcome_receipt"] = compile_record(raw["outcome_record"])

    _require(
        raw["outcome_receipt"]["known_facts"][0]["source_digest_sha256"] == "9" * 64,
        "upstream receipt did not bind the new evidence generation",
    )
    _require(
        hypothesis["evidence_basis"][0] == old_basis,
        "hostile accidentally rewrote the old hypothesis generation",
    )

    receipt = compile_plan(raw)
    _require(receipt["source_outcome"] == "LOST", "upstream terminal outcome changed")
    _require(receipt["status"] == "HOLD_CONTRADICTION", "cross-generation hypothesis stayed actionable")

    hyp = next(row for row in receipt["internal_hypotheses"] if row["hypothesis_id"] == "hyp-runway")
    _require(hyp["basis_valid"] is False, "old hypothesis generation remained basis-valid")
    _require(
        "hypothesis_evidence_binding_mismatch:hyp-runway:notice-002" in receipt["hold_reasons"],
        "specific generation-binding hold reason missing",
    )

    gap = next(row for row in receipt["remediation_gaps"] if row["gap_id"] == "gap-runway-screen")
    _require(gap["basis_valid"] is False, "gap stayed actionable from a cross-generation hypothesis")


class ProcurementLossRemediationGenerationRemintTests(unittest.TestCase):
    def test_legitimate_upstream_remint_cannot_reuse_old_hypothesis_basis(self) -> None:
        _exercise_generation_remint()

    def test_same_predecessor_under_real_python_optimized(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-O", str(Path(__file__).resolve()), "--optimized-child"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"python -O predecessor failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )
        self.assertIn("GENERATION_REMINT_OK", proc.stdout)


if __name__ == "__main__":
    if "--optimized-child" in sys.argv:
        _exercise_generation_remint()
        print("GENERATION_REMINT_OK")
    else:
        unittest.main()
