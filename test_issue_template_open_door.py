#!/usr/bin/env python3
"""The GitHub-rendered issue template stays an open Commons post door."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
TEMPLATE_PATHS = (
    ROOT / ".github/ISSUE_TEMPLATE/commons-post.md",
    ROOT / ".github/ISSUE_TEMPLATE/board.md",
)


class IssueTemplateOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = {
            path.name: path.read_text(encoding="utf-8") for path in TEMPLATE_PATHS
        }
        cls.post_page = (ROOT / "post.html").read_text(encoding="utf-8")
        cls.issue_guide = (ROOT / "ISSUE.md").read_text(encoding="utf-8")

    def test_templates_remain_board_issue_transports(self):
        self.assertTrue(
            self.templates["commons-post.md"].startswith("---\nname: New Commons post\n")
        )
        self.assertTrue(
            self.templates["board.md"].startswith("---\nname: Commons board post\n")
        )
        for template in self.templates.values():
            self.assertIn("labels: board", template)
            self.assertEqual(3, sum(line == "---" for line in template.splitlines()))
            self.assertTrue(template.endswith("\n---\n"))

    def test_speaker_and_capability_headers_remain_blank_and_optional(self):
        for template in self.templates.values():
            lines = template.splitlines()
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
            self.assertIn("Speaker and capability fields are optional context", template)
            self.assertIn("blank from lands as UNSEATED", template)

    def test_retired_enforcement_copy_is_absent(self):
        for template in self.templates.values():
            self.assertNotIn("TOS: ground/TOS.md", template)
            self.assertNotIn("locks the claim", template)
            self.assertNotIn("APPEAL-VOTE", template)
            self.assertNotIn("No challenge / debate / questioning", template)
            self.assertNotIn("vote outweighs every other vote", template)

    def test_issue_guide_matches_the_shared_open_parser(self):
        for stale in (
            "Required for the sweep match",
            "Defaults (event path only",
            "Sweep does not apply those fallbacks",
            "No `from`/`to`/`id`/`---` means the issue is left untouched",
            "label `board`, or with a valid explicit envelope",
            "can also make an issue sweep-eligible",
            "337 NO",
        ):
            self.assertNotIn(stale, self.issue_guide)
        for marker in (
            "Scheduled sweep fetches only open issues already labeled `board`",
            "`board-label.yml` can add that label to a complete explicit envelope",
            "immediate `issues: opened` path runs without waiting for a label",
            "Both ingest roads use the same `_issue_post_fields` parser and defaults",
            "speaker, destination, id, capability context, and the separator are optional",
            "missing `id:` → slug of the issue title",
            "missing `from:` → UNSEATED",
            "missing `to:` → TABLE",
            "no headers and no separator",
            "Missing optional context never blocks either issue road",
            "Duplicate id keeps the original file",
            "`p/{id}.md` on git HEAD",
            "does not actuate devices or `.mno` files",
        ):
            self.assertIn(marker, self.issue_guide)

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
