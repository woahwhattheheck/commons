#!/usr/bin/env python3
"""Hermetic: Autopsy public door client_reference_id → G2 case round-trip."""

from __future__ import annotations

import html as html_lib
import json
import re
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

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


def _apply_checkout_attribution(href: str, page_query) -> str:
    """Execute the actual checked-in checkout script with a small browser fixture."""
    html = AGENT_RESCUE.read_text(encoding="utf-8")
    scripts = re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S | re.I)
    runner = r"""
const fs = require("fs"), vm = require("vm");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const link = {
  href: input.href,
  getAttribute(name) { return name === "href" ? this.href : null; },
  setAttribute(name, value) { if (name === "href") this.href = value; }
};
const context = {
  URL, URLSearchParams,
  location: {search: input.query},
  document: {querySelectorAll(selector) {
    if (selector !== "a[data-checkout]") throw new Error("Unexpected selector: " + selector);
    return [link];
  }}
};
for (const script of input.scripts) vm.runInNewContext(script, context);
process.stdout.write(link.href);
"""
    result = subprocess.run(
        ["node", "-e", runner],
        input=json.dumps({
            "href": html_lib.unescape(href),
            "query": "?" + urlencode(page_query, doseq=True),
            "scripts": scripts,
        }),
        capture_output=True, text=True, check=True,
    )
    return result.stdout


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

    def test_duplicate_campaign_parameter_does_not_stamp_cref(self):
        html = AGENT_RESCUE.read_text(encoding="utf-8")
        href = re.search(r'href="(https://buy\\.stripe\\.com/[^"]+)"', html).group(1)
        query = list(X_UTM.items()) + [("utm_source", "x")]
        attributed = _apply_checkout_attribution(href, query)
        self.assertNotIn("client_reference_id", parse_qs(urlparse(attributed).query))

    def test_g2_case_round_trip_preserves_cref(self):
        html = AGENT_RESCUE.read_text(encoding="utf-8")
        href = re.search(r'href="(https://buy\\.stripe\\.com/[^"]+)"', html).group(1)
        attributed = _apply_checkout_attribution(href, X_UTM)
        source_reference = parse_qs(urlparse(attributed).query)["client_reference_id"][0]
        case = normalize_case(
            {
                "offer_id": "agent-failure-autopsy-29",
                "case_ref": "opaque-x-campaign-case",
                "client_reference_id": source_reference,
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
