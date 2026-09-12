# SPDX-License-Identifier: Apache-2.0
"""Current-ABI retry-boundary acceptance for the public V231 envelope."""
import copy
import unittest

from test_v231_late_current import observation, selected
from v231_late_current_safe import V231LateCurrentABISafe


class TestV231RetryBoundary(unittest.TestCase):
    def test_malformed_same_step_retry_is_detached_and_preserves_transaction(self):
        arm = V231LateCurrentABISafe(enabled=True)
        obs = observation(step=216)
        parent = selected([["BUY_ANIMAL", "SHEEP", 1]])

        first = arm.transform(obs, parent)
        self.assertEqual(first["market"], [["BUY_ANIMAL", "COW", 1]])
        post = copy.deepcopy(arm.states[0])
        transaction = copy.deepcopy(arm._transactions[0])

        malformed = {"farmer": ["PASS"], "hands": "not-a-list", "market": []}
        self.assertEqual(arm.transform(obs, malformed), malformed)
        self.assertEqual(arm.states[0], post)
        self.assertEqual(arm._transactions[0], transaction)

        # A later valid retry still resolves against the exact original transaction.
        retry = arm.transform(copy.deepcopy(obs), copy.deepcopy(parent))
        self.assertEqual(retry, first)
        self.assertEqual(arm.states[0], post)
        self.assertEqual(arm._transactions[0], transaction)


if __name__ == "__main__":
    unittest.main(verbosity=2)
