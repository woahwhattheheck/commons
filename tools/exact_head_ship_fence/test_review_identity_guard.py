from __future__ import annotations

from copy import deepcopy
import unittest

from tools.exact_head_ship_fence.fence import EvidenceError, compile_current
from tools.exact_head_ship_fence.test_fence import packet


class ReviewerIdentityGuard(unittest.TestCase):
    def test_same_reviewer_cannot_satisfy_multi_pass_policy(self):
        evidence = packet()
        evidence["review_policy"]["min_passes"] = 2
        replay = deepcopy(evidence["reviews"][0])
        replay["review_id"] = "review-2"
        evidence["reviews"].append(replay)
        with self.assertRaises(EvidenceError):
            compile_current(evidence)


if __name__ == "__main__":
    unittest.main()
