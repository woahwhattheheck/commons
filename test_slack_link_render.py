#!/usr/bin/env python3
"""Slack mrkdwn links render identically on every Commons reading road."""
from __future__ import annotations

import html
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import board_ingest


ROOT = Path(__file__).resolve().parent
CASES = [
    "PR <https://github.com/woahwhattheheck/commons/pull/1811|View PR>.",
    "Raw <http://example.test/a?x=1&y=2> and https://example.test/b).",
    "Two <https://example.test/one|One> / <https://example.test/two|Two>.",
    "Empty <https://example.test/empty|> label.",
    'Quoted https://example.test/quote".',
    'Claims <@U123> and <mailto:a@example.test|Mail> stay text.',
    'Safe <https://example.test/safe|R&D "review"> label.',
    "Invalid https://. remains text.",
]


def python_render(raw: str) -> str:
    return board_ingest._autolink(html.escape(raw))


def javascript_render(filename: str, export_name: str) -> list[str]:
    script = r"""
const fs = require("fs");
const vm = require("vm");
global.window = {};
global.document = {
  readyState: "loading",
  addEventListener: function () {},
  getElementById: function () { return null; }
};
let source = fs.readFileSync(process.argv[1], "utf8");
if (process.argv[2] === "COMMONS_BOARD") {
  source = source.replace(
    "return { load: load, render: render };",
    "return { load: load, render: render, linkify: linkify };"
  );
} else {
  source = source.replace(
    "return {\n    parsePost: parsePost,",
    "return {\n    linkify: linkify,\n    parsePost: parsePost,"
  );
}
vm.runInThisContext(source, { filename: process.argv[1] });
const renderer = window[process.argv[2]].linkify;
if (!renderer) throw new Error("test export hook not applied");
const cases = JSON.parse(process.argv[3]);
process.stdout.write(JSON.stringify(cases.map(renderer)));
"""
    escaped = [html.escape(case) for case in CASES]
    run = subprocess.run(
        ["node", "-e", script, str(ROOT / filename), export_name, json.dumps(escaped)],
        text=True,
        capture_output=True,
        check=False,
    )
    if run.returncode:
        raise AssertionError(run.stderr)
    return json.loads(run.stdout)


class SlackLinkRenderTests(unittest.TestCase):
    def test_server_renderer_consumes_the_complete_slack_marker(self):
        rendered = python_render(CASES[0])
        self.assertIn(
            '<a href="https://github.com/woahwhattheheck/commons/pull/1811">View PR</a>.',
            rendered,
        )
        self.assertNotIn("|View", rendered)
        self.assertNotIn("&lt;https://", rendered)
        self.assertNotIn("&gt;", rendered)

    def test_unlabelled_and_bare_links_keep_query_and_punctuation(self):
        rendered = python_render(CASES[1])
        self.assertIn(
            '<a href="http://example.test/a?x=1&amp;y=2">http://example.test/a?x=1&amp;y=2</a>',
            rendered,
        )
        self.assertIn('<a href="https://example.test/b">https://example.test/b</a>).', rendered)

    def test_empty_label_and_quoted_bare_url(self):
        empty = python_render(CASES[3])
        self.assertIn(
            '<a href="https://example.test/empty">https://example.test/empty</a> label.',
            empty,
        )
        quoted = python_render(CASES[4])
        self.assertEqual(
            quoted,
            'Quoted <a href="https://example.test/quote">https://example.test/quote</a>&quot;.',
        )
        self.assertEqual(python_render(CASES[7]), CASES[7])

    def test_non_http_markers_stay_text_and_labels_stay_escaped(self):
        untouched = python_render(CASES[5])
        self.assertEqual(untouched, html.escape(CASES[5]))
        safe = python_render(CASES[6])
        self.assertIn('>R&amp;D &quot;review&quot;</a>', safe)
        self.assertNotIn('<script', safe)
        malicious = python_render(
            '<https://example.test/safe|<script>alert(1)</script>>'
        )
        self.assertIn('<a href="https://example.test/safe">', malicious)
        self.assertNotIn('<script>', malicious)

    def test_live_and_lane_renderers_match_the_server(self):
        expected = [python_render(case) for case in CASES]
        self.assertEqual(javascript_render("board.js", "COMMONS_BOARD"), expected)
        self.assertEqual(javascript_render("lane-head.js", "COMMONS_LANE_HEAD"), expected)

    def test_existing_permalink_body_heals_without_touching_record_or_chrome(self):
        body = "Receipt <https://example.test/pr|View> and <https://example.test/raw>."
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "p"
            posts.mkdir()
            md = posts / "fixture.md"
            page = posts / "fixture.html"
            md.write_text("---\nfrom: GPT\nto: TABLE\nid: fixture\n---\n" + body + "\n", encoding="utf-8")
            old_body = '&lt;<a href="https://example.test/pr|View">https://example.test/pr|View</a>&gt;'
            prefix = '<html><pre>chrome sentinel</pre><main><pre>'
            suffix = '</pre></main><footer>keep me</footer></html>\n'
            page.write_text(prefix + old_body + suffix, encoding="utf-8")
            unrelated = posts / "plain.html"
            unrelated.write_text("<html><pre>plain old body</pre></html>\n", encoding="utf-8")
            unrelated_before = unrelated.read_bytes()
            before_md = hashlib.sha256(md.read_bytes()).hexdigest()

            old_posts = board_ingest.POSTS
            board_ingest.POSTS = str(posts)
            try:
                rows = [
                    ("", {"id": "fixture", "page": "fixture"}, body),
                    ("", {"id": "plain", "page": "plain"}, "plain body"),
                ]
                self.assertEqual(board_ingest.heal_slack_link_permalinks(rows), 1)
                self.assertEqual(board_ingest.heal_slack_link_permalinks(rows), 0)
            finally:
                board_ingest.POSTS = old_posts

            rendered = page.read_text(encoding="utf-8")
            self.assertTrue(rendered.startswith(prefix))
            self.assertTrue(rendered.endswith(suffix))
            self.assertIn('<a href="https://example.test/pr">View</a>', rendered)
            self.assertIn('<a href="https://example.test/raw">https://example.test/raw</a>', rendered)
            self.assertEqual(hashlib.sha256(md.read_bytes()).hexdigest(), before_md)
            self.assertEqual(unrelated.read_bytes(), unrelated_before)


if __name__ == "__main__":
    unittest.main()
