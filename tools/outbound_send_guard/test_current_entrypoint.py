from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import tools.outbound_send_guard as outbound_package
from tools.outbound_send_guard import current, guard

NOW = datetime(2026, 9, 14, 4, 55, 0, tzinfo=timezone.utc)


def intent(requested_at: str = "2026-09-14T04:54:30Z") -> dict:
    return {
        "schema_version": "outbound-send-intent/v1",
        "intent_id": "entrypoint-1",
        "recipient": "buyer@example.com",
        "offer_id": "fixed-proof-001",
        "requested_at": requested_at,
        "route_kind": "email",
    }


def evidence(generated_at: str = "2026-09-14T04:54:20Z") -> dict:
    return {
        "schema_version": "outbound-send-evidence/v1",
        "generated_at": generated_at,
        "mailbox": {"complete": True, "query_id": "mail-complete", "messages": []},
        "slack": {"complete": True, "query_id": "slack-complete", "events": []},
        "policy": {
            "cross_offer_cooldown_days": 30,
            "max_evidence_age_seconds": 604800,
            "max_future_skew_seconds": 86400,
        },
    }


class CurrentEntrypointTests(unittest.TestCase):
    def test_direct_guard_cli_routes_old_syntax_through_current_clock(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ip, ep, out = root / "intent.json", root / "evidence.json", root / "receipt.json"
            ip.write_text(json.dumps(intent()), encoding="utf-8")
            ep.write_text(json.dumps(evidence()), encoding="utf-8")
            with patch.object(current, "_utc_now", return_value=NOW):
                rc = guard.main(["--intent", str(ip), "--evidence", str(ep), "--out", str(out)])
            self.assertEqual(rc, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))["payload"]
            self.assertEqual(payload["schema_version"], current.CURRENT_RECEIPT_SCHEMA)
            self.assertEqual(payload["verified_at"], "2026-09-14T04:55:00Z")
            self.assertTrue(payload["current_preflight_clear"])

    def test_legacy_engine_is_historical_while_package_api_holds_stale_replay(self):
        stale_intent = intent("2025-01-01T00:00:10Z")
        stale_evidence = evidence("2025-01-01T00:00:00Z")
        historical = guard.evaluate(stale_intent, stale_evidence)
        self.assertEqual(historical["payload"]["decision"], "ALLOW_NEW")
        with patch.object(current, "_utc_now", return_value=NOW):
            supported = outbound_package.evaluate(stale_intent, stale_evidence)
        self.assertEqual(supported["payload"]["historical_decision"], "ALLOW_NEW")
        self.assertEqual(supported["payload"]["decision"], "HOLD")
        self.assertFalse(supported["payload"]["current_preflight_clear"])


if __name__ == "__main__":
    unittest.main()
