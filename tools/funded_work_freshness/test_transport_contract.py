from __future__ import annotations

import io
import unittest
from unittest import mock

from funded_work_freshness import Candidate, EvidenceError, MAX_HTTP_BYTES
from transport import read_bounded, validate_public_destination, validate_redirect_destination


class TransportContractTests(unittest.TestCase):
    def test_public_network_fence_rejects_loopback_resolution(self):
        with mock.patch("transport.socket.getaddrinfo") as lookup:
            lookup.return_value = [(2, 1, 6, "", ("127.0.0.1", 443))]
            with self.assertRaises(EvidenceError) as caught:
                validate_public_destination("https://board.example/reward")
        self.assertEqual(caught.exception.code, "unsafe_destination")

    def test_redirect_stays_inside_recognized_sponsor_domain_family(self):
        with mock.patch("transport.socket.getaddrinfo") as lookup:
            lookup.return_value = [(2, 1, 6, "", ("8.8.8.8", 443))]
            validate_redirect_destination(
                "https://algora.io/bounties/1",
                "https://console.algora.io/bounties/1",
            )
            with self.assertRaises(EvidenceError) as caught:
                validate_redirect_destination(
                    "https://algora.io/bounties/1",
                    "https://evilalgora.io/redirected",
                )
        self.assertEqual(caught.exception.code, "unsafe_redirect")

    def test_non_sponsor_read_rejects_cross_host_redirect(self):
        with mock.patch("transport.socket.getaddrinfo") as lookup:
            lookup.return_value = [(2, 1, 6, "", ("8.8.8.8", 443))]
            with self.assertRaises(EvidenceError) as caught:
                validate_redirect_destination(
                    "https://api.github.com/repos/acme/widget/issues/1",
                    "https://attacker.example/redirected",
                )
        self.assertEqual(caught.exception.code, "unsafe_redirect")

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
