from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parent


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_module(
    "reply_to_revenue_measurement_boundary_core",
    ROOT / "host" / "reply_to_revenue_core.py",
)
facade = load_module(
    "reply_to_revenue_measurement_boundary_facade",
    ROOT / "host" / "reply_to_revenue.py",
)


class ReplyToRevenueMeasurementBoundaryTests(unittest.TestCase):
    def observations(self, received_at: str) -> dict[str, object]:
        return {
            "schema_version": "commons-reply-to-revenue-observations/v1",
            "kind": "REPLY_TO_REVENUE_OBSERVATIONS",
            "measured_at": "2026-09-13T12:00:00Z",
            "monitor": {
                "connector": "fixture",
                "status": "COMPLETE",
                "mailbox_claim": "fixture-only",
                "sends": 0,
                "queries": 1,
                "attributed_inbound": 1,
            },
            "events": [
                {
                    "event_ref": "opaque:measurement-boundary-event-001",
                    "received_at": received_at,
                    "prospect_key": "example-buyer",
                    "payload_sha256": "a" * 64,
                    "markers": ["we want to proceed"],
                    "provider": "fixture",
                    "matched_receipt_id": "receipt-example-1",
                    "requested_classification": "POSITIVE_SCOPE",
                }
            ],
        }

    def load(
        self,
        module: ModuleType,
        value: dict[str, object],
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return module.load_observations(path)

    def assert_future_event_rejected(self, module: ModuleType) -> None:
        with self.assertRaisesRegex(
            module.ReplyRevenueError,
            r"events\[0\]\.received_at exceeds observations\.measured_at",
        ):
            self.load(module, self.observations("2026-09-13T12:00:01Z"))

    def test_direct_core_rejects_future_event_before_chronology(self) -> None:
        self.assert_future_event_rejected(core)

    def test_facade_rejects_future_event_before_chronology(self) -> None:
        self.assert_future_event_rejected(facade)

    def test_offset_equivalent_measurement_instant_is_accepted(self) -> None:
        for module in (core, facade):
            with self.subTest(module=module.__name__):
                value = self.load(
                    module,
                    self.observations("2026-09-13T13:00:00+01:00"),
                )
                self.assertEqual(len(value["events"]), 1)
                self.assertEqual(
                    value["events"][0]["classification"],
                    "POSITIVE_SCOPE",
                )


if __name__ == "__main__":
    unittest.main()
