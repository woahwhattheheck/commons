from __future__ import annotations

import io
import unittest
from unittest import mock

from funded_work_freshness import Candidate, EvidenceError, MAX_HTTP_BYTES
from transport import read_bounded, validate_public_destination


class TransportContractTests(unittest.TestCase):
    def test_public_network_fence_rejects_loopback_resolution(self):
        with mock.patch("transport.socket.getaddrinfo") as lookup:
            lookup.return_value = [(2, 1, 6, "", ("127.0.0.1", 443))]
            with self.assertRaises(EvidenceError) as caught:
                validate_public_destination("https://board.example/reward")
        self.assertEqual(caught.exception.code, "unsafe_destination")

    def test_bounded_reader_rejects_oversized_response(self):
        with self.assertRaises(EvidenceError) as caught:
            read_bounded(io.BytesIO(b"x" * (MAX_HTTP_BYTES + 1)))
        self.assertEqual(caught.exception.code, "response_too_large")

    def test_invalid_url_port_is_input_error(self):
        with self.assertRaises(ValueError):
            Candidate.validated(
                candidate_url="https://example.com:bad/reward",
                platform="fixture",
                advertised_amount="5",
                currency="USD",
            )
