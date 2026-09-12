# SPDX-License-Identifier: Apache-2.0
"""Configuration exactness contracts for the P07 joint-assignment witness."""
import unittest

from joint_assignment import JointAssignmentError, propose_pair_swap
from test_joint_assignment import crossing_fixture


class JointAssignmentConfigExactnessTests(unittest.TestCase):
    def _run(self, configuration):
        mechanics, obs, route = crossing_fixture()
        return propose_pair_swap(
            mechanics,
            obs,
            route,
            0,
            1,
            start_step=0,
            end_step=14,
            configuration=configuration,
        )

    def test_exact_default_configuration_still_certifies_known_swap(self):
        result = self._run({"turnsPerDay": 24, "shedCapacity": 100})
        self.assertTrue(result.changed, result.reason)
        self.assertEqual(result.reason, "accepted_exact_joint_swap")

    def test_turns_per_day_must_be_plain_positive_int(self):
        for value in (24.5, 24.0, "24", True, 0, -24):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    JointAssignmentError, "turnsPerDay must be a positive integer"
                ):
                    self._run({"turnsPerDay": value, "shedCapacity": 100})

    def test_shed_capacity_must_be_plain_positive_int(self):
        for value in (100.5, 100.0, "100", True, 0, -100):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    JointAssignmentError, "shedCapacity must be a positive integer"
                ):
                    self._run({"turnsPerDay": 24, "shedCapacity": value})


if __name__ == "__main__":
    unittest.main(verbosity=2)
