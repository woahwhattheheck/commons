"""Tests for auditable dispositions."""

from __future__ import annotations

import unittest

from charttrace.review.dispositions import (
    Disposition,
    apply_disposition,
    validate_rejection_reason,
)


class DispositionTests(unittest.TestCase):
    def test_all_seven_dispositions_exist(self) -> None:
        expected = {
            "PASS",
            "REPAIR",
            "DOWNGRADE",
            "WEAK_APPENDIX",
            "MERGE_DUPLICATE",
            "REJECT_UNSUPPORTED",
            "HOLD",
        }
        self.assertEqual({d.value for d in Disposition}, expected)

    def test_cannot_reject_solely_as_not_actionable(self) -> None:
        for reason in (
            "not actionable",
            "unlikely",
            "too aggressive",
            "a lawyer might dislike it",
        ):
            err = validate_rejection_reason(reason, Disposition.REJECT_UNSUPPORTED)
            self.assertIsNotNone(err, reason)
            with self.assertRaises(ValueError):
                apply_disposition(
                    "L1", Disposition.REJECT_UNSUPPORTED, "hostile_audit", reason
                )

    def test_reject_with_concrete_defect_ok(self) -> None:
        rec = apply_disposition(
            "L1",
            Disposition.REJECT_UNSUPPORTED,
            "hostile_audit",
            "Citation does not entail clause",
            defect_codes=["CITATION_DOES_NOT_ENTAIL"],
        )
        self.assertFalse(rec.leaves_packet)
        self.assertEqual(rec.disposition, Disposition.REJECT_UNSUPPORTED)

    def test_weak_appendix_leaves_in_appendix(self) -> None:
        rec = apply_disposition(
            "L2",
            Disposition.WEAK_APPENDIX,
            "synthesis_dedup",
            "Grounded weak lead retained",
        )
        self.assertTrue(rec.leaves_packet)
        self.assertTrue(rec.preserves_in_appendix)

    def test_merge_requires_target(self) -> None:
        with self.assertRaises(ValueError):
            apply_disposition(
                "L3",
                Disposition.MERGE_DUPLICATE,
                "synthesis_dedup",
                "duplicate",
            )

    def test_hold_does_not_leave(self) -> None:
        rec = apply_disposition("L4", Disposition.HOLD, "break_the_packet", "tamper")
        self.assertFalse(rec.leaves_packet)


if __name__ == "__main__":
    unittest.main()
