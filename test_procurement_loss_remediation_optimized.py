from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ProcurementLossRemediationOptimizedTests(unittest.TestCase):
    def test_real_python_o_executes_core_trust_boundaries(self):
        # Do not use `assert` inside the child: -O intentionally removes them.
        script = r'''
import copy
import json
from pathlib import Path

from tools.procurement_loss_remediation import compile_plan, verify_plan
from tools.procurement_win_loss import compile_record

root = Path.cwd()
fixtures = json.loads((root / "tools" / "procurement_loss_remediation" / "fixtures.json").read_text())
fixture = copy.deepcopy(fixtures["stated_loss"])
source = fixture.pop("outcome_record")
raw = {
    "schema": "procurement-loss-remediation-input/v1",
    "outcome_record": source,
    "outcome_receipt": compile_record(source),
    **fixture,
}
receipt = compile_plan(raw)
if receipt.get("status") != "HOLD_CONTRADICTION":
    raise SystemExit("optimized caller-stated packet became actionable")
if any(receipt.get("authority", {}).values()):
    raise SystemExit("optimized compile raised external authority")
if verify_plan(raw, receipt).get("status") != "VERIFIED":
    raise SystemExit("optimized semantic verification failed")
reason = receipt["buyer_reasons"][0]
if reason["statement_attribution"] != "CALLER_RETAINED_STATED_SOURCE_BOUND_NOT_BUYER_AUTHENTICATED":
    raise SystemExit("optimized buyer attribution was not truth-narrowed")
if reason.get("buyer_source_authenticated") is not False:
    raise SystemExit("optimized caller source became buyer-authenticated")
if receipt["remediation_gaps"][0].get("basis_valid") is not False:
    raise SystemExit("optimized unauthenticated buyer reason authorized a gap")
if not any(item.startswith("buyer_reason_not_authenticated:") for item in receipt["hold_reasons"]):
    raise SystemExit("optimized unauthenticated-buyer hold missing")

# Direct predecessor requested by review: a caller can self-author BUYER_NOTICE,
# a well-formed arbitrary digest, and STATED rationale that verifies upstream.
forged = copy.deepcopy(raw)
forged_fact = forged["outcome_record"]["evidence"][0]
forged_fact["source_kind"] = "BUYER_NOTICE"
forged_fact["source_digest_sha256"] = "a" * 64
forged["buyer_reason_mappings"][0]["source_digest_sha256"] = "a" * 64
forged["outcome_receipt"] = compile_record(forged["outcome_record"])
forged_receipt = compile_plan(forged)
if forged_receipt.get("status") != "HOLD_CONTRADICTION":
    raise SystemExit("forged BUYER_NOTICE packet became actionable")
if forged_receipt["buyer_reasons"][0].get("buyer_source_authenticated") is not False:
    raise SystemExit("forged BUYER_NOTICE became authenticated")
if forged_receipt["remediation_gaps"][0].get("basis_valid") is not False:
    raise SystemExit("forged BUYER_NOTICE authorized remediation")

hostile = copy.deepcopy(raw)
hostile["buyer_reason_mappings"][0]["source_digest_sha256"] = "9" * 64
hostile_receipt = compile_plan(hostile)
if hostile_receipt.get("status") != "HOLD_CONTRADICTION":
    raise SystemExit("optimized digest mismatch failed to hold")

hyp = copy.deepcopy(fixtures["unknown_reason_internal_hypothesis"])
hyp_source = hyp.pop("outcome_record")
hyp_raw = {
    "schema": "procurement-loss-remediation-input/v1",
    "outcome_record": hyp_source,
    "outcome_receipt": compile_record(hyp_source),
    **hyp,
}
hyp_receipt_ok = compile_plan(hyp_raw)
if hyp_receipt_ok.get("status") != "ACTIONABLE_GAPS":
    raise SystemExit("optimized internal hypothesis lost its separate actionability")
if hyp_receipt_ok["internal_hypotheses"][0].get("attribution") != "INTERNAL_HYPOTHESIS_NOT_BUYER_FACT":
    raise SystemExit("optimized internal hypothesis attribution widened")

hyp_raw["internal_hypotheses"][0]["evidence_basis"][0]["observed_at"] = "2026-09-17T11:29:59Z"
hyp_receipt = compile_plan(hyp_raw)
if hyp_receipt.get("status") != "HOLD_CONTRADICTION":
    raise SystemExit("optimized hypothesis source binding failed to hold")
if hyp_receipt["internal_hypotheses"][0].get("basis_valid") is not False:
    raise SystemExit("optimized hypothesis basis unexpectedly valid")
'''
        result = subprocess.run(
            [sys.executable, "-O", "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"optimized child failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
