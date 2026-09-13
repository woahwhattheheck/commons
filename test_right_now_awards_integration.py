from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent

settled_spec = importlib.util.spec_from_file_location(
    "host.settled_awards", ROOT / "host" / "settled_awards.py"
)
assert settled_spec and settled_spec.loader
settled = importlib.util.module_from_spec(settled_spec)
sys.modules["host.settled_awards"] = settled
settled_spec.loader.exec_module(settled)

host_package = sys.modules.get("host")
if host_package is None:
    host_package = types.ModuleType("host")
    host_package.__path__ = [str(ROOT / "host")]
    sys.modules["host"] = host_package
setattr(host_package, "settled_awards", settled)

smart = types.ModuleType("host.smart_outreach")


class OutreachError(ValueError):
    pass


smart.OutreachError = OutreachError
smart.read_object = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
smart.build_plan = lambda value, receipts: {
    "offer": {"sku_id": "offer-one"},
    "items": [
        {
            "prospect_id": "prospect-one",
            "organization": "Prospect One",
            "decision": "RESEARCH_REQUIRED",
            "score": 40,
            "evidence": {
                "source_url": "https://example.test/evidence",
                "observed_at": "2026-09-01T00:00:00Z",
            },
            "route": {"state": "UNVERIFIED"},
            "collision_receipts": [],
            "missing": ["verified route"],
            "next_action": "research",
        }
    ],
    "truth": {
        "prospects_evaluated": 1,
        "transport_actions": 0,
        "decision_counts": {"READY_TO_DRAFT": 0},
    },
}
sys.modules["host.smart_outreach"] = smart
setattr(host_package, "smart_outreach", smart)

control_spec = importlib.util.spec_from_file_location(
    "right_now_revenue_awards_integration",
    ROOT / "host" / "right_now_revenue.py",
)
assert control_spec and control_spec.loader
control = importlib.util.module_from_spec(control_spec)
control_spec.loader.exec_module(control)


class RightNowAwardsIntegrationTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        for relative in (
            "revenue/right_now",
            "revenue/smart_outreach",
            "revenue/payment_ready/outreach_receipts",
            "revenue/human_outcomes",
            "revenue/production_survival",
        ):
            (root / relative).mkdir(parents=True, exist_ok=True)

        catalog = {
            "as_of": "2026-09-05T09:50:00Z",
            "truth": {
                "collected_cash_usd": 0,
                "verified_positive_replies": 0,
                "accepted_scopes": 0,
                "active_chargeable_checkout": True,
            },
            "offers": [
                {
                    "rank": 1,
                    "id": "offer-one",
                    "name": "Offer One",
                    "price_usd": 29,
                    "delivery_window": "one day",
                    "start_route": "offer.html",
                    "payment_state": "LIVE_PUBLIC_CHECKOUT_PAGE",
                    "next_external_event": "buyer pays",
                    "founder_bottleneck": "confirm",
                    "commons_bottleneck": "deliver",
                }
            ],
            "portfolio": {"NOW": "now"},
        }
        payment = {
            "cash_claimed": False,
            "receipt_id": "usd-zero",
            "stage": "PURCHASE_INTENT",
            "state": "NEEDS_BUYER",
            "next_stage": "PURCHASE_INTENT",
            "facts": {
                "collected_cash_usd": 0,
                "processor_payment": "NOT_LANDED",
            },
        }
        (root / "revenue/right_now/catalog.json").write_text(
            json.dumps(catalog), encoding="utf-8"
        )
        for name in ("diagnostic_offer.json", "autopsy_offer.json"):
            (root / "revenue/right_now" / name).write_text("{}", encoding="utf-8")
        (root / "revenue/right_now/settled_awards.json").write_text(
            (ROOT / "revenue/right_now/settled_awards.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (root / "revenue/smart_outreach/candidates.json").write_text(
            "{}", encoding="utf-8"
        )
        (root / "revenue/payment_ready/current_receipt.json").write_text(
            json.dumps(payment), encoding="utf-8"
        )
        (root / "revenue/human_outcomes/offers.json").write_text("{}", encoding="utf-8")
        (root / "revenue/production_survival/offer.json").write_text("{}", encoding="utf-8")

    def bind(self, root: Path) -> dict[str, object]:
        original = {}
        paths = {
            "CATALOG_PATH": root / "revenue/right_now/catalog.json",
            "DIAGNOSTIC_PATH": root / "revenue/right_now/diagnostic_offer.json",
            "AUTOPSY_PATH": root / "revenue/right_now/autopsy_offer.json",
            "SETTLED_AWARDS_PATH": root / "revenue/right_now/settled_awards.json",
            "OUTREACH_PATH": root / "revenue/smart_outreach/candidates.json",
            "PAYMENT_PATH": root / "revenue/payment_ready/current_receipt.json",
            "HUMAN_PATH": root / "revenue/human_outcomes/offers.json",
            "SURVIVAL_PATH": root / "revenue/production_survival/offer.json",
            "RECEIPTS_PATH": root / "revenue/payment_ready/outreach_receipts",
            "ROOT": root,
        }
        for name, value in paths.items():
            original[name] = getattr(control, name)
            setattr(control, name, value)
        original["validate_catalog"] = control.validate_catalog
        control.validate_catalog = lambda value: value
        return original

    def restore(self, original: dict[str, object]) -> None:
        for name, value in original.items():
            setattr(control, name, value)

    def test_paid_award_is_composed_without_promoting_usd_cash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            original = self.bind(root)
            try:
                value = control.build_control()
            finally:
                self.restore(original)
        self.assertEqual(value["as_of"], "2026-09-13T09:13:24Z")
        self.assertEqual(value["truth"]["collected_cash_usd"], 0)
        self.assertEqual(value["truth"]["paid_awards"], 1)
        self.assertEqual(
            value["truth"]["settled_amounts_by_currency"],
            [{"currency": "RTC", "amount": "25"}],
        )
        self.assertIs(value["truth"]["usd_conversion_asserted"], False)
        self.assertIs(value["truth"]["award_bank_availability_asserted"], False)
        self.assertIs(value["truth"]["award_withdrawability_asserted"], False)
        self.assertIn(
            "revenue/right_now/settled_awards.json",
            {row["path"] for row in value["source_receipts"]},
        )

    def test_invented_conversion_stops_control_compilation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            ledger_path = root / "revenue/right_now/settled_awards.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["awards"][0]["usd_equivalent"] = "1.25"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            original = self.bind(root)
            try:
                with self.assertRaises(settled.SettlementError):
                    control.build_control()
            finally:
                self.restore(original)


if __name__ == "__main__":
    unittest.main()
