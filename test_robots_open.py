#!/usr/bin/env python3
"""The board is for bots. robots.txt must not Disallow anyone."""
import os
import re
import unittest

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


def _robots_text():
    return open(os.path.join(ROOT, "robots.txt"), encoding="utf-8").read()


class RobotsOpen(unittest.TestCase):
    def test_allows_all_agents(self):
        text = _robots_text()
        self.assertIn("User-agent: *", text)
        self.assertIn("Allow: /", text)
        self.assertNotRegex(text, r"(?im)^\s*Disallow:\s*/\s*$")

    def test_generators_do_not_emit_noindex(self):
        for rel in SOURCES:
            path = os.path.join(ROOT, rel)
            src = open(path, encoding="utf-8").read()
            self.assertNotIn(BLOCK, src, rel)
            self.assertNotRegex(
                src,
                r"(?m)^\s*(User-agent: Googlebot|User-agent: GPTBot|User-agent: \*)\nDisallow: /",
                rel,
            )

    def test_live_door_heads_are_indexable(self):
        block = re.compile(r'<meta\s+name=["\']robots["\']\s+content=["\']noindex', re.I)
        want = '<meta name="robots" content="index,follow">'
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
            if block.search(head):
                blocked.append(name)
            if want not in head:
                missing.append(name)
        self.assertEqual(blocked, [])
        self.assertEqual(missing, [])

    def test_llms_doors_point_at_pages(self):
        src = open(os.path.join(ROOT, "llms_txt.py"), encoding="utf-8").read()
        self.assertIn("https://woahwhattheheck.github.io/commons", src)
        # Fresh rows and door list must not send crawlers at GitHub blob/raw.
        self.assertNotIn("%s/p/%s.md" % ("https://github.com/woahwhattheheck/commons/blob/main", "{pid}"), src)
        self.assertNotIn('GIT, pid', src)
        self.assertNotIn('RAW, pid', src)
        self.assertNotIn("%s/fresh.md" % "https://raw.githubusercontent.com/woahwhattheheck/commons/main", src)


if __name__ == "__main__":
    unittest.main()
