from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
LAB = HERE.parents[1]
for source in (HERE, LAB):
    text = str(source)
    if text not in sys.path:
        sys.path.insert(0, text)

import candidate_main
from candidate_runtime import KestrelTitanAgent
import titan_runtime


class CanonicalEntrypointContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.canonical = candidate_main._canonical_module()
        cls.feature_data = json.loads((LAB / "TITAN-CONFIG.json").read_text())

    def new_instance(self):
        return self.canonical._new_instance(LAB, dict(self.feature_data))

    def test_adapter_delegates_to_exact_canonical_main(self):
        self.assertEqual(
            Path(self.canonical.__file__).resolve(),
            (LAB / "main.py").resolve(),
        )
        self.assertTrue(callable(self.canonical._entrypoint_fallback))
        self.assertTrue(callable(self.canonical._record_entrypoint_deadline))
        self.assertTrue(hasattr(self.canonical, "_INSTANCE"))
        self.assertFalse(hasattr(candidate_main, "_INSTANCE"))

        sentinel = object()
        observation = {"step": 17}
        configuration = {"episodeSteps": 720}
        with patch.object(self.canonical, "agent", return_value=sentinel) as delegated:
            result = candidate_main.agent(observation, configuration)
        self.assertIs(result, sentinel)
        delegated.assert_called_once_with(observation, configuration)

    def test_factory_preserves_final_pressure_over_kestrel_mro(self):
        original_runtime_base = titan_runtime.TitanAgent
        instance = self.new_instance()

        self.assertIs(titan_runtime.TitanAgent, original_runtime_base)
        self.assertIsInstance(instance, KestrelTitanAgent)
        mro = type(instance).__mro__
        self.assertEqual(mro[0].__name__, "FinalPressureAgent")
        self.assertIs(mro[1], KestrelTitanAgent)
        self.assertIs(mro[2], original_runtime_base)
        self.assertTrue(instance.features.market_pressure)
        self.assertTrue(instance.features.early_capital)

    def test_final_pressure_is_suppressed_then_runs_once_after_kestrel(self):
        instance = self.new_instance()
        instance.diagnostics = {"status": "completed"}
        before = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["BUY_LAND"], ["SELL", "WOOL", 1]],
        }
        after_kestrel = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "WOOL", 1], ["BUY_LAND"]],
        }
        events = []

        def fake_kestrel(_self, _obs, _cfg, selected):
            events.append(("kestrel", selected))
            return after_kestrel

        def fake_pressure(_self, _obs, _cfg, selected):
            events.append(("pressure", selected))
            return selected

        with patch.object(
            KestrelTitanAgent,
            "_early_capital_selected",
            new=fake_kestrel,
        ), patch.object(
            titan_runtime.TitanAgent,
            "_market_pressure_selected",
            new=fake_pressure,
        ):
            # Canonical FinalPressureAgent suppresses the earlier in-pipeline
            # call.  No legacy pressure transform may run before KESTREL.
            early = instance._market_pressure_selected({}, {}, before)
            self.assertIs(early, before)
            self.assertEqual(events, [])

            result = instance._early_capital_selected({}, {}, before)

        self.assertIs(result, after_kestrel)
        self.assertEqual([event[0] for event in events], ["kestrel", "pressure"])
        self.assertIs(events[0][1], before)
        self.assertIs(events[1][1], after_kestrel)
        self.assertFalse(getattr(instance, "_final_pressure_boundary", False))


if __name__ == "__main__":
    unittest.main()
