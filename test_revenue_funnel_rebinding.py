import copy
import unittest

import revenue.revenue_funnel_control.engine as engine
from test_revenue_funnel_control import base_doc


class FunnelRebindingTests(unittest.TestCase):
    def test_public_authority_mapping_is_read_only(self):
        with self.assertRaises(TypeError):
            engine.AUTHORITY["external_send"] = True

    def test_captured_generation_ignores_ordinary_module_global_rebinding(self):
        compile_fn = engine.compile_bundle
        verify_fn = engine.verify_bundle
        baseline = compile_fn(base_doc())
        saved = {
            "AUTHORITY": engine.AUTHORITY,
            "SCHEMA": engine.SCHEMA,
            "BUNDLE_SCHEMA": engine.BUNDLE_SCHEMA,
            "LANES": engine.LANES,
            "EVENT_KINDS": engine.EVENT_KINDS,
            "SOURCE_CLASSES": engine.SOURCE_CLASSES,
            "_canonical": engine._canonical,
        }
        try:
            engine.AUTHORITY = {"external_send": True}
            engine.SCHEMA = "ATTACKER_SCHEMA"
            engine.BUNDLE_SCHEMA = "ATTACKER_BUNDLE"
            engine.LANES = frozenset({"ATTACKER"})
            engine.EVENT_KINDS = frozenset({"PAYMENT_RECEIVED"})
            engine.SOURCE_CLASSES = frozenset({"ATTACKER_RECEIPT"})
            engine._canonical = lambda value: b"forged"
            self.assertEqual(compile_fn(base_doc()), baseline)
            self.assertTrue(verify_fn(copy.deepcopy(baseline)))
            self.assertTrue(all(value is False for value in baseline["packet"]["authority"].values()))
            self.assertTrue(all(value is False for value in baseline["receipt"]["authority"].values()))
        finally:
            for name, value in saved.items():
                setattr(engine, name, value)


if __name__ == "__main__":
    unittest.main()
