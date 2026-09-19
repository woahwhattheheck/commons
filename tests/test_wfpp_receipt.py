import unittest

from tools.workfeed_poll_planner.core import compile_plan, verify_plan
from tools.workfeed_poll_planner.demo import sample_packet


class ReceiptTests(unittest.TestCase):
    def test_receipt_tamper_is_detected(self):
        packet = sample_packet()
        plan = compile_plan(packet)
        self.assertTrue(verify_plan(packet, plan))
        plan["receipt_sha256"] = "0" * 64
        self.assertFalse(verify_plan(packet, plan))


if __name__ == "__main__":
    unittest.main()
