#!/usr/bin/env python3
"""Runtime offline check: oracle build and score do not open connections."""

from __future__ import annotations

import socket
import unittest

from charttrace.assurance.evaluate import evaluate_packet, gold_packet
from charttrace.fixtures.oracle import build_oracle


class _DenyConnect:
    def __init__(self) -> None:
        self.attempts: list[object] = []
        self._real = socket.socket.connect

    def __enter__(self) -> "_DenyConnect":
        probe = self

        def hooked(sock: socket.socket, address: object) -> None:
            probe.attempts.append(address)
            raise RuntimeError("offline")

        socket.socket.connect = hooked  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: object) -> None:
        socket.socket.connect = self._real  # type: ignore[method-assign]


class ChartTraceNetworkTests(unittest.TestCase):
    def test_oracle_and_gold_packet_stay_offline(self) -> None:
        with _DenyConnect() as probe:
            oracle = build_oracle()
            result = evaluate_packet(gold_packet(oracle), oracle)
            self.assertTrue(result["pass"], result["failures"])
            self.assertEqual(probe.attempts, [])
