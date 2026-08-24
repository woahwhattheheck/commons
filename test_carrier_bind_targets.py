#!/usr/bin/env python3
"""Every root-page form wired by carrier.js has its required receipt target."""
from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).parent
BOUND_OUTPUTS = {
    "say": "out",
    "session-open": "session-open-out",
    "session-close": "session-close-out",
    "petition": "petition-out",
    "bench": "bench-out",
    "presence": "presence-out",
    "job": "out",
    "panel": "out",
    "moderation": "mod-out",
    "wake-request": "wake-out",
}


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.forms = set()

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.add(element_id)
        if tag == "form" and element_id:
            self.forms.add(element_id)


class CarrierBindTargets(unittest.TestCase):
    def test_every_bound_root_form_has_its_output_element(self):
        missing = []
        consumers = set()
        for path in sorted(ROOT.glob("*.html")):
            source = path.read_text(encoding="utf-8")
            if "carrier.js" not in source:
                continue
            parsed = IdCollector()
            parsed.feed(source)
            for form_id, output_id in BOUND_OUTPUTS.items():
                if form_id not in parsed.forms:
                    continue
                consumers.add((path.name, form_id))
                if output_id not in parsed.ids:
                    missing.append(f"{path.name}: form#{form_id} needs #{output_id}")

        self.assertIn(("commands.html", "say"), consumers)
        self.assertIn(("offer.html", "say"), consumers)
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
