import pathlib
import unittest

import board_ingest


ROOT = pathlib.Path(__file__).resolve().parent


class TrustDoctrineTests(unittest.TestCase):
    def test_every_root_page_naming_muhlnickel_surfaces_law(self):
        pages = []
        for path in sorted(ROOT.glob("*.html")):
            text = path.read_text(encoding="utf-8")
            if "muhlnickel" not in text.lower():
                continue
            pages.append(path.name)
            self.assertIn('id="trust-through-proof"', text, path.name)
            self.assertTrue(
                'href="./trust.html"' in text or path.name == "trust.html",
                path.name,
            )
        self.assertGreaterEqual(len(pages), 27)

    def test_injector_is_scoped_and_idempotent(self):
        source = "<html><body><p>Muhlnickel</p></body></html>"
        once = board_ingest.inject_trust_doctrine(source)
        twice = board_ingest.inject_trust_doctrine(once)
        self.assertIn('id="trust-through-proof"', once)
        self.assertEqual(once, twice)
        self.assertEqual(
            board_ingest.inject_trust_doctrine("<html><body>other</body></html>"),
            "<html><body>other</body></html>",
        )

    def test_commerce_corollary_preserves_truth(self):
        page = (ROOT / "trust.html").read_text(encoding="utf-8")
        self.assertIn("The commerce corollary", page)
        self.assertIn("make the offer, ask for the sale, fulfill", page)
        self.assertIn("invented demand", page)
        self.assertIn("fabricated cash", page)


if __name__ == "__main__":
    unittest.main()
