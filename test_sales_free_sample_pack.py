#!/usr/bin/env python3
"""Canaries for the public FREE SAMPLE sales pack.

The door must cite the live GRBN organ / sidecar numbers. The sales
insert is a paste sheet, not outreach, and must not claim a titan walk
or leak factory language.
"""
from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ORGAN = ROOT / "excerpts" / "20260823" / "muhl_grbn.mno"
CARD = ROOT / "ground" / "SUBZERO_GRBN.md"
SIDECAR = ROOT / "excerpts" / "20260823" / "grbn_circuits.json"
RECEIPT = ROOT / "revenue" / "dio" / "examples" / "substrate_delivery.json"
PAGE = ROOT / "free-sample.html"
INSERT = ROOT / "sales-sample" / "FREE-SAMPLE-SALES-INSERT.md"
POST = ROOT / "p" / "sales-free-sample-pack-20260830-01.md"

BANNED_INSERT = (
    "titan-walk",
    "titan walk",
    "factory-leak",
    "factory leak",
)


def _header(blob: bytes) -> tuple[str, int, int, int, int, int]:
    magic = blob[:8].decode("ascii")
    n_gate, n_wires, n_in, n_out, depth = struct.unpack_from("<IIIII", blob, 8)
    return magic, n_gate, n_wires, n_in, n_out, depth


class SalesFreeSamplePackTests(unittest.TestCase):
    def test_page_cites_current_grbn_header_and_sha(self) -> None:
        blob = ORGAN.read_bytes()
        sha = hashlib.sha256(blob).hexdigest()
        magic, n_gate, n_wires, n_in, n_out, depth = _header(blob)
        page = PAGE.read_text(encoding="utf-8")
        card = CARD.read_text(encoding="utf-8")
        sidecar = SIDECAR.read_text(encoding="utf-8")
        receipt = RECEIPT.read_text(encoding="utf-8")

        self.assertEqual(magic, "MUHLGRBN")
        self.assertEqual(n_gate, 8704)
        self.assertEqual(len(blob), 228638)
        self.assertIn(sha, card)
        self.assertIn(sha, receipt)
        self.assertIn("MUHLGRBN", sidecar)

        for token in (sha, magic, "8704", "8962", "228638", "4d55484c4752424e"):
            self.assertIn(token, page, token)
        self.assertIn("excerpts/20260823/muhl_grbn.mno", page)
        self.assertIn("ground/SUBZERO_GRBN.md", page)
        self.assertIn("STRUCTURAL", page)
        self.assertIn("OWNER-PC-ONLY", page)
        self.assertIn("RUNTIME-MISSING", page)
        self.assertIn("host/shared_one_lever.py --json", page)
        self.assertIn("substrate_receipt.py check", page)
        self.assertNotIn("login required", page.lower())
        self.assertNotIn("must authenticate", page.lower())

    def test_insert_is_a_sales_paste_not_a_walk_claim(self) -> None:
        insert = INSERT.read_text(encoding="utf-8")
        page = PAGE.read_text(encoding="utf-8")
        sha = hashlib.sha256(ORGAN.read_bytes()).hexdigest()
        self.assertIn("https://woahwhattheheck.github.io/commons/free-sample.html", insert)
        self.assertIn(sha, insert)
        self.assertIn("STRUCTURAL", insert)
        self.assertIn("OWNER-PC-ONLY", insert)
        self.assertIn("RUNTIME-MISSING", insert)
        self.assertIn("Measured-vs-demonstrated", insert)
        self.assertIn("Public excerpt catalog", insert)
        self.assertIn("GRBN structural briefing", insert)
        self.assertIn("not outreach", insert.lower())
        self.assertIn("Not buyers", insert)
        lowered = insert.lower()
        for banned in BANNED_INSERT:
            self.assertNotIn(banned, lowered, banned)
        self.assertIn("sales-sample/FREE-SAMPLE-SALES-INSERT.md", page)

    def test_hub_and_resources_link_the_door(self) -> None:
        needle = 'href="./free-sample.html"'
        hub = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        resources = (ROOT / "resources.html").read_text(encoding="utf-8")
        self.assertIn(needle, hub)
        self.assertIn(needle, boards)
        self.assertIn(needle, resources)
        self.assertIn("resources-tab-freshness:begin", resources)

    def test_receipt_names_scope(self) -> None:
        post = POST.read_text(encoding="utf-8")
        self.assertIn("from: SETH", post)
        self.assertIn("to: TABLE", post)
        self.assertIn("id: sales-free-sample-pack-20260830-01", post)
        self.assertIn("DURABLE_PAGE", post)
        self.assertIn("no outreach", post.lower())
        self.assertIn("ChatGPT/Claude doorbells out of scope", post)
        self.assertIn("cursor-help-gpt-muhl-inference-20260830-01", post)
        page = PAGE.read_text(encoding="utf-8")
        insert = INSERT.read_text(encoding="utf-8")
        self.assertIn("cursor-help-gpt-muhl-inference-20260830-01", page)
        self.assertIn("cursor-help-gpt-muhl-inference-20260830-01", insert)
        self.assertIn("GRBN structural", page)
        self.assertIn("not EVE", page)
        self.assertIn("pitch_pack.json", insert)


if __name__ == "__main__":
    unittest.main()
