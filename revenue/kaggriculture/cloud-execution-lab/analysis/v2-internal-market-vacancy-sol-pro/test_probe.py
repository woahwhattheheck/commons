# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import probe


class ProbeModelTests(unittest.TestCase):
    def test_internal_hole_is_selected_without_moving_inherited_rows(self):
        tape = [["A"], [], ["B"], [], ["C"]]
        before = probe.nonempty_rows(tape)
        candidate, slot = probe.fill_last_internal_vacancy(
            tape, ["SELL", "MILK", 2], 5
        )
        self.assertEqual(slot, 3)
        self.assertEqual(
            [row for row in probe.nonempty_rows(candidate) if row["index"] != slot],
            before,
        )
        self.assertEqual(candidate[3], ["SELL", "MILK", 2])
        self.assertEqual(tape, [["A"], [], ["B"], [], ["C"]])

    def test_trailing_holes_are_excluded(self):
        tape = [["A"], ["B"], [], []]
        candidate, slot = probe.fill_last_internal_vacancy(
            tape, ["SELL", "MILK", 2], 4
        )
        self.assertIsNone(slot)
        self.assertEqual(candidate, tape)

    def test_unsaturated_tape_is_not_rewritten(self):
        tape = [["A"], [], ["B"]]
        candidate, slot = probe.fill_last_internal_vacancy(
            tape, ["SELL", "MILK", 2], 10
        )
        self.assertIsNone(slot)
        self.assertEqual(candidate, tape)

    def test_only_executable_window_counts(self):
        tape = [["A"], [], ["B"], [], ["C"]]
        self.assertEqual(probe.internal_vacancies(tape, 3), (1,))
        self.assertEqual(probe.internal_vacancies(tape, 2), ())


if __name__ == "__main__":
    unittest.main()
