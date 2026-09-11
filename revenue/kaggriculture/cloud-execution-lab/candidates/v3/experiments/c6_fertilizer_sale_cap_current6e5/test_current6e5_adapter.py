import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).with_name("current6e5_adapter.py")
spec = importlib.util.spec_from_file_location("c6_current6e5_adapter_tested", PATH)
if spec is None or spec.loader is None:
    raise ImportError(PATH)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class C6Current6e5AdapterTest(unittest.TestCase):
    def test_reviewed_donor_bytes_keep_historical_tuple(self):
        self.assertEqual(a.source.LIVE_BASELINE, {
            "horizon": 8,
            "opening": 0,
            "row_order": True,
            "evening_flush": True,
            "sale_fertilizer": True,
            "cattle_early": True,
        })

    def test_adapter_binds_literal_repaired_p0_shipped_tuple(self):
        self.assertEqual(a.CURRENT_R04_TUPLE, {
            "horizon": 8,
            "opening": 0,
            "row_order": True,
            "evening_flush": True,
            "sale_fertilizer": True,
            "cattle_early": True,
            "kill_late_water": False,
            "strawberry_endgame": False,
            "strawberry_max_plants": 8,
            "no_late_sale_advance": True,
            "no_late_sale_advance_step": 648,
            "strawberry_topup": True,
            "b5_carrot_fertilizer": True,
            "b5_jit_fertilize": True,
        })
        b = a.source.base
        self.assertEqual(b.SALE_HORIZON, 8)
        self.assertEqual(b.OPEN_ROUNDTRIP, 0)
        self.assertIs(b.ROW_ORDER, True)
        self.assertIs(b.EVENING_FLUSH, True)
        self.assertEqual(b.SALE_EXCLUDED, ("WHEAT",))
        self.assertIs(b._V231_EARLY, True)
        self.assertIs(b.KILL_LATE_WATER, False)
        self.assertIs(b.STRAWBERRY_ENDGAME, False)
        self.assertEqual(b.STRAWBERRY_MAX_PLANTS, 8)
        self.assertIs(b.NO_LATE_SALE_ADVANCE, True)
        self.assertEqual(b.NO_LATE_SALE_ADVANCE_STEP, 648)
        self.assertIs(b.STRAWBERRY_TOPUP, True)
        self.assertIs(b.B5_CARROT_FERTILIZER, True)
        self.assertIs(b.B5_JIT_FERTILIZE, True)

    def test_adapter_delegates_to_reviewed_agent_and_telemetry(self):
        self.assertIs(a.agent.telemetry, a.source.REPORT)


if __name__ == "__main__":
    unittest.main()
