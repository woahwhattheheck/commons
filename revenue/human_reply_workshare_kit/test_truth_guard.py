from __future__ import annotations

import copy
import json
import unittest

from revenue.human_reply_workshare_kit.core import (
    CompiledOffer,
    WorkshareError,
    compile_offer,
    render_offer_markdown,
    render_receipt_json,
)
from revenue.human_reply_workshare_kit.test_core import base_record


class HumanReplyWorkshareTruthGuardTests(unittest.TestCase):
    def test_commercial_assertion_is_screened_in_every_rendered_caller_field(self):
        mutations = (
            lambda row: row.__setitem__("counterparty_label", "Buyer accepted this scope yesterday"),
            lambda row: row.__setitem__("opportunity_label", "Existing customer - award secured"),
            lambda row: row["scope"].__setitem__("one_line", "Contract has been signed for this workshare"),
            lambda row: row["scope"].__setitem__(
                "input_bounds", ["one legal entity", "Payment has been received for this pilot"]
            ),
        )
        for mutate in mutations:
            row = base_record()
            mutate(row)
            with self.subTest(row=row):
                with self.assertRaisesRegex(WorkshareError, "unsupported commercial/outcome assertion"):
                    compile_offer(row)

    def test_extended_false_authority_assertions_are_rejected(self):
        phrases = (
            "Invoice has been issued for this pilot",
            "Invoice was sent for this pilot",
            "Payment is settled",
            "Customer relationship is confirmed",
            "The engagement was awarded yesterday",
            "This is booked revenue",
            "This is recognized revenue",
        )
        for phrase in phrases:
            row = base_record()
            row["scope"]["one_line"] = phrase
            with self.subTest(phrase=phrase):
                with self.assertRaisesRegex(WorkshareError, "unsupported commercial/outcome assertion"):
                    compile_offer(row)

    def test_markdown_and_punctuation_split_assertions_are_rejected(self):
        phrases = (
            "Buyer **accepted** this scope yesterday",
            "Payment [received] for the pilot",
            "Invoice *sent* yesterday",
            "Award -- secured for this workshare",
        )
        for phrase in phrases:
            row = base_record()
            row["scope"]["one_line"] = phrase
            with self.subTest(phrase=phrase):
                with self.assertRaisesRegex(WorkshareError, "unsupported commercial/outcome assertion"):
                    compile_offer(row)

    def test_nfkc_compatibility_assertion_is_rejected(self):
        row = base_record()
        row["opportunity_label"] = "Ｂｕｙｅｒ ａｃｃｅｐｔｅｄ this scope"
        with self.assertRaisesRegex(WorkshareError, "unsupported commercial/outcome assertion"):
            compile_offer(row)

    def test_unicode_format_separator_is_rejected_before_render(self):
        row = base_record()
        row["scope"]["input_bounds"] = ["one entity", "Buyer acce\u200bpted this scope"]
        with self.assertRaisesRegex(WorkshareError, "Unicode control/format/private text"):
            compile_offer(row)

    def test_bidi_control_is_rejected_before_render(self):
        row = base_record()
        row["counterparty_label"] = "Example\u202ePrime"
        with self.assertRaisesRegex(WorkshareError, "Unicode control/format/private text"):
            compile_offer(row)

    def test_unicode_line_separator_is_rejected_before_render(self):
        row = base_record()
        row["counterparty_label"] = "Example\u2028Prime"
        with self.assertRaisesRegex(WorkshareError, "Unicode control/format/private text"):
            compile_offer(row)

    def test_normalization_collisions_fail_closed(self):
        row = base_record()
        row["scope"]["input_bounds"] = ["Ａ", "A"]
        with self.assertRaisesRegex(WorkshareError, "duplicate item after normalization"):
            compile_offer(row)

    def test_benign_compatibility_text_is_canonicalized_into_receipt(self):
        row = base_record()
        row["counterparty_label"] = "Ｅｘａｍｐｌｅ　Ｐｒｉｍｅ"
        compiled = compile_offer(row)
        self.assertEqual(compiled.normalized["counterparty_label"], "Example Prime")
        self.assertIn("- Counterparty: Example Prime", compiled.markdown)

    def test_direct_render_cannot_bypass_caller_text_guard(self):
        compiled = compile_offer(base_record())
        forged = copy.deepcopy(dict(compiled.normalized))
        forged["scope"] = copy.deepcopy(dict(compiled.normalized["scope"]))
        forged["scope"]["input_bounds"] = ["one entity", "Payment [received] for the pilot"]
        with self.assertRaisesRegex(WorkshareError, "unsupported commercial/outcome assertion"):
            render_offer_markdown(forged)

    def test_direct_render_reenters_complete_normalization_contract(self):
        compiled = compile_offer(base_record())
        forged = copy.deepcopy(dict(compiled.normalized))
        forged["offer_id"] = "unsafe offer id"
        with self.assertRaisesRegex(WorkshareError, "invalid token characters"):
            render_offer_markdown(forged)

        forged = copy.deepcopy(dict(compiled.normalized))
        forged["evidence_state"]["payment_settled"] = True
        with self.assertRaisesRegex(WorkshareError, "outside this qualification"):
            render_offer_markdown(forged)

    def test_receipt_rejects_minimal_forged_compiled_offer(self):
        forged = CompiledOffer(
            normalized={"offer_id": "forged", "pack_id": "DATA_MIGRATION_ACCEPTANCE"},
            markdown="forged",
            receipt_sha256="0" * 64,
        )
        with self.assertRaises(WorkshareError):
            render_receipt_json(forged)

    def test_receipt_reenters_current_commercial_truth_boundary(self):
        compiled = compile_offer(base_record())
        forged_normalized = copy.deepcopy(dict(compiled.normalized))
        forged_normalized["opportunity_label"] = "Payment [received] for the pilot"
        forged = CompiledOffer(
            normalized=forged_normalized,
            markdown=compiled.markdown,
            receipt_sha256=compiled.receipt_sha256,
        )
        with self.assertRaisesRegex(WorkshareError, "unsupported commercial/outcome assertion"):
            render_receipt_json(forged)

    def test_receipt_rejects_stale_markdown_and_hash(self):
        compiled = compile_offer(base_record())
        stale_markdown = CompiledOffer(
            normalized=compiled.normalized,
            markdown=compiled.markdown + "\nforged",
            receipt_sha256=compiled.receipt_sha256,
        )
        with self.assertRaisesRegex(WorkshareError, "compiled markdown does not match"):
            render_receipt_json(stale_markdown)

        stale_hash = CompiledOffer(
            normalized=compiled.normalized,
            markdown=compiled.markdown,
            receipt_sha256="0" * 64,
        )
        with self.assertRaisesRegex(WorkshareError, "compiled receipt hash does not match"):
            render_receipt_json(stale_hash)

    def test_receipt_for_valid_compiled_offer_binds_recompiled_state(self):
        compiled = compile_offer(base_record())
        receipt = json.loads(render_receipt_json(compiled))
        self.assertEqual(receipt["schema"], "human-reply-paid-workshare-receipt/v1")
        self.assertEqual(receipt["offer_id"], compiled.normalized["offer_id"])
        self.assertEqual(receipt["pack_id"], compiled.normalized["pack_id"])
        self.assertEqual(receipt["commercial_state"], "PROPOSED_NOT_ACCEPTED")
        self.assertEqual(receipt["normalized_sha256"], compiled.receipt_sha256)

    def test_benign_acceptance_evidence_language_still_compiles(self):
        row = base_record("DATA_MIGRATION_ACCEPTANCE")
        row["scope"]["one_line"] = (
            "Legacy-to-target reconciliation and acceptance evidence for one frozen migration batch."
        )
        self.assertIn("acceptance evidence", compile_offer(row).markdown)


if __name__ == "__main__":
    unittest.main()
