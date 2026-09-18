import unittest
import unc_ap_ai as m

class TestCompiler(unittest.TestCase):
    def test_public_source_is_fail_closed(self):
        self.assertEqual(m.compile_source({})["state"], "HOLD_SOURCE_BYTES")

if __name__ == "__main__":
    unittest.main()
