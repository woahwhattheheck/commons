from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent
STRIPE_URL_RE = re.compile(r"https://(?:buy|donate)\.stripe\.com/[A-Za-z0-9]+")


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocking_stylesheets = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet" and attrs.get("media") != "print":
            self.blocking_stylesheets.append(attrs.get("href"))
        if tag == "script":
            self.scripts.append(attrs.get("src", "inline"))


class PagesSpeedContract(unittest.TestCase):
    def test_payment_page_is_standalone_and_canonical(self):
        catalog = (ROOT / "land" / "stripe-payment-links-20260826.md").read_text(encoding="utf-8")
        page = (ROOT / "stripe-payment-links-20260826.html").read_text(encoding="utf-8")
        self.assertEqual(STRIPE_URL_RE.findall(page), STRIPE_URL_RE.findall(catalog))
        self.assertEqual(len(STRIPE_URL_RE.findall(page)), 7)
        parser = _PageParser()
        parser.feed(page)
        self.assertEqual(parser.blocking_stylesheets, [])
        self.assertEqual(parser.scripts, [])
        self.assertLess(len(page.encode()), 6_000)

    def test_agent_rescue_has_critical_css_before_nonblocking_enhancement(self):
        page = (ROOT / "agent-rescue.html").read_text(encoding="utf-8")
        parser = _PageParser()
        parser.feed(page.split("<noscript>", 1)[0])
        self.assertEqual(parser.blocking_stylesheets, [])
        self.assertEqual(parser.scripts, [])
        self.assertIn('rel="preload" href="./commons.css?v=20260823f" as="style"', page)
        self.assertLess(page.index("<style>"), page.index("<body>"))
        self.assertLess(len(page.encode()), 12_000)


if __name__ == "__main__":
    unittest.main()
