from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import subprocess
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
ENGINE_PATH = Path(__file__).with_name("_laundry_desk_engine.py.disabled")
LEGACY_FACADE_PATH = Path(__file__).with_name("_laundry_desk_facade_impl.py.disabled")


def assert_hard_false(case: unittest.TestCase, value: dict[str, bool]) -> None:
    case.assertEqual(set(value), FALSE_KEYS)
    case.assertTrue(all(flag is False for flag in value.values()))


def load_engine_directly(name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(ENGINE_PATH))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise AssertionError("engine probe spec unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


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

    def _assert_shared_container_rejected(self, ctor, db: Path, prefix: str):
        desk = ctor(db)
        route = self._seed(desk)
        stop_a, stop_b = [row["stop_id"] for row in route["stops"]]
        desk.pickup(f"{prefix}.pickup.a", stop_a, {"sheet": 1}, ["BIN-SHARED"])
        with self.assertRaises(core.StateConflict):
            ctor(db).pickup(f"{prefix}.pickup.b", stop_b, {"sheet": 1}, ["BIN-SHARED"])

    def test_facade_and_core_are_same_authoritative_class(self):
        self.assertIs(facade.LaundryDesk, core.LaundryDesk)
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_shared_container_rejected(core.LaundryDesk, Path(tmp) / "core.sqlite3", "core")

    def test_alternate_sourcefileloader_gets_same_hardened_semantics(self):
        direct = load_engine_directly("_laundry_direct_probe")
        self.assertIsNot(direct.LaundryDesk, core.LaundryDesk)
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_shared_container_rejected(
                direct.LaundryDesk, Path(tmp) / "direct.sqlite3", "direct"
            )

    def test_direct_python_path_is_inert_definition_only(self):
        run = subprocess.run(
            [sys.executable, str(ENGINE_PATH)],
            cwd=str(ENGINE_PATH.parent),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "")
        self.assertEqual(run.stderr, "")

    def test_legacy_second_facade_payload_is_absent(self):
        self.assertFalse(LEGACY_FACADE_PATH.exists())
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("_laundry_desk_facade_impl")

    def test_authority_exports_are_immutable(self):
        self.assertIs(facade.AUTHORITY, core.AUTHORITY)
        assert_hard_false(self, dict(facade.AUTHORITY))
        with self.assertRaises(TypeError):
            facade.AUTHORITY["payment_mutation"] = True
        with self.assertRaises(TypeError):
            core.AUTHORITY["payment_mutation"] = True
        direct = load_engine_directly("_laundry_authority_probe")
        assert_hard_false(self, dict(direct.AUTHORITY))
        with self.assertRaises(TypeError):
            direct.AUTHORITY["revenue_assertion"] = True

    def test_public_module_rebinding_cannot_widen_outputs(self):
        facade_original = facade.AUTHORITY
        core_original = core.AUTHORITY
        try:
            facade.AUTHORITY = WIDENED.copy()
            core.AUTHORITY = WIDENED.copy()
            with tempfile.TemporaryDirectory() as tmp:
                desk = facade.LaundryDesk(Path(tmp) / "public.sqlite3")
                route = self._seed(desk)
                stop = route["stops"][0]["stop_id"]
                self._good_stop(desk, stop, "public")
                assert_hard_false(self, desk.draft_invoice("public.invoice", stop).value["authority"])
                assert_hard_false(self, desk.route_snapshot(route["route_id"])["authority"])
                assert_hard_false(self, desk.customer_snapshot("cust-a")["authority"])
                assert_hard_false(self, desk.verify_integrity()["authority"])
        finally:
            facade.AUTHORITY = facade_original
            core.AUTHORITY = core_original

    def test_method_globals_rebinding_cannot_widen_outputs(self):
        methods = (
            facade.LaundryDesk.draft_invoice,
            facade.LaundryDesk.route_snapshot,
            facade.LaundryDesk.customer_snapshot,
            facade.LaundryDesk.verify_integrity,
        )
        namespace = methods[0].__globals__
        self.assertTrue(all(method.__globals__ is namespace for method in methods))
        previous_authority = namespace.get("AUTHORITY")
        previous_literal = namespace.get("_AUTHORITY_LITERAL")
        try:
            namespace["AUTHORITY"] = WIDENED.copy()
            namespace["_AUTHORITY_LITERAL"] = WIDENED.copy()
            with tempfile.TemporaryDirectory() as tmp:
                desk = facade.LaundryDesk(Path(tmp) / "globals.sqlite3")
                route = self._seed(desk)
                stop = route["stops"][0]["stop_id"]
                self._good_stop(desk, stop, "globals")
                assert_hard_false(self, desk.draft_invoice("globals.invoice", stop).value["authority"])
                assert_hard_false(self, desk.route_snapshot(route["route_id"])["authority"])
                assert_hard_false(self, desk.customer_snapshot("cust-a")["authority"])
                assert_hard_false(self, desk.verify_integrity()["authority"])
        finally:
            namespace["AUTHORITY"] = previous_authority
            namespace["_AUTHORITY_LITERAL"] = previous_literal

    def test_direct_loaded_module_rebinding_cannot_widen_outputs(self):
        direct = load_engine_directly("_laundry_direct_authority_probe")
        direct.AUTHORITY = WIDENED.copy()
        direct._AUTHORITY_LITERAL = WIDENED.copy()
        with tempfile.TemporaryDirectory() as tmp:
            desk = direct.LaundryDesk(Path(tmp) / "direct-authority.sqlite3")
            route = self._seed(desk)
            stop = route["stops"][0]["stop_id"]
            self._good_stop(desk, stop, "directauth")
            assert_hard_false(self, desk.draft_invoice("directauth.invoice", stop).value["authority"])
            assert_hard_false(self, desk.route_snapshot(route["route_id"])["authority"])
            assert_hard_false(self, desk.customer_snapshot("cust-a")["authority"])
            assert_hard_false(self, desk.verify_integrity()["authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
