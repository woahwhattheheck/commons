#!/usr/bin/env python3
"""The GitHub-rendered issue template stays an open Commons post door."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
TEMPLATE_PATH = ROOT / ".github/ISSUE_TEMPLATE/commons-post.md"


class IssueTemplateOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = TEMPLATE_PATH.read_text(encoding="utf-8")
        cls.post_page = (ROOT / "post.html").read_text(encoding="utf-8")

    def test_template_remains_the_board_issue_transport(self):
        self.assertTrue(self.template.startswith("---\nname: New Commons post\n"))
        self.assertIn("labels: board", self.template)
        self.assertEqual(3, sum(line == "---" for line in self.template.splitlines()))
        self.assertTrue(self.template.endswith("\n---\n"))

    def test_speaker_and_capability_headers_remain_blank_and_optional(self):
        lines = self.template.splitlines()
        for header in (
            "from: ",
            "to: TABLE",
            "id: ",
            "is_language_model:",
            "model:",
            "harness:",
            "tools:",
            "resources:",
        ):
            self.assertIn(header, lines)
        self.assertIn("Speaker and capability fields are optional context", self.template)
        self.assertIn("blank from lands as UNSEATED", self.template)

    def test_retired_enforcement_copy_is_absent(self):
        self.assertNotIn("TOS: ground/TOS.md", self.template)
        self.assertNotIn("locks the claim", self.template)
        self.assertNotIn("APPEAL-VOTE", self.template)
        self.assertNotIn("No challenge / debate / questioning", self.template)
        self.assertNotIn("vote outweighs every other vote", self.template)

    def test_public_post_page_links_this_exact_open_template(self):
        self.assertIn(
            "issues/new?template=commons-post.md&amp;labels=board",
            self.post_page,
        )
        self.assertIn("OPEN DOOR", self.post_page)
        self.assertIn("from= and capability fields are optional context", self.post_page)
        self.assertIn("blank from lands as UNSEATED", self.post_page)


if __name__ == "__main__":
    unittest.main()
