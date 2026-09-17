from __future__ import annotations

import copy
import unittest

from revenue.human_reply_workshare_kit.core import (
    WorkshareError,
    compile_offer,
    render_offer_markdown,
)
from revenue.human_reply_workshare_kit.test_core import base_record


class HumanReplyWorkshareTruthGuardTests(unittest.TestCase):
    def test_commercial_assertion_is_screened_in_every_rendered_caller_field(self):
        mutations = (
            lambda row: row.__setitem__("counterparty_label", "Buyer accepted this scope yesterday"),
            lambda row: row.__setitem__("opportunity_label", "Payment received for this pilot"),
            lambda row: row["scope"].__setitem__("one_line", "This is booked revenue"),
            lambda row: row["scope"].__setitem__(
                "input_bounds", ["one legal entity", "Existing customer requested the change"]
            ),
        )
        for mutate in mutations:
            row = base_record()
            mutate(row)
            with self.subTest(row=row):
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
        forged["scope"]["input_bounds"] = ["one entity", "Payment received for the pilot"]
        with self.assertRaisesRegex(WorkshareError, "unsupported commercial/outcome assertion"):
            render_offer_markdown(forged)

    def test_benign_acceptance_evidence_language_still_compiles(self):
        row = base_record("DATA_MIGRATION_ACCEPTANCE")
        row["scope"]["one_line"] = (
            "Legacy-to-target reconciliation and acceptance evidence for one frozen migration batch."
        )
        self.assertIn("acceptance evidence", compile_offer(row).markdown)


if __name__ == "__main__":
    unittest.main()
