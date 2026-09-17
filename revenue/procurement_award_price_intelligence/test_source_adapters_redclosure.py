from __future__ import annotations

import copy
import json
import unittest

from revenue.procurement_award_price_intelligence.source_adapters import Error, compile
from revenue.procurement_award_price_intelligence.test_source_adapters import (
    award,
    bid,
    document,
    raw,
    request,
)


class SourceAdapterRedClosureTests(unittest.TestCase):
    def test_query_and_fragment_source_uris_fail_closed(self):
        secret_uris = (
            "https://buyer.example.gov/award?token=secret-value",
            "https://buyer.example.gov/award?X-Amz-Signature=deadbeef",
            "https://buyer.example.gov/award#access_token=secret-value",
            "https://buyer.example.gov/award?",
            "https://buyer.example.gov/award#",
        )
        for uri in secret_uris:
            doc = document("AWARD_NOTICE_JSON_V1", award(), "AWARD_NOTICE")
            doc["source"]["uri"] = uri
            with self.subTest(uri=uri):
                with self.assertRaisesRegex(Error, "queryless fragmentless https URI"):
                    compile(raw(request([doc])))

    def test_raw_source_cannot_be_reminted_under_fresh_source_identity(self):
        first = document("AWARD_NOTICE_JSON_V1", award(), "AWARD_NOTICE", source_id="source-a")
        remint = copy.deepcopy(first)
        remint["source"]["source_id"] = "source-b"
        remint["source"]["uri"] = "https://buyer.example.gov/alternate-locator"
        with self.assertRaisesRegex(Error, "duplicate retained raw source"):
            compile(raw(request([first, remint])))

    def test_same_raw_source_cannot_be_resliced_into_second_payload(self):
        first = document("AWARD_NOTICE_JSON_V1", award(), "AWARD_NOTICE", source_id="source-a")
        changed_payload = award()
        changed_payload["award_id"] = "a2"
        changed_payload["award_amount_minor"] = 999999
        second = document("AWARD_NOTICE_JSON_V1", changed_payload, "AWARD_NOTICE", source_id="source-b")
        second["source"]["sha256"] = first["source"]["sha256"]
        with self.assertRaisesRegex(Error, "duplicate retained raw source"):
            compile(raw(request([first, second])))

    def test_legitimate_multiple_rows_live_inside_one_retained_source(self):
        payload = bid()
        payload["rows"] = [
            {"row_id": "r1", "vendor": "A LLC", "bid_amount_minor": 111100, "responsive": True},
            {"row_id": "r2", "vendor": "B LLC", "bid_amount_minor": 121200, "responsive": True},
        ]
        doc = document("BID_TABULATION_JSON_V1", payload, "BID_TABULATION")
        price_bytes, packet_bytes, _ = compile(raw(request([doc])))
        price = json.loads(price_bytes)
        packet = json.loads(packet_bytes)
        self.assertEqual(1, len(price["sources"]))
        self.assertEqual(2, len(price["observations"]))
        self.assertEqual(2, packet["emitted_observation_count"])
        self.assertEqual({"A LLC", "B LLC"}, {row["vendor"] for row in price["observations"]})


if __name__ == "__main__":
    unittest.main()
