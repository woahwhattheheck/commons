from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "opportunities" / "nhdes_lims_2026_093"
CARRIER_PATH = LANE / "carrier.py"
SOURCE_PATH = LANE / "source_snapshot.json"
CANDIDATE_PATH = LANE / "partner_candidate.json"

_spec = importlib.util.spec_from_file_location("nhdes_lims_2026_093_builtin_shadow_carrier", CARRIER_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load NHDES carrier")
carrier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(carrier)

FORBIDDEN_LATE_GLOBALS = {
    "CarrierError",
    "TypeError",
    "ValueError",
    "UnicodeError",
    "RecursionError",
    "OverflowError",
    "type",
    "dict",
    "set",
    "sorted",
    "any",
    "len",
    "list",
    "str",
    "int",
    "bool",
    "bytes",
    "frozenset",
}


def _canonical_hash(body: dict[str, object]) -> str:
    payload = json.dumps(
        body,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8", "strict")
    return hashlib.sha256(payload).hexdigest()


class NhdesBuiltinShadowClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        self.candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))

    def _reachable_python_functions(self) -> list[types.FunctionType]:
        roots = [
            carrier.validate_source,
            carrier.validate_candidate,
            carrier.evaluate_runtime_state,
            carrier._posture_for,
            carrier.build_receipt,
            carrier.verify_receipt,
        ]
        found: list[types.FunctionType] = []
        seen: set[int] = set()
        stack = list(roots)
        while stack:
            fn = stack.pop()
            if id(fn) in seen:
                continue
            seen.add(id(fn))
            found.append(fn)
            for cell in fn.__closure__ or ():
                try:
                    value = cell.cell_contents
                except ValueError:
                    continue
                if isinstance(value, types.FunctionType):
                    stack.append(value)
        return found

    def test_semantic_graph_has_no_late_mutable_builtin_or_error_globals(self) -> None:
        offenders: dict[str, list[str]] = {}
        for fn in self._reachable_python_functions():
            bad = sorted(FORBIDDEN_LATE_GLOBALS.intersection(fn.__code__.co_names))
            if bad:
                offenders[fn.__name__] = bad
        self.assertEqual(offenders, {})

    def test_set_shadow_alone_cannot_erase_active_collision_or_self_verify_ready(self) -> None:
        baseline = carrier.build_receipt(self.source, self.candidate)
        real_set = set
        sentinel = object()
        original = getattr(carrier, "set", sentinel)

        def forged_set(value=()):
            material = real_set(value)
            if "ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE" in material:
                return real_set()
            return material

        try:
            carrier.set = forged_set
            rebuilt = carrier.build_receipt(self.source, self.candidate)
            self.assertEqual(rebuilt, baseline)
            self.assertEqual(
                rebuilt["partner_conversion_posture"],
                "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE",
            )
            self.assertIn(
                "ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE",
                rebuilt["runtime_gate"]["holds"],
            )
            carrier.verify_receipt(rebuilt, self.source, self.candidate)
        finally:
            if original is sentinel:
                delattr(carrier, "set")
            else:
                carrier.set = original

    def test_module_builtin_shadow_cannot_erase_collision_hold_or_self_verify_ready(self) -> None:
        baseline = carrier.build_receipt(self.source, self.candidate)
        original_error = carrier.CarrierError
        self.assertEqual(
            baseline["partner_conversion_posture"],
            "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE",
        )
        self.assertIn(
            "ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE",
            baseline["runtime_gate"]["holds"],
        )

        real_set = set

        def forged_set(value=()):
            material = real_set(value)
            if "ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE" in material:
                return real_set()
            return material

        sentinel = object()
        shadows = {
            "set": forged_set,
            "sorted": lambda value: [],
            "type": lambda value: object,
            "any": lambda value: False,
            "len": lambda value: 0,
            "dict": lambda *args, **kwargs: {},
            "list": tuple,
            "str": bytes,
            "int": float,
            "bool": lambda value=False: True,
            "bytes": str,
            "frozenset": lambda value=(): real_set(),
            "CarrierError": RuntimeError,
            "TypeError": RuntimeError,
            "ValueError": RuntimeError,
            "UnicodeError": RuntimeError,
            "RecursionError": RuntimeError,
            "OverflowError": RuntimeError,
        }
        originals = {name: getattr(carrier, name, sentinel) for name in shadows}
        try:
            for name, value in shadows.items():
                setattr(carrier, name, value)

            rebuilt = carrier.build_receipt(self.source, self.candidate)
            self.assertEqual(rebuilt, baseline)
            self.assertEqual(
                rebuilt["partner_conversion_posture"],
                "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE",
            )
            self.assertIn(
                "ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE",
                rebuilt["runtime_gate"]["holds"],
            )
            self.assertTrue(all(value is False for value in rebuilt["authority"].values()))
            carrier.verify_receipt(rebuilt, self.source, self.candidate)

            forged_ready = copy.deepcopy(rebuilt)
            forged_ready["runtime_gate"]["holds"] = []
            forged_ready["partner_conversion_posture"] = "READY_FOR_MUSE_GATED_PARTNER_INQUIRY_ONLY"
            body = {key: value for key, value in forged_ready.items() if key != "receipt_hash"}
            forged_ready["receipt_hash"] = _canonical_hash(body)
            with self.assertRaises(original_error):
                carrier.verify_receipt(forged_ready, self.source, self.candidate)
        finally:
            for name, value in originals.items():
                if value is sentinel:
                    delattr(carrier, name)
                else:
                    setattr(carrier, name, value)


if __name__ == "__main__":
    unittest.main()
