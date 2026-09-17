from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

import laundry_desk as facade
import laundry_desk_core as core


FALSE_KEYS = {
    "customer_messaging",
    "provider_navigation",
    "accounting_mutation",
    "payment_mutation",
    "deployment",
    "revenue_assertion",
    "sanitation_certification",
    "quality_inference",
}
WIDENED = {key: True for key in FALSE_KEYS}


def assert_hard_false(case: unittest.TestCase, value: dict[str, bool]) -> None:
    case.assertEqual(set(value), FALSE_KEYS)
    case.assertTrue(all(flag is False for flag in value.values()))


class CoreAndAuthorityHostiles(unittest.TestCase):
    def _seed(self, desk):
        desk.add_customer("seed.customer.a", "cust-a", "Customer A")
        desk.add_customer("seed.customer.b", "cust-b", "Customer B")
        desk.add_site("seed.site.a", "site-a", "cust-a", "Site A")
        desk.add_site("seed.site.b", "site-b", "cust-b", "Site B")
        for site, suffix in (("site-a", "a"), ("site-b", "b")):
            desk.add_agreement(
                f"seed.agreement.{suffix}", f"agr-{suffix}", site, "sheet", 100, "2026-01-01"
            )
        desk.add_service_plan("seed.plan.a", "plan-a", "site-a", "route-one", 0, 10, "2026-01-01")
        desk.add_service_plan("seed.plan.b", "plan-b", "site-b", "route-one", 0, 20, "2026-01-01")
        return desk.create_daily_route("seed.route", "2026-09-21", "route-one").value

    def _good_stop(self, desk, stop_id: str, key: str):
        desk.pickup(f"{key}.pickup", stop_id, {"sheet": 1}, [f"BIN-{key}"])
        desk.process(f"{key}.process", stop_id, {"sheet": 1}, {"sheet": 0})
        desk.deliver(f"{key}.deliver", stop_id, {"sheet": 1}, [f"BIN-{key}"])

    def _raw_engine_class(self):
        matches = [
            cls
            for cls in facade.LaundryDesk.__mro__[1:]
            if cls.__module__ == "_commercial_laundry_engine_private"
        ]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_public_core_constructor_routes_to_hardened_facade_and_custody(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "core.sqlite3"
            desk = core.LaundryDesk(db)
            self.assertIs(type(desk), facade.LaundryDesk)
            route = self._seed(desk)
            stop_a, stop_b = [row["stop_id"] for row in route["stops"]]
            desk.pickup("core.pickup.a", stop_a, {"sheet": 1}, ["BIN-SHARED"])
            with self.assertRaises(core.StateConflict):
                core.LaundryDesk(db).pickup(
                    "core.pickup.b", stop_b, {"sheet": 1}, ["BIN-SHARED"]
                )

    def test_raw_base_handle_removed_constructor_sealed_and_unbound_pickup_safe(self):
        self.assertFalse(hasattr(core, "_BaseLaundryDesk"))
        raw = self._raw_engine_class()
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "raw.sqlite3"
            with self.assertRaises(TypeError):
                raw(db)
            desk = facade.LaundryDesk(db)
            route = self._seed(desk)
            stop_a, stop_b = [row["stop_id"] for row in route["stops"]]
            desk.pickup("raw.pickup.a", stop_a, {"sheet": 1}, ["BIN-SHARED"])
            # Even an explicit MRO-base unbound call delegates to the hardened
            # public operation and cannot revive the retained blind pickup.
            with self.assertRaises(core.StateConflict):
                raw.pickup(desk, "raw.pickup.b", stop_b, {"sheet": 1}, ["BIN-SHARED"])

    def test_retained_implementation_modules_are_not_ordinary_import_targets(self):
        self.assertNotIn("_commercial_laundry_engine_private", sys.modules)
        self.assertNotIn("_commercial_laundry_facade_private", sys.modules)
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("_laundry_desk_engine")
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("_laundry_desk_facade_impl")

    def test_authority_exports_are_immutable(self):
        assert_hard_false(self, dict(facade.AUTHORITY))
        assert_hard_false(self, dict(core.AUTHORITY))
        with self.assertRaises(TypeError):
            facade.AUTHORITY["payment_mutation"] = True
        with self.assertRaises(TypeError):
            core.AUTHORITY["payment_mutation"] = True

    def test_public_module_rebinding_cannot_widen_outputs(self):
        facade_original = facade.AUTHORITY
        core_original = core.AUTHORITY
        try:
            facade.AUTHORITY = WIDENED.copy()
            core.AUTHORITY = WIDENED.copy()
            with tempfile.TemporaryDirectory() as tmp:
                for ctor, name in ((facade.LaundryDesk, "facade"), (core.LaundryDesk, "core")):
                    desk = ctor(Path(tmp) / f"{name}.sqlite3")
                    route = self._seed(desk)
                    stop = route["stops"][0]["stop_id"]
                    self._good_stop(desk, stop, name)
                    invoice = desk.draft_invoice(f"{name}.invoice", stop).value
                    assert_hard_false(self, invoice["authority"])
                    assert_hard_false(self, desk.route_snapshot(route["route_id"])["authority"])
                    assert_hard_false(self, desk.customer_snapshot("cust-a")["authority"])
                    assert_hard_false(self, desk.verify_integrity()["authority"])
        finally:
            facade.AUTHORITY = facade_original
            core.AUTHORITY = core_original

    def test_method_globals_and_retained_projection_globals_cannot_widen_outputs(self):
        methods = (
            facade.LaundryDesk.draft_invoice,
            facade.LaundryDesk.route_snapshot,
            facade.LaundryDesk.customer_snapshot,
            facade.LaundryDesk.verify_integrity,
        )
        touched: dict[int, tuple[dict, object]] = {}
        sentinel = object()
        try:
            for method in methods:
                namespace = method.__globals__
                if id(namespace) not in touched:
                    touched[id(namespace)] = (namespace, namespace.get("AUTHORITY", sentinel))
                namespace["AUTHORITY"] = WIDENED.copy()
                # The core projection wrappers capture retained originals in a
                # closure. Rebind those originals' private module global too.
                for cell in method.__closure__ or ():
                    original = cell.cell_contents
                    if callable(original) and hasattr(original, "__globals__"):
                        original_ns = original.__globals__
                        if id(original_ns) not in touched:
                            touched[id(original_ns)] = (
                                original_ns,
                                original_ns.get("AUTHORITY", sentinel),
                            )
                        original_ns["AUTHORITY"] = WIDENED.copy()

            with tempfile.TemporaryDirectory() as tmp:
                desk = facade.LaundryDesk(Path(tmp) / "globals.sqlite3")
                route = self._seed(desk)
                stop = route["stops"][0]["stop_id"]
                self._good_stop(desk, stop, "globals")
                invoice = desk.draft_invoice("globals.invoice", stop).value
                assert_hard_false(self, invoice["authority"])
                assert_hard_false(self, desk.route_snapshot(route["route_id"])["authority"])
                assert_hard_false(self, desk.customer_snapshot("cust-a")["authority"])
                assert_hard_false(self, desk.verify_integrity()["authority"])
        finally:
            for namespace, previous in touched.values():
                if previous is sentinel:
                    namespace.pop("AUTHORITY", None)
                else:
                    namespace["AUTHORITY"] = previous


if __name__ == "__main__":
    unittest.main(verbosity=2)
