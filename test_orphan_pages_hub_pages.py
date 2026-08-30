#!/usr/bin/env python3
"""Job C link-from-boards half: six formerly orphan pages stay linked.

boards.html is generated from hub_pages.rebuild_boards
(hub_pages.py BAILIFF 2026-08-20). Hand-editing the bake alone is
reverted on the next ingest. Keep the six doors in the generator.

Does not remint nav-single-source-generation-20260830-01 (Job A).
Does not take Job B. Does not retire or delete the pages.
"""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent

# Six names from the 2026-08-20 findability cluster Job C measurement.
ORPHANS = (
    "feature-requests",
    "grave-card",
    "nojs",
    "open-door",
    "topics",
    "whisper",
)


def _href(name: str) -> str:
    return 'href="./%s.html"' % name


class OrphanPagesHubPagesTests(unittest.TestCase):
    def test_generator_and_boards_link_each_orphan(self) -> None:
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        boards = (ROOT / "boards.html").read_text(encoding="utf-8")
        for name in ORPHANS:
            needle = _href(name)
            self.assertIn(needle, gen, needle)
            self.assertIn(needle, boards, needle)

    def test_orphan_pages_still_exist(self) -> None:
        for name in ORPHANS:
            path = ROOT / ("%s.html" % name)
            self.assertTrue(path.is_file(), str(path))

    def test_does_not_remint_job_a_nav_source(self) -> None:
        gen = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertIn("NAV_LINKS = (", gen)
        self.assertIn("def nav_html(parent=False):", gen)
        nav_block = gen[gen.index("NAV_LINKS = ("):gen.index("def nav_html")]
        for name in ORPHANS:
            self.assertNotIn("./%s.html" % name, nav_block)


if __name__ == "__main__":
    unittest.main()
