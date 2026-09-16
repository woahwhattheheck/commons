from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CORE_PATH = ROOT / "host" / "reply_to_revenue_core.py"


def load_core(name: str):
    spec = importlib.util.spec_from_file_location(name, CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def receipt(receipt_id: str, prospect_key: str) -> dict[str, Any]:
    return {
        "path": f"fixture-{receipt_id}.json",
        "receipt_id": receipt_id,
        "prospect_key": prospect_key,
        "organization": f"Fixture {prospect_key}",
        "recipient_email": None,
        "provider_reference": None,
        "provider_state": "COMPLETED",
        "response_state": "UNKNOWN",
        "hard_dnr": True,
        "cash_usd": 0,
        "observed_at": "2026-09-15T20:00:00Z",
    }


def raw_event(
    *,
    event_ref: str = "opaque:canonical-provenance-0001",
    prospect_key: str = "buyer-one",
    provider: Any = "gmail-observation",
    matched_receipt_id: Any = "receipt-one",
) -> dict[str, Any]:
    return {
        "event_ref": event_ref,
        "received_at": "2026-09-15T20:00:00Z",
        "prospect_key": prospect_key,
        "payload_sha256": "a" * 64,
        "markers": ["please invoice"],
        "provider": provider,
        "matched_receipt_id": matched_receipt_id,
        "requested_classification": "POSITIVE_SCOPE",
    }


def raw_observations(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "commons-reply-to-revenue-observations/v1",
        "kind": "REPLY_TO_REVENUE_OBSERVATIONS",
        "measured_at": "2026-09-15T20:10:00Z",
        "monitor": {
            "connector": "fixture",
            "status": "complete",
            "mailbox_claim": "fixture",
            "sends": 0,
            "queries": 1,
            "attributed_inbound": len(events),
        },
        "events": events,
    }


def processed_event(
    *,
    prospect_key: str = "buyer-one",
    provider: Any = "gmail-observation",
    matched_receipt_id: Any = "receipt-one",
) -> dict[str, Any]:
    return {
        "event_ref": "opaque:processed-provenance-0001",
        "received_at": "2026-09-15T20:00:00Z",
        "prospect_key": prospect_key,
        "payload_sha256": "b" * 64,
        "provider": provider,
        "matched_receipt_id": matched_receipt_id,
        "classification": "POSITIVE_SCOPE",
        "next_action": "NEEDS_ACCEPTANCE",
        "buyer_interest": True,
        "auto_ack": False,
        "delivery_failure": False,
        "matched_markers": [],
        "reason": "fixture classification",
    }


class CanonicalProvenanceTests(unittest.TestCase):
    def _load(self, core: Any, events: list[dict[str, Any]]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations.json"
            path.write_text(
                json.dumps(raw_observations(events), sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            return core.load_observations(path)

    def test_loader_rejects_invalid_provider_and_receipt_id(self) -> None:
        core = load_core("reply_to_revenue_provenance_loader")
        invalid_values: tuple[Any, ...] = (None, "", " leading", "trailing ", "x" * 201)
        for field in ("provider", "matched_receipt_id"):
            for value in invalid_values:
                with self.subTest(field=field, value=repr(value)):
                    event = raw_event()
                    event[field] = value
                    with self.assertRaisesRegex(core.ReplyRevenueError, field):
                        self._load(core, [event])

    def test_unknown_receipt_id_fails_closed_after_real_loader(self) -> None:
        core = load_core("reply_to_revenue_provenance_unknown")
        loaded = self._load(
            core,
            [raw_event(matched_receipt_id="receipt-missing")],
        )
        with self.assertRaisesRegex(core.ReplyRevenueError, "unknown canonical receipt"):
            core.build_funnel(
                receipts=[receipt("receipt-one", "buyer-one")],
                observations=loaded,
            )

    def test_cross_prospect_receipt_transplant_fails_closed(self) -> None:
        core = load_core("reply_to_revenue_provenance_cross")
        loaded = self._load(
            core,
            [
                raw_event(
                    prospect_key="buyer-one",
                    matched_receipt_id="receipt-two",
                )
            ],
        )
        with self.assertRaisesRegex(core.ReplyRevenueError, "does not match canonical prospect"):
            core.build_funnel(
                receipts=[
                    receipt("receipt-one", "buyer-one"),
                    receipt("receipt-two", "buyer-two"),
                ],
                observations=loaded,
            )

    def test_duplicate_canonical_receipt_id_fails_closed(self) -> None:
        core = load_core("reply_to_revenue_provenance_duplicate")
        observations = raw_observations([processed_event()])
        with self.assertRaisesRegex(core.ReplyRevenueError, "duplicate canonical receipt_id"):
            core.build_funnel(
                receipts=[
                    receipt("receipt-one", "buyer-one"),
                    receipt("receipt-one", "buyer-two"),
                ],
                observations=observations,
            )

    def test_direct_build_cannot_bypass_provider_validation(self) -> None:
        core = load_core("reply_to_revenue_provenance_direct")
        for value in (None, "", " ", "x" * 201):
            with self.subTest(value=repr(value)):
                observations = raw_observations(
                    [processed_event(provider=value)]
                )
                with self.assertRaisesRegex(core.ReplyRevenueError, "provider"):
                    core.build_funnel(
                        receipts=[receipt("receipt-one", "buyer-one")],
                        observations=observations,
                    )

    def test_exact_receipt_prospect_binding_surfaces_positive(self) -> None:
        core = load_core("reply_to_revenue_provenance_valid")
        loaded = self._load(core, [raw_event()])
        funnel = core.build_funnel(
            receipts=[receipt("receipt-one", "buyer-one")],
            observations=loaded,
        )
        self.assertEqual(funnel["truth"]["human_positive"], 1)
        self.assertEqual(len(funnel["surfaces"]), 1)
        self.assertEqual(funnel["surfaces"][0]["prospect_key"], "buyer-one")
        self.assertTrue(funnel["surfaces"][0]["buyer_interest"])
        self.assertEqual(funnel["inbound"][0]["matched_receipt_id"], "receipt-one")


if __name__ == "__main__":
    unittest.main()
