from __future__ import annotations

import copy
import subprocess
import sys
import textwrap
import unittest

from revenue.human_reply_workshare_kit.core import (
    WorkshareError,
    compile_offer,
    render_offer_markdown,
)
from revenue.human_reply_workshare_kit.test_core import base_record


_UNSUPPORTED = (
    "Buyer accepted this scope yesterday.",
    "We have been awarded the work.",
    "Award secured for this program.",
    "We were paid for the pilot.",
    "Payment received for the pilot.",
    "This is booked revenue.",
    "This is recognized revenue.",
    "Signed contract for phase one.",
    "Existing customer requested the change.",
    "Guaranteed savings of ten percent.",
)


class HumanReplyWorkshareClaimGuardTests(unittest.TestCase):
    def _put(self, row, field: str, value: str) -> None:
        if field == "counterparty_label":
            row["counterparty_label"] = value
        elif field == "opportunity_label":
            row["opportunity_label"] = value
        elif field == "scope.input_bounds":
            row["scope"]["input_bounds"] = [value]
        else:  # pragma: no cover - test helper misuse
            raise AssertionError(field)

    def test_every_alternate_rendered_field_rejects_unsupported_claims(self):
        for field in ("counterparty_label", "opportunity_label", "scope.input_bounds"):
            for phrase in _UNSUPPORTED:
                with self.subTest(field=field, phrase=phrase):
                    row = base_record()
                    self._put(row, field, phrase)
                    with self.assertRaisesRegex(WorkshareError, "unsupported"):
                        compile_offer(row)

    def test_unicode_compatibility_and_format_smuggling_fail_closed(self):
        hostiles = (
            "Ｐａｙｍｅｎｔ ｒｅｃｅｉｖｅｄ for the pilot.",
            "Pay\u200bment received for the pilot.",
            "Existing\u2060 customer requested the change.",
            "Buyer\u2028accepted this scope yesterday.",
        )
        for field in ("counterparty_label", "opportunity_label", "scope.input_bounds"):
            for phrase in hostiles:
                with self.subTest(field=field, phrase=repr(phrase)):
                    row = base_record()
                    self._put(row, field, phrase)
                    with self.assertRaises(WorkshareError):
                        compile_offer(row)

    def test_legitimate_acceptance_evidence_and_unicode_labels_still_compile(self):
        phrase = "Acceptance evidence workshare"
        for field in ("counterparty_label", "opportunity_label", "scope.input_bounds"):
            with self.subTest(field=field):
                row = base_record()
                self._put(row, field, phrase)
                self.assertIn("PROPOSED_NOT_ACCEPTED", compile_offer(row).markdown)
        row = base_record()
        row["counterparty_label"] = "Café Example Prime"
        self.assertIn("Café Example Prime", compile_offer(row).markdown)

    def test_public_renderer_revalidates_forged_normalized_mapping(self):
        forged = copy.deepcopy(dict(compile_offer(base_record()).normalized))
        forged["scope"] = copy.deepcopy(dict(forged["scope"]))
        forged["opportunity_label"] = "Payment received for the pilot."
        with self.assertRaisesRegex(WorkshareError, "unsupported"):
            render_offer_markdown(forged)

    def test_optimized_python_keeps_ascii_and_unicode_guards(self):
        program = textwrap.dedent(
            """
            from revenue.human_reply_workshare_kit.core import WorkshareError, compile_offer
            from revenue.human_reply_workshare_kit.test_core import base_record

            cases = (
                ("counterparty_label", "Buyer accepted this scope yesterday."),
                ("opportunity_label", "Existing customer - award secured"),
                ("scope.input_bounds", "Payment received for the pilot."),
                ("counterparty_label", "Ｐａｙｍｅｎｔ ｒｅｃｅｉｖｅｄ for the pilot."),
                ("opportunity_label", "Pay\\u200bment received for the pilot."),
            )
            for field, phrase in cases:
                row = base_record()
                if field == "scope.input_bounds":
                    row["scope"]["input_bounds"] = [phrase]
                else:
                    row[field] = phrase
                try:
                    compile_offer(row)
                except WorkshareError:
                    continue
                raise SystemExit(f"guard bypass under -O: {field}: {phrase!r}")
            """
        )
        result = subprocess.run(
            [sys.executable, "-O", "-c", program],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
