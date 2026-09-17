import builtins
import importlib
import importlib.util
import sys
import unittest

from revenue.pilot_delivery_renewal_expansion_gate import engine
from revenue.pilot_delivery_renewal_expansion_gate.test_gate import current_packet


class ReloadStableTrustRootTests(unittest.TestCase):
    def _generation_one_claim_packet(self):
        packet = current_packet()
        for row in packet["milestones"]:
            row["commercial_generation"] = 1
        packet["payment"]["commercial_generation"] = 1
        return packet

    def test_hostile_max_during_reload_cannot_ratify_generation_one(self):
        packet = self._generation_one_claim_packet()
        control = engine.compile_current(packet)
        self.assertEqual(control["state"], engine.HOLD_ACCEPTANCE)
        self.assertEqual(control["commercial_generation"], 2)
        original_compile = engine.compile_current
        original_verify = engine.verify_receipt

        real_max = builtins.max

        def forged_max(*args, **kwargs):
            if len(args) == 1 and not kwargs and type(args[0]) is list and args[0] == [1, 2]:
                return 1
            return real_max(*args, **kwargs)

        try:
            builtins.max = forged_max
            importlib.reload(engine)
        finally:
            builtins.max = real_max

        self.assertIs(engine.compile_current, original_compile)
        self.assertIs(engine.verify_receipt, original_verify)
        after = engine.compile_current(packet)
        self.assertEqual(after["state"], engine.HOLD_ACCEPTANCE)
        self.assertEqual(after["commercial_generation"], 2)
        self.assertFalse(any(after["authority"].values()))

    def test_hostile_max_during_direct_engine_execution_reuses_first_generation(self):
        packet = self._generation_one_claim_packet()
        original_compile = engine.compile_current
        original_verify = engine.verify_receipt
        real_max = builtins.max

        def forged_max(*args, **kwargs):
            if len(args) == 1 and not kwargs and type(args[0]) is list and args[0] == [1, 2]:
                return 1
            return real_max(*args, **kwargs)

        module_name = f"{engine.__package__}._hostile_engine_probe"
        spec = importlib.util.spec_from_file_location(module_name, engine.__file__)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        probe = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = probe
        try:
            builtins.max = forged_max
            spec.loader.exec_module(probe)
        finally:
            builtins.max = real_max
            sys.modules.pop(module_name, None)

        self.assertIs(probe.compile_current, original_compile)
        self.assertIs(probe.verify_receipt, original_verify)
        after = probe.compile_current(packet)
        self.assertEqual(after["state"], engine.HOLD_ACCEPTANCE)
        self.assertEqual(after["commercial_generation"], 2)
        self.assertFalse(any(after["authority"].values()))

    def test_hostile_isinstance_during_reload_cannot_admit_bool_integer(self):
        packet = current_packet()
        packet["baseline"]["generation"] = True
        with self.assertRaisesRegex(engine.GateError, "integer required"):
            engine.compile_current(packet)

        original_compile = engine.compile_current
        real_isinstance = builtins.isinstance

        def forged_isinstance(value, kind):
            if value is True and kind is bool:
                return False
            return real_isinstance(value, kind)

        try:
            builtins.isinstance = forged_isinstance
            importlib.reload(engine)
        finally:
            builtins.isinstance = real_isinstance

        self.assertIs(engine.compile_current, original_compile)
        with self.assertRaisesRegex(engine.GateError, "integer required"):
            engine.compile_current(packet)


if __name__ == "__main__":
    unittest.main()
