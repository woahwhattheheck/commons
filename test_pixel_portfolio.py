import os
import struct
import unittest


ROOT = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(ROOT, "pixel-portfolio.html")
CONCEPT = os.path.join(ROOT, "portfolio", "pixel", "ash-bell-warden-concept.png")
STRIP = os.path.join(ROOT, "portfolio", "pixel", "ash-bell-warden-sprite-strip.png")


def png_header(path):
    with open(path, "rb") as handle:
        data = handle.read(26)
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"not a PNG with IHDR: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height, data[25]


class TestPixelPortfolio(unittest.TestCase):
    def test_page_discloses_process_and_cash_truth(self):
        with open(PAGE, encoding="utf-8") as handle:
            page = handle.read()
        self.assertIn("AI-assisted", page)
        self.assertIn("not presented as hand-pixeled", page)
        self.assertIn("$0 / NOT_LANDED", page)
        self.assertIn("humans.html#interest", page)

    def test_page_references_both_original_assets(self):
        with open(PAGE, encoding="utf-8") as handle:
            page = handle.read()
        self.assertIn("portfolio/pixel/ash-bell-warden-concept.png", page)
        self.assertIn("portfolio/pixel/ash-bell-warden-sprite-strip.png", page)

    def test_assets_have_expected_dimensions_and_alpha_channel(self):
        self.assertEqual(png_header(CONCEPT), (1024, 1536, 6))
        self.assertEqual(png_header(STRIP), (1774, 887, 6))


if __name__ == "__main__":
    unittest.main()
