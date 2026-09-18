from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import hub_pages


HREF = 'href="./keep-sell.html"'
TITLE = '>KEEP vs SELL</a>'
COPY = 'Factory classification ledger. Marketing stays Bryce. No invented Stripe URLs.'
PAYMENT = 'href="./payment-capability.html"'
LOOK = 'href="./look.html"'


class KeepSellBoardProjectionTests(unittest.TestCase):
    def test_keep_sell_row_is_projected_once_in_canonical_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mod = SimpleNamespace(
                ROOT=str(root),
                CSS='<link rel="stylesheet" href="./commons.css">',
                doors=lambda: '<p class="nav"></p>',
                _write=lambda path, text: Path(path).write_text(text, encoding='utf-8'),
            )
            hub_pages.rebuild_boards(mod, {'open': [], 'receipts': 0})
            rendered = (root / 'boards.html').read_text(encoding='utf-8')

        self.assertEqual(rendered.count(HREF), 1)
        self.assertEqual(rendered.count(TITLE), 1)
        self.assertEqual(rendered.count(COPY), 1)
        self.assertLess(rendered.index(PAYMENT), rendered.index(HREF))
        self.assertLess(rendered.index(HREF), rendered.index(LOOK))


if __name__ == '__main__':
    unittest.main()
