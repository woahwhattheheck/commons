#!/usr/bin/env python3
from __future__ import annotations

import unittest

import check_activation_contracts as guard


class ActivationAliasTaintTests(unittest.TestCase):
    def assert_clean(self, source: str) -> None:
        self.assertEqual([], guard.analyze_source(source, path="alias.py"))

    def assert_fails(self, source: str, count: int = 1) -> list[guard.Finding]:
        findings = guard.analyze_source(source, path="alias.py")
        self.assertEqual(count, len(findings), findings)
        return findings

    def test_direct_alias_truthiness_is_fail_open(self):
        findings = self.assert_fails(
            "def apply(action, enabled=False):\n"
            "    active = enabled\n"
            "    if active:\n"
            "        return {'changed': True}\n"
            "    return action\n"
        )
        self.assertEqual("apply", findings[0].function)
        self.assertEqual(3, findings[0].line)

    def test_chained_alias_boolop_is_fail_open(self):
        self.assert_fails(
            "def apply(candidate, enabled=False):\n"
            "    first = enabled\n"
            "    second = first\n"
            "    return second and candidate\n"
        )

    def test_alias_coercions_are_fail_open(self):
        self.assert_fails(
            "def apply(enabled=False):\n"
            "    active = enabled\n"
            "    return bool(active)\n"
        )
        self.assert_fails(
            "def apply(enabled=False):\n"
            "    active: object = enabled\n"
            "    return not active\n"
        )

    def test_unconditional_safe_overwrite_clears_alias_taint(self):
        self.assert_clean(
            "def apply(action, enabled=False):\n"
            "    active = enabled\n"
            "    active = False\n"
            "    if active:\n"
            "        return {'changed': True}\n"
            "    return action\n"
        )

    def test_branch_ambiguous_alias_stays_fail_closed(self):
        self.assert_fails(
            "def apply(action, condition, enabled=False):\n"
            "    active = False\n"
            "    if condition:\n"
            "        active = enabled\n"
            "    if active:\n"
            "        return {'changed': True}\n"
            "    return action\n"
        )

    def test_both_branches_safe_overwrite_clear_alias_taint(self):
        self.assert_clean(
            "def apply(action, condition, enabled=False):\n"
            "    active = enabled\n"
            "    if condition:\n"
            "        active = False\n"
            "    else:\n"
            "        active = False\n"
            "    if active:\n"
            "        return {'changed': True}\n"
            "    return action\n"
        )

    def test_literal_true_guard_still_discharges_alias_truthiness(self):
        self.assert_clean(
            "def apply(action, enabled=False):\n"
            "    active = enabled\n"
            "    if enabled is not True:\n"
            "        return action\n"
            "    if active:\n"
            "        return {'changed': True}\n"
            "    return action\n"
        )


if __name__ == "__main__":
    unittest.main()
