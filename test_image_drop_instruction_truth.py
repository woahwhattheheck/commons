#!/usr/bin/env python3
"""Active image-drop instructions match the shipped attachment runtime."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class ImageDropInstructionTruthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = (ROOT / ".agents/skills/drop-image/SKILL.md").read_text(encoding="utf-8")
        cls.token = (ROOT / "ground/tokens/drop.md").read_text(encoding="utf-8")
        cls.picker = (ROOT / ".agents/skills/take-a-line/SKILL.md").read_text(encoding="utf-8")
        cls.directives = (ROOT / "DIRECTIVES.md").read_text(encoding="utf-8")
        cls.todo = (ROOT / "todo.html").read_text(encoding="utf-8")
        cls.ingest = (ROOT / "board_ingest.py").read_text(encoding="utf-8")
        cls.carrier = (ROOT / "carrier.js").read_text(encoding="utf-8")
        cls.reply = (ROOT / "reply.js").read_text(encoding="utf-8")
        cls.file_drop = (ROOT / "file_drop.py").read_text(encoding="utf-8")

    def test_active_drop_guides_distinguish_both_attachment_sequences(self):
        for source in (self.skill, self.token):
            for marker in (
                "image: shots/<name>.png",
                "images/<post-id>.png",
                "<post-id>-drop",
                "sent first",
                "later board rebuild",
                "image bytes never ride ntfy",
                "current HEAD",
            ):
                self.assertIn(marker.lower(), source.lower())
        for marker in (
            "two derived forms",
            "one literal target file",
            "Pillow is unavailable",
            "image-drop.html",
            "Reconcile the post id",
            "Never remint either",
        ):
            self.assertIn(marker, self.skill)
        for marker in (
            "<name>.png",
            "<name>.thumb.jpg",
            "one literal target file",
            "accepts literal target paths",
            "no protected-path gate applies",
            "preserve exact ids and existing canonical records",
        ):
            self.assertIn(marker, self.token)

    def test_runtime_uses_post_id_path_and_distinct_drop_id(self):
        for source in (self.carrier, self.reply):
            self.assertIn('return "images/" + id + ".png";', source)
            self.assertIn('var extra = "-drop";', source)
            self.assertIn("return id + extra;", source)
            self.assertIn('payload.body = "image: " + imgPath', source)
            self.assertIn("var imgPath = dropPathFor(payload.id);", source)
            self.assertIn("var path = isImageFile(file) ? dropPathFor(payload.id)", source)
            self.assertIn("openDropIssue", source)
            self.assertIn("path, dropIssueId(payload.id), b64", source)

    def test_compose_and_reply_post_before_opening_drop_issue(self):
        deliver = self.carrier[self.carrier.index("function deliver(payload"):]
        self.assertLess(
            deliver.index("return postLive(payload).then(function (got)"),
            deliver.index("var how = openDropIssue(payload.from, path"),
        )
        after_live = self.reply[self.reply.index("function afterLive(got, b64)"):]
        self.assertIn("var how = openDropIssue(src, path", after_live)
        self.assertIn(
            "return postLive(payload).then(function (got) {\n          afterLive(got, b64);",
            after_live,
        )

    def test_missing_file_is_hidden_until_later_rebuild(self):
        self.assertIn("def post_image_html", self.ingest)
        self.assertIn('path = (meta.get("image") or "").strip()', self.ingest)
        self.assertIn("if not os.path.isfile(os.path.join(ROOT, path)):", self.ingest)
        self.assertIn('return ""', self.ingest)
        for source in (self.skill, self.token):
            self.assertIn("file-drop lands", source)
            self.assertIn("later board rebuild", source)

    def test_one_file_fallback_is_documented_and_measured(self):
        self.assertIn('return [(path, data)], "stored as-is: Pillow unavailable', self.file_drop)
        self.assertIn('return [(path, data)], "stored as-is: not a decodable image', self.file_drop)
        for source in (self.skill, self.token):
            self.assertIn("one literal target file", source)
            self.assertIn("supplied bytes", source)
            self.assertNotIn("original 4 MB file is never stored", source)
        self.assertIn("one literal target file stores the supplied bytes", self.directives)
        self.assertNotIn("The original 4 MB file is never stored", self.directives)

    def test_directive_and_picker_no_longer_offer_landed_work(self):
        self.assertIn("Item 5 image upload plus post/reply attachment is BUILT", self.picker)
        self.assertIn("`test_post_image.py`", self.picker)
        self.assertNotIn("**5** (image on the post road)", self.picker)
        self.assertIn("**Status:** BUILT 2026-08-20 — upload plus post/reply attachment are live", self.directives)
        self.assertIn("BUILT</b> 2026-08-20 — upload plus post/reply attachment are live", self.todo)

    def test_retired_impossible_attachment_copy_stays_absent(self):
        active = "\n".join((self.skill, self.token, self.picker))
        self.assertNotIn("Post road is **not** built", active)
        self.assertNotIn("has no image handling", active)
        self.assertNotIn("cannot be attached *to a post*", active)
        self.assertNotIn("that is the open half", active)
        self.assertNotIn("image on the post road", active)
        self.assertNotIn("The drop road refuses canonical records", active)
        self.assertNotIn("on the **upload road**, not the post road", self.directives)
        self.assertNotIn("on the upload road, not the post road", self.todo)


if __name__ == "__main__":
    unittest.main()
