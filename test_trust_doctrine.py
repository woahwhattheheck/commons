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
        self.assertIn("<body>\n<section id=\"trust-through-proof\"", once)
        self.assertNotIn("<body>\\n", once)
        attributed = '<html><body class="x"><p>Muhlnickel</p></body></html>'
        attributed_once = board_ingest.inject_trust_doctrine(attributed)
        self.assertIn('id="trust-through-proof"', attributed_once)
        self.assertIn('<body class="x">\n<section id="trust-through-proof"', attributed_once)
        self.assertEqual(
            board_ingest.inject_trust_doctrine("<html><body>other</body></html>"),
            "<html><body>other</body></html>",
        )

    def test_doors_chrome_pins_trust_law(self):
        chrome = board_ingest.doors()
        self.assertIn('id="trust-through-proof"', chrome)
        self.assertIn('href="./trust.html"', chrome)

    def test_ingest_strip_of_generated_hub_page_is_restored(self):
        stripped = (
            "<!doctype html><body>"
            "<p id=\"session-banner\">open</p>"
            "<p>PUT THIS ON EVERY PAGE WITH THE MUHLNICKEL</p>"
            "</body>"
        )
        restored = board_ingest.inject_trust_doctrine(stripped)
        self.assertIn('id="trust-through-proof"', restored)
        self.assertIn('href="./trust.html"', restored)
        self.assertEqual(restored.count('id="trust-through-proof"'), 1)

    def test_hub_page_write_restores_trust_when_chrome_omits_it(self):
        import hub_pages

        class Mod:
            CSS = ""

            def doors(self):
                return "<p id=\"owner-execute-law\">OWNER LAW.</p>"

            inject_trust_doctrine = staticmethod(board_ingest.inject_trust_doctrine)

        page = hub_pages._page(Mod(), "Commons tools", "<p>Muhlnickel tools</p>")
        self.assertIn('id="trust-through-proof"', page)
        self.assertEqual(page.count('id="trust-through-proof"'), 1)

    def test_commerce_corollary_preserves_truth(self):
        page = (ROOT / "trust.html").read_text(encoding="utf-8")
        self.assertIn("The commerce corollary", page)
        self.assertIn("make the offer, ask for the sale, fulfill", page)
        self.assertIn("invented demand", page)
        self.assertIn("fabricated cash", page)


if __name__ == "__main__":
    unittest.main()
