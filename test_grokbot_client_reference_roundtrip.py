#!/usr/bin/env python3
"""Hermetic: Autopsy public door client_reference_id → G2 case round-trip."""

from __future__ import annotations

import re
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from integrations.grokbot_control.client import GrokBotControlClient
from integrations.grokbot_control.gateway import build_server
from integrations.grokbot_control.store import normalize_case

ROOT = Path(__file__).resolve().parent
AGENT_RESCUE = ROOT / "agent-rescue.html"
X_CREF = "afa29_x_a_v1"
X_UTM = {
    "utm_source": "x",
    "utm_medium": "paid_social",
    "utm_campaign": "agent_failure_autopsy_29",
}


def _apply_checkout_attribution(href: str, page_query: dict[str, str]) -> str:
    """Mirror agent-rescue.html checkout script (no browser)."""
    clean = lambda v: re.sub(r"[^A-Za-z0-9_-]", "", str(v or ""))[:60]
    parsed = urlparse(href)
    params = parse_qs(parsed.query, keep_blank_values=True)
    flat = {k: (v[0] if v else "") for k, v in params.items()}
    for key in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"):
        value = clean(page_query.get(key, ""))
        if value:
            flat[key] = value
    is_x = all(page_query.get(k) == X_UTM[k] for k in X_UTM)
    if is_x:
        flat["client_reference_id"] = X_CREF
    query = "&".join("%s=%s" % (k, flat[k]) for k in sorted(flat))
    return "%s://%s%s?%s" % (parsed.scheme, parsed.netloc, parsed.path, query)


class GatewayFixture:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "runs.sqlite3"
        self.server = build_server(
            host="127.0.0.1", port=0, db_path=db, mode="echo"
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = GrokBotControlClient("http://127.0.0.1:%d" % self.port)
        for _ in range(50):
            try:
                self.client.health()
                break
            except Exception:
                time.sleep(0.05)
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.server.controller.store.close()
        self.tmp.cleanup()


class TestClientReferenceRoundTrip(unittest.TestCase):
    def test_agent_rescue_script_pins_x_campaign_cref(self):
        html = AGENT_RESCUE.read_text(encoding="utf-8")
        self.assertIn('data-checkout', html)
        self.assertIn('client_reference_id","afa29_x_a_v1"', html.replace("'", '"'))
        self.assertIn('utm_source:"x"', html.replace("'", '"').replace(" ", ""))
        self.assertIn('utm_medium:"paid_social"', html.replace("'", '"').replace(" ", ""))
        self.assertIn(
            'utm_campaign:"agent_failure_autopsy_29"',
            html.replace("'", '"').replace(" ", ""),
        )
        hrefs = re.findall(
            r'<a[^>]*data-checkout[^>]*href="([^"]+)"',
            html,
        )
        if not hrefs:
            hrefs = re.findall(
                r'<a[^>]*href="([^"]+)"[^>]*data-checkout',
                html,
            )
        self.assertGreaterEqual(len(hrefs), 1)
        attributed = _apply_checkout_attribution(hrefs[0], X_UTM)
        qs = parse_qs(urlparse(attributed).query)
        self.assertEqual(qs.get("client_reference_id"), [X_CREF])
        self.assertEqual(qs.get("utm_source"), ["x"])

    def test_non_x_utm_does_not_stamp_cref(self):
        html = AGENT_RESCUE.read_text(encoding="utf-8")
        href = re.search(r'href="(https://buy\.stripe\.com/[^"]+)"', html).group(1)
        attributed = _apply_checkout_attribution(
            href,
            {
                "utm_source": "commons",
                "utm_medium": "website",
                "utm_campaign": "agent_failure_autopsy_29",
            },
        )
        qs = parse_qs(urlparse(attributed).query)
        self.assertNotIn("client_reference_id", qs)

    def test_g2_case_round_trip_preserves_cref(self):
        case = normalize_case(
            {
                "offer_id": "agent-failure-autopsy-29",
                "case_ref": "opaque-x-campaign-case",
                "client_reference_id": X_CREF,
                "sku": "agent-failure-autopsy-29",
            }
        )
        self.assertEqual(case["client_reference_id"], X_CREF)
        with GatewayFixture() as fx:
            submitted = fx.client.submit(
                "x-campaign attribution proof",
                seat="SPARK",
                async_mode=False,
                case=case,
            )
            self.assertEqual(submitted["status"], "completed")
            self.assertEqual(submitted["case"]["client_reference_id"], X_CREF)
            inspected = fx.client.inspect(submitted["run_id"])
            self.assertEqual(inspected["case"]["client_reference_id"], X_CREF)
            self.assertEqual(inspected["case"]["offer_id"], "agent-failure-autopsy-29")


if __name__ == "__main__":
    unittest.main()
