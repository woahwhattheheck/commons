#!/usr/bin/env python3
"""Peer packets stay isolated from order totals and destination offices."""

from __future__ import annotations

import unittest

from charttrace.assurance.evaluate import gold_packet, packet_to_canonical_bytes
from charttrace.assurance.release_guards import peer_input_isolation
from charttrace.fixtures.oracle import build_oracle


class ChartTracePricingTests(unittest.TestCase):
    def test_gold_packet_has_no_economic_fields(self) -> None:
        payload = packet_to_canonical_bytes(gold_packet(build_oracle())).decode("utf-8")
        self.assertNotIn("order_total", payload)
        self.assertNotIn("destination_office", payload)
        self.assertNotIn("recovery_share", payload)
        self.assertTrue(peer_input_isolation({})["pass"])

    def test_economic_fields_fail_isolation(self) -> None:
        self.assertFalse(peer_input_isolation({"order_total": 15000})["pass"])
        self.assertFalse(peer_input_isolation({"recovery_share": "15"})["pass"])
