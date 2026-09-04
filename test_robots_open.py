#!/usr/bin/env python3
"""The board is for bots. robots.txt must not Disallow anyone."""
import os
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
BLOCK = 'content="noindex,nofollow,noarchive"'
SOURCES = (
    "board_ingest.py",
    "hub_pages.py",
    "memory_board.py",
    "chunk_board.py",
    "builds_ledger.py",
    "infra/host/muhl_pub_commons.py",
    "infra/host/muhl_commons_mouth.py",
    "infra/host/muhl_pages_bridge.py",
    "infra/host/muhl_world_mouth.py",
)


class _RobotsMetaParser(HTMLParser):
    """Collect real robots tags, not comments or script/style examples."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.directives = []

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        attributes = dict(attrs)
        if (attributes.get("name") or "").lower() != "robots":
            return
        content = attributes.get("content") or ""
        self.directives.append({
            item.strip().lower().split(":", 1)[0]
            for item in content.split(",")
            if item.strip()
        })


def _robots_text():
    return Path(ROOT, "robots.txt").read_text(encoding="utf-8")


class RobotsOpen(unittest.TestCase):
    def test_allows_all_agents(self):
        text = _robots_text()
        self.assertIn("User-agent: *", text)
        self.assertIn("Allow: /", text)
        self.assertNotRegex(text, r"(?im)^\s*Disallow:\s*/\s*$")

    def test_generators_do_not_emit_noindex(self):
        for rel in SOURCES:
            path = os.path.join(ROOT, rel)
            src = Path(path).read_text(encoding="utf-8")
            self.assertNotIn(BLOCK, src, rel)
            self.assertNotRegex(
                src,
                r"(?m)^\s*(User-agent: Googlebot|User-agent: GPTBot|User-agent: \*)\nDisallow: /",
                rel,
            )

    def test_live_door_heads_are_indexable(self):
        blocked = []
        missing = []
        for name in sorted(os.listdir(ROOT)):
            if not name.endswith(".html"):
                continue
            path = os.path.join(ROOT, name)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as fh:
                head = fh.read()[:4000]
            parser = _RobotsMetaParser()
            parser.feed(head)
            parser.close()
            # Any real blocking tag wins, even after an index/follow tag.
            if any(items.intersection({"noindex", "nofollow"})
                   for items in parser.directives):
                blocked.append(name)
            # Retain the explicit pair requirement; do not synthesize it
            # from separate incomplete tags or from text inside comments.
            if not any({"index", "follow"}.issubset(items)
                       for items in parser.directives):
                missing.append(name)
        self.assertEqual(blocked, [])
        self.assertEqual(missing, [])
        canaries = (
            "open-model-release-receipt.html",
            "proof-spiral-succinct-argument.html",
            "repair-booking-preflight.html",
            "salesforce-contact-preflight.html",
            "paperwork-included.html",
            # Keep the repaired hub/wire doors present as well as indexable.
            "catalog.html",
            "claude-paste.html",
            "hub-eyes.html",
            "insights.html",
            "wire.html",
        )
        for name in canaries:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, name)), name)
            self.assertNotIn(name, missing)
            self.assertNotIn(name, blocked)

    def test_llms_doors_point_at_pages(self):
        src = Path(ROOT, "llms_txt.py").read_text(encoding="utf-8")
        self.assertIn("https://woahwhattheheck.github.io/commons", src)
        # Fresh rows and door list must not send crawlers at GitHub blob/raw.
        self.assertNotIn("%s/p/%s.md" % ("https://github.com/woahwhattheheck/commons/blob/main", "{pid}"), src)
        self.assertNotIn('GIT, pid', src)
        self.assertNotIn('RAW, pid', src)
        self.assertNotIn("%s/fresh.md" % "https://raw.githubusercontent.com/woahwhattheheck/commons/main", src)


if __name__ == "__main__":
    unittest.main()
