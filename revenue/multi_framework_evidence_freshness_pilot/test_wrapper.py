from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from revenue.multi_framework_evidence_freshness.golden import build_golden_input

from . import cli, wrapper
from .wrapper import (
    MAX_EVIDENCE_OBJECTS,
    PRICE_STATUS,
    DiagnosticError,
    compile_diagnostic,
    render_buyer_page,
    verify_diagnostic,
)


class WrapperTests(unittest.TestCase):
    def test_golden_compiles_and_verifies(self) -> None:
        envelope = compile_diagnostic(build_golden_input())
        digest = verify_diagnostic(envelope)
        self.assertEqual(digest, envelope["diagnostic_sha256"])
        counts = envelope["diagnostic"]["summary"]["counts"]
        self.assertEqual(sum(counts.values()), 400)
        self.assertEqual(envelope["diagnostic"]["offer"]["status"], PRICE_STATUS)
        self.assertEqual(envelope["diagnostic"]["scope"]["max_evidence_objects"], MAX_EVIDENCE_OBJECTS)
        page = render_buyer_page(envelope)
        self.assertIn("Evidence Freshness Diagnostic", page)
        self.assertIn("PROPOSED_NOT_ACCEPTED", page)
        self.assertTrue(all(v is False for v in envelope["diagnostic"]["authority"].values()))

    def test_order_invariance(self) -> None:
        raw = build_golden_input()
        a = compile_diagnostic(raw)
        raw["evidence"] = list(reversed(raw["evidence"]))
        b = compile_diagnostic(raw)
        self.assertEqual(a["diagnostic"]["summary"]["counts"], b["diagnostic"]["summary"]["counts"])
        self.assertEqual(a["diagnostic"]["binding"]["engine_receipt_sha256"], b["diagnostic"]["binding"]["engine_receipt_sha256"])

    def test_cli_roundtrip(self) -> None:
        raw = build_golden_input()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "in.json"
            out = root / "diag.json"
            md = root / "page.md"
            src.write_text(json.dumps(raw), encoding="utf-8")
            self.assertEqual(cli.main(["compile", str(src), str(out), str(md)]), 0)
            self.assertEqual(cli.main(["verify", str(out)]), 0)
            self.assertTrue(md.read_text(encoding="utf-8").startswith("# Evidence Freshness Diagnostic"))

    def test_engine_reason_codes_are_preserved(self) -> None:
        envelope = compile_diagnostic(build_golden_input())
        reasons = envelope["diagnostic"]["summary"]["non_reusable"]
        reason_codes = {row["reason"] for row in reasons}
        self.assertIn("FRESHNESS_WINDOW_EXCEEDED", reason_codes)
        self.assertIn("MISSING_OWNER", reason_codes)
        self.assertNotIn("UNSPECIFIED", reason_codes)

    def test_forged_counts_rejected_even_with_redigested_body(self) -> None:
        envelope = compile_diagnostic(build_golden_input())
        forged = copy.deepcopy(envelope)
        forged["diagnostic"]["summary"]["counts"] = {state: 0 for state in wrapper.STATES}
        forged["diagnostic"]["summary"]["counts"]["REUSABLE"] = 400
        forged["diagnostic_sha256"] = wrapper._sha(forged["diagnostic"])
        with self.assertRaisesRegex(DiagnosticError, "diagnostic_packet_mismatch"):
            verify_diagnostic(forged)

    def test_forged_engine_binding_rejected_even_with_redigested_body(self) -> None:
        envelope = compile_diagnostic(build_golden_input())
        forged = copy.deepcopy(envelope)
        forged["diagnostic"]["binding"]["input_sha256"] = "0" * 64
        forged["diagnostic"]["binding"]["projection_sha256"] = "1" * 64
        forged["diagnostic_sha256"] = wrapper._sha(forged["diagnostic"])
        with self.assertRaisesRegex(DiagnosticError, "diagnostic_packet_mismatch"):
            verify_diagnostic(forged)

    def test_forged_scope_rejected_even_with_redigested_body(self) -> None:
        envelope = compile_diagnostic(build_golden_input())
        forged = copy.deepcopy(envelope)
        forged["diagnostic"]["scope"]["objects_submitted"] = 499
        forged["diagnostic"]["scope"]["objects_evaluated"] = 499
        forged["diagnostic_sha256"] = wrapper._sha(forged["diagnostic"])
        with self.assertRaisesRegex(DiagnosticError, "diagnostic_packet_mismatch"):
            verify_diagnostic(forged)

    def test_offer_and_authority_contract_is_machine_readable(self) -> None:
        envelope = compile_diagnostic(build_golden_input())
        offer = envelope["diagnostic"]["offer"]
        self.assertFalse(offer["free_custom_adapter"])
        self.assertIn("PAID_DIAGNOSTIC", offer["integration_sprint_condition"])
        authority = envelope["diagnostic"]["authority"]
        self.assertFalse(authority["outbound"])
        self.assertFalse(authority["evidence_mutation"])

    def test_buyer_page_aggregates_reasons_without_evidence_ids(self) -> None:
        envelope = compile_diagnostic(build_golden_input())
        page = render_buyer_page(envelope)
        self.assertIn("FRESHNESS_WINDOW_EXCEEDED", page)
        self.assertNotIn("STALE-000", page)


if __name__ == "__main__":
    unittest.main()
