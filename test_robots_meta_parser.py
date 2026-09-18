"""Exercise the real door guard against temporary HTML, without network I/O."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_robots_open as guard

ALLOW = '<meta name="robots" content="index,follow">'
CANARIES = (
    "open-model-release-receipt.html",
    "proof-spiral-succinct-argument.html",
    "repair-booking-preflight.html",
    "salesforce-contact-preflight.html",
    "paperwork-included.html",
    "catalog.html",
    "claude-paste.html",
    "hub-eyes.html",
    "insights.html",
    "wire.html",
)


class RobotsMetaParserRegression(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for name in CANARIES:
            (self.root / name).write_text(self.page(ALLOW), encoding="utf-8")
        root_patch = patch.object(guard, "ROOT", str(self.root))
        root_patch.start()
        self.addCleanup(root_patch.stop)

    @staticmethod
    def page(tags):
        return '<!doctype html><html><head>' + tags + '</head><body></body></html>'

    def check(self, tags):
        (self.root / "candidate.html").write_text(self.page(tags), encoding="utf-8")
        guard.RobotsOpen("test_live_door_heads_are_indexable").test_live_door_heads_are_indexable()

    def rejected(self, tags):
        with self.assertRaises(AssertionError):
            self.check(tags)

    def test_plain_allow_is_accepted(self):
        self.check(ALLOW)

    def test_later_noindex_is_rejected(self):
        self.rejected(ALLOW + '<meta name="robots" content="noindex">')

    def test_later_nofollow_is_rejected(self):
        self.rejected(ALLOW + '<meta name="robots" content="nofollow">')

    def test_earlier_block_is_not_overridden(self):
        self.rejected('<meta name="robots" content="noindex">' + ALLOW)

    def test_comment_only_is_rejected(self):
        self.rejected('<!-- ' + ALLOW + ' -->')

    def test_script_string_only_is_rejected(self):
        self.rejected('<script>const sample = \'' + ALLOW + '\';</script>')

    def test_style_text_only_is_rejected(self):
        self.rejected('<style>/* ' + ALLOW + ' */</style>')

    def test_commented_block_does_not_block_real_allow(self):
        self.check('<!-- <meta name="robots" content="noindex"> -->' + ALLOW)

    def test_data_name_is_not_name(self):
        self.rejected('<meta data-name="robots" content="index,follow">')

    def test_data_content_is_not_content(self):
        self.rejected('<meta name="robots" data-content="index,follow">')

    def test_attribute_order_case_and_quoted_greater_than(self):
        self.check('<META data-note="a > b" CONTENT="INDEX, FOLLOW" NAME="ROBOTS">')

    def test_unquoted_block_is_rejected(self):
        self.rejected(ALLOW + '<meta name=robots content=noindex>')

    def test_single_quotes_and_self_closing_tag(self):
        self.check("<meta content='index,follow' name='robots'/>")

    def test_missing_required_directives_are_rejected(self):
        for content in ('', 'index', 'follow', 'noindex,nofollow'):
            with self.subTest(content=content):
                self.rejected('<meta name="robots" content="' + content + '">')

    def test_missing_tag_is_rejected(self):
        self.rejected('<title>No robots tag</title>')

    def test_late_tag_does_not_expand_inspection_window(self):
        self.rejected(' ' * 4000 + ALLOW)

    def test_split_tags_do_not_weaken_explicit_pair_requirement(self):
        self.rejected('<meta name="robots" content="index"><meta name="robots" content="follow">')

    def test_redundant_nonblocking_tag_is_accepted(self):
        self.check(ALLOW + '<meta name="robots" content="max-snippet:0">')

    def test_canary_presence_still_required(self):
        (self.root / "wire.html").unlink()
        self.rejected(ALLOW)


if __name__ == "__main__":
    unittest.main()
