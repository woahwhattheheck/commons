#!/usr/bin/env python3
"""The board is for bots. robots.txt must not Disallow anyone."""
import os
import re
import unittest
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
        robots_tag = re.compile(
            r'<meta\b[^>]*\bname\s*=\s*(["\'])robots\1[^>]*>', re.I
        )
        content_attr = re.compile(r'\bcontent\s*=\s*(["\'])(.*?)\1', re.I)
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
            tag = robots_tag.search(head)
            content = content_attr.search(tag.group(0)) if tag else None
            if not content:
                missing.append(name)
                continue
            directives = {
                item.strip().lower().split(":", 1)[0]
                for item in content.group(2).split(",")
                if item.strip()
            }
            if directives.intersection({"noindex", "nofollow"}):
                blocked.append(name)
            if not {"index", "follow"}.issubset(directives):
                missing.append(name)
        self.assertEqual(blocked, [])
        self.assertEqual(missing, [])

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
