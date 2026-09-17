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
            facade.AUTHORITY = {"payment_mutation": True, "revenue_assertion": True}
            core.AUTHORITY = {"payment_mutation": True, "revenue_assertion": True}
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
