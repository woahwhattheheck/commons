#!/usr/bin/env python3
"""Hermetic: four $199 diagnostic pages carry post-pay receipt→handoff copy."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = (
    (
        "dealer-service-lead-rescue.html",
        "https://buy.stripe.com/3cIdR8gBf6379uF1Oy43S0b",
    ),
    (
        "referral-intake-completeness.html",
        "https://buy.stripe.com/9B600i98N77b9uFeBk43S0c",
    ),
    (
        "plant-downtime-handoff.html",
        "https://buy.stripe.com/14AfZgckZ0IN0Y99h043S0e",
    ),
    (
        "repair-booking-preflight.html",
        "https://buy.stripe.com/9B66oGacR2QVdKVeBk43S0d",
    ),
)


class TestForgeDiagPostpayReceiptHandoff(unittest.TestCase):
    def test_four_pages_have_postpay_handoff(self) -> None:
        for path, plink in PAGES:
            with self.subTest(path=path):
                raw = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn('data-postpay-handoff="1"', raw)
                self.assertIn("After purchase", raw)
                self.assertIn("Stripe receipt", raw)
                self.assertIn("mailto:tokenjunkielabs@gmail.com", raw)
                self.assertIn(plink, raw)


    def test_generated_packets_preserve_delivery_window(self) -> None:
        # Exercise the checked-in click handlers against their actual engines.
        script = r"""
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
for (const [slug, globalName] of [
  ["dealer-service-lead-rescue", "DealerServiceLeadRescue"],
  ["referral-intake-completeness", "ReferralIntakeCompleteness"],
  ["plant-downtime-handoff", "PlantDowntimeHandoff"],
]) {
  const html = fs.readFileSync(slug + ".html", "utf8");
  const nodes = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(
    ([, id]) => [id, {value: "", textContent: "", onclick: null}]
  ));
  const document = {getElementById(id) {
    assert(nodes.has(id), slug + ": unknown element " + id);
    return nodes.get(id);
  }};
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)]
    .map(match => match[1]).filter(source => source.trim());
  assert.equal(scripts.length, 1, slug + ": expected one inline controller");
  const window = {[globalName]: require("./" + slug + ".js")};
  vm.runInNewContext(scripts[0], {
    window, document,
    fetch() {throw new Error("buyer packet must not make network calls");},
  }, {filename: slug + ".html"});
  assert.equal(typeof nodes.get("packet").onclick, "function");
  nodes.get("packet").onclick();
  const packet = JSON.parse(nodes.get("output").textContent);
  assert.equal(packet.offer.diagnosticUsd, 199);
  assert.equal(packet.offer.window, "one business day");
  assert.equal(packet.offer.clock, packet.offer.window);
  assert.equal(packet.externalMessagesSent, 0);
  assert.equal(packet.cashUsd, 0);
}
console.log("BUYER_PACKET_COMPATIBILITY_PASS");
"""
        result = subprocess.run(
            ["node", "-e", script], cwd=ROOT, capture_output=True,
            text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BUYER_PACKET_COMPATIBILITY_PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
