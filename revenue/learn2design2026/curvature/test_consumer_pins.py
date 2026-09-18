"""Keep both executable consumers bound to the exact repaired candidate."""
import unittest
from pathlib import Path

from benchmark import PINS, verify_sources
from public_run import CANDIDATES, identity


class ConsumerPinTests(unittest.TestCase):
    def test_both_runners_pin_actual_candidate_bytes(self):
        actual = identity(Path(__file__).with_name("submission.py"))["git_blob"]
        self.assertEqual(PINS["submission.py"], actual)
        self.assertEqual(CANDIDATES["curvature_b8"][3], actual)
        self.assertEqual(verify_sources()["submission.py"]["git_blob"], actual)


if __name__ == "__main__":
    unittest.main()
