import unittest

from tools.workfeed_poll_planner.core import PlannerError, strict_json_loads


class ParserTests(unittest.TestCase):
    def test_duplicate_key_is_rejected(self):
        with self.assertRaises(PlannerError):
            strict_json_loads('{"a":1,"a":2}')

    def test_float_is_rejected(self):
        with self.assertRaises(PlannerError):
            strict_json_loads('{"a":1.5}')


if __name__ == "__main__":
    unittest.main()
