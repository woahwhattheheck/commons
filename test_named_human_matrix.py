#!/usr/bin/env python3
"""Self-tests for the frozen named-human validator matrix."""
from __future__ import annotations

import re
import unittest

from host.named_human_matrix import (
    NAMED_HUMAN_CASES,
    NamedHumanMatrixFailure,
    assert_named_human_matrix,
)

_RESERVED = {"ai", "agent", "auto", "automated", "automation", "bot", "robot", "service", "system"}


def reference_validator(value):
    if not isinstance(value, str) or not value.strip():
        return False
    tokens = re.findall(r"[^\W\d_]+", value.casefold(), flags=re.UNICODE)
    if len(tokens) < 2:
        return False
    if any(token in _RESERVED for token in tokens):
        return False

    # Reconstruct maximal runs of one-letter tokens so A-U-T-O / S Y S T E M
    # cannot bypass a reserved-token check through separators.
    singles: list[str] = []
    for token in tokens + ["__boundary__"]:
        if len(token) == 1:
            singles.append(token)
            continue
        if singles:
            if "".join(singles) in _RESERVED:
                return False
            singles = []
    return True


class NamedHumanMatrixTests(unittest.TestCase):
    def test_matrix_case_ids_are_unique_and_has_allow_and_deny_families(self):
        ids = [case.case_id for case in NAMED_HUMAN_CASES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(sum(case.expected for case in NAMED_HUMAN_CASES), 8)
        self.assertGreaterEqual(sum(not case.expected for case in NAMED_HUMAN_CASES), 20)

    def test_reference_validator_passes_entire_matrix(self):
        assert_named_human_matrix(reference_validator)

    def test_nonempty_string_only_validator_is_caught(self):
        def broken(value):
            return isinstance(value, str) and bool(value.strip())

        with self.assertRaises(NamedHumanMatrixFailure) as caught:
            assert_named_human_matrix(broken)
        text = str(caught.exception)
        self.assertIn("deny-one-token", text)
        self.assertIn("deny-punct-system", text)
        self.assertIn("deny-digit-bot", text)

    def test_whole_string_denylist_is_caught_by_embedded_and_segmented_cases(self):
        def broken(value):
            if not isinstance(value, str):
                return False
            normalized = value.strip().casefold()
            return bool(normalized) and " " in normalized and normalized not in _RESERVED

        with self.assertRaises(NamedHumanMatrixFailure) as caught:
            assert_named_human_matrix(broken)
        text = str(caught.exception)
        self.assertIn("deny-exact-system", text)
        self.assertIn("deny-punct-auto", text)
        self.assertIn("deny-digit-service", text)

    def test_substring_blacklist_false_positive_is_caught_by_legitimate_controls(self):
        def broken(value):
            if not isinstance(value, str):
                return False
            normalized = value.strip().casefold()
            if len(normalized.split()) < 2:
                return False
            return not any(reserved in normalized for reserved in _RESERVED)

        with self.assertRaises(NamedHumanMatrixFailure) as caught:
            assert_named_human_matrix(broken)
        text = str(caught.exception)
        self.assertIn("allow-agent-substring", text)
        self.assertIn("allow-service-substring", text)
        self.assertIn("allow-system-substring", text)
        self.assertIn("allow-bot-substring", text)

    def test_non_boolean_validator_result_is_rejected_with_case_id(self):
        def broken(_value):
            return "yes"

        with self.assertRaisesRegex(NamedHumanMatrixFailure, "deny-none: returned non-bool str"):
            assert_named_human_matrix(broken)


if __name__ == "__main__":
    unittest.main()
