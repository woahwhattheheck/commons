#!/usr/bin/env python3
from __future__ import annotations

import unittest

from host.named_human import is_named_human_label


class NamedHumanLabelMatrixTests(unittest.TestCase):
    def test_literal_accept_matrix(self):
        # Literal expectations are intentionally independent of the implementation's
        # reserved-token constant so changing that constant cannot rewrite the oracle.
        accepted = (
            "Aisha",
            "Aisha Rahman",
            "Agentson Rivera",
            "Serviceman Lee",
            "María-José Carreño Quiñones",
            "O'Connor Smith",
            "Anne-Marie O'Neill",
            "李 雷",
            "Systema Reviewer",
        )
        for label in accepted:
            with self.subTest(label=label):
                self.assertTrue(is_named_human_label(label))

    def test_literal_reject_matrix(self):
        rejected = (
            None,
            42,
            "",
            "   ",
            "123-456",
            "system",
            "System Reviewer",
            "BOT_operator",
            "AI Reviewer",
            "Service Account",
            "automation-2-reviewer",
            "agent007 reviewer",
            "auto reviewer",
            "A.G.E.N.T Reviewer",
            "S Y S T E M Reviewer",
            "b.o.t user",
            "A I Reviewer",
            "r_o_b_o_t Reviewer",
        )
        for label in rejected:
            with self.subTest(label=label):
                self.assertFalse(is_named_human_label(label))

    def test_digits_and_punctuation_are_token_boundaries(self):
        for label in ("System2 Operator", "bot123 user", "service_7_account"):
            with self.subTest(label=label):
                self.assertFalse(is_named_human_label(label))

    def test_reserved_substrings_inside_larger_names_are_not_blocked(self):
        for label in ("Agentson Reviewer", "Serviceman Lee", "Automationa Cruz"):
            with self.subTest(label=label):
                self.assertTrue(is_named_human_label(label))

    def test_min_parts_is_optional_caller_policy_not_identity_proof(self):
        self.assertTrue(is_named_human_label("Aisha"))
        self.assertFalse(is_named_human_label("Aisha", min_parts=2))
        self.assertTrue(is_named_human_label("Aisha Rahman", min_parts=2))

    def test_invalid_min_parts_fails_closed(self):
        for value in (0, -1, True, 1.5, "2"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    is_named_human_label("Aisha Rahman", min_parts=value)


if __name__ == "__main__":
    unittest.main()
