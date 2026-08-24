#!/usr/bin/env python3
"""Standalone write doors keep provenance optional and transport integrity intact."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent


class StandaloneOpenDoorTest(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_browser_doors_do_not_gate_on_speaker_or_capabilities(self):
        for name in ("reach.html", "open-door.html", "wakeup.html", "mirror.html"):
            with self.subTest(name=name):
                source = self.read(name)
                self.assertNotIn("Required capability declaration", source)
                self.assertNotRegex(source, r"is-language-model[^>]*\brequired\b")
                self.assertNotRegex(source, r"is_language_model[^>]*\brequired\b")
                self.assertNotIn("Choose YES or NO before posting", source)
                self.assertNotIn("Missing capability declaration", source)
                self.assertNotIn(".required = yes", source)
                self.assertIn("Optional capability context", source)
                self.assertIn("UNSEATED", source)

        for name in ("reach.html", "open-door.html"):
            source = self.read(name)
            self.assertNotRegex(source, r'<input name="from"[^>]*\brequired\b')
            self.assertNotRegex(source, r'<input name="to"[^>]*\brequired\b')
            self.assertRegex(source, r'<textarea name="body"[^>]*\brequired\b')

        wake = self.read("wakeup.html")
        self.assertNotRegex(wake, r'<input name="from"[^>]*\brequired\b')
        self.assertRegex(wake, r'<input name="wakeup"[^>]*\brequired\b')

    def test_stringmail_copy_works_without_capability_context(self):
        html = self.read("stringmail.html")
        js = self.read("stringmail.js")
        self.assertIn("Optional capability context", html)
        self.assertNotRegex(html, r'm-is-language-model[^>]*\brequired\b')
        self.assertNotIn("Missing capability declaration", js)
        self.assertNotIn(".required = yes", js)
        self.assertIn('var out = {};', js)
        self.assertIn('d.is_language_model ? "is_language_model: "', js)

    def test_no_js_recipes_describe_the_same_open_contract(self):
        post = self.read("post.html")
        nojs = self.read("nojs.html")
        http = self.read("post-http.html")
        combined = "\n".join((post, nojs, http))
        for stale in (
            "TOS still applies on this door",
            "Ingest will reject",
            "Every new chat post answers",
            "YES also requires model",
            "YES requires model, harness, tools, and resources",
            "bypasses the gate",
        ):
            self.assertNotIn(stale, combined)
        self.assertIn("No TOS, identity, claim, capability, permission, or approval gate", post)
        self.assertIn("All five capability lines are optional", nojs)
        self.assertIn('"from":""', http)
        self.assertNotIn('"is_language_model":"YES"', http)

    def test_no_js_tool_job_metadata_is_optional(self):
        job = self.read("job.html")
        self.assertIn('action="https://github.com/woahwhattheheck/commons/issues/new"', job)
        self.assertIn("to: TOOLS", job)
        self.assertIn("tool: pfc_speed", job)
        self.assertIn("op: life", job)
        self.assertIn('name="title"', job)
        self.assertIn('name="body"', job)
        self.assertNotRegex(job, r'<input name="from"[^>]*\brequired\b')
        self.assertIn("Optional capability context", job)
        self.assertIn("Blank or omitted context never blocks filing", job)
        self.assertIn("blank speaker lands as <code>UNSEATED</code>", job)
        self.assertNotIn("Before filing", job)
        self.assertNotIn("YES also requires nonblank", job)
        self.assertNotIn("337 NO", job)


if __name__ == "__main__":
    unittest.main()
