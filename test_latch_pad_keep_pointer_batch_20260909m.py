#!/usr/bin/env python3
from __future__ import annotations
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent
PAGES = ['pixel-unify.html', 'plug.html', 'post-http.html', 'post.html', 'preinnewhof-pfas-fieldblank-gate-lims.html', 'proof-spiral-succinct-argument.html', 'proof-to-proposal.html', 'ptl-controlled-sample-order-preflight.html', 'qlabs-qconnect-cutover-verification-lims.html', 'recents.html', 'redundancy.html', 'repair-booking-preflight.html', 'right-now.html', 'ringdelta.html', 'rmb-crosssite-courier-accession-lims.html', 'rooms.html', 'rosecity-olcc-metrc-sampling-lims.html', 'roslinct-hopkinton-paperless-qc-lims.html', 'salesforce-contact-preflight.html', 'salvage.html']
REQUIRED = ["https://webmcp-pad.vercel.app/", "1.4.5"]
class LatchPadKeepPointerBatch20260909mTest(unittest.TestCase):
    def test_all(self) -> None:
        for name in PAGES:
            with self.subTest(page=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                for n in REQUIRED:
                    self.assertIn(n, text)
if __name__ == "__main__":
    unittest.main()
