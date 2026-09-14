import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gate", ROOT / "readiness_gate.py")
gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(gate)


class GateTests(unittest.TestCase):
    def test_empty_is_blocked(self):
        ok, missing = gate.evaluate({})
        self.assertFalse(ok); self.assertTrue(missing)

    def test_all_true_is_ready(self):
        doc = {name: True for name in gate.REQUIRED_TRUE}
        doc["p37_or_rfp_exception_needed"] = False
        doc["buyer_contact_outside_authorized_poc_attempted"] = False
        ok, missing = gate.evaluate(doc)
        self.assertTrue(ok); self.assertEqual(missing, [])

    def test_expired_exception_need_blocks(self):
        doc = {name: True for name in gate.REQUIRED_TRUE}
        doc["p37_or_rfp_exception_needed"] = True
        ok, missing = gate.evaluate(doc)
        self.assertFalse(ok); self.assertTrue(any("inquiry period ended" in x for x in missing))

    def test_unauthorized_contact_blocks(self):
        doc = {name: True for name in gate.REQUIRED_TRUE}
        doc["p37_or_rfp_exception_needed"] = False
        doc["buyer_contact_outside_authorized_poc_attempted"] = True
        ok, missing = gate.evaluate(doc)
        self.assertFalse(ok); self.assertTrue(any("communication restriction" in x for x in missing))


if __name__ == "__main__": unittest.main()
