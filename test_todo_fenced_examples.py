#!/usr/bin/env python3
"""Fenced examples must not become real directives in either TODO parser."""
import html.parser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import todo_gen

ROOT = Path(__file__).resolve().parent
NODE = shutil.which("node")
REAL = "## Open\n### 1. Real directive\n"
STATUS = "**Status:** OPEN pending\n"
EXPECTED = [["1", "Real directive", "OPEN pending", "Open"]]
PHANTOM = "## Wrong section\n### 999. Example only\n**Status:** LANDED\n"
CASES = {
    "backtick_example": (REAL + "```markdown\n" + PHANTOM + "```\n" + STATUS, EXPECTED),
    "tilde_example": (REAL + "~~~markdown\n" + PHANTOM + "~~~\n" + STATUS, EXPECTED),
    "three_space_fence": (REAL + "   ```md\n" + PHANTOM + "  ```\t\n" + STATUS, EXPECTED),
    "crlf": ((REAL + "```md\n" + PHANTOM + "```\n" + STATUS).replace("\n", "\r\n"), EXPECTED),
    "longer_closer": (REAL + "~~~md\n" + PHANTOM + "~~~~~  \n" + STATUS, EXPECTED),
    "shorter_is_not_closer": (REAL + "````md\n```\n" + PHANTOM + "````\n" + STATUS, EXPECTED),
    "other_kind_is_not_closer": (REAL + "~~~\n```\n" + PHANTOM + "~~~\n" + STATUS, EXPECTED),
    "closer_with_info_is_not_closer": (REAL + "```\n```md\n" + PHANTOM + "```\n" + STATUS, EXPECTED),
    "indented_closer_is_not_closer": (REAL + "```\n    ```\n" + PHANTOM + "```\n" + STATUS, EXPECTED),
    "unclosed_fence": (REAL + STATUS + "```md\n" + PHANTOM, EXPECTED),
    "fence_ends_status_continuation": (
        REAL + STATUS + "```\nexample body\n```\nnot part of status\n", EXPECTED),
    "example_before_first_directive": ("```\n" + PHANTOM + "```\n" + REAL + STATUS, EXPECTED),
    "invalid_backtick_info": ("```bad`info\n" + REAL + STATUS, EXPECTED),
    "tilde_info_with_backticks": ("~~~a`b\n" + PHANTOM + "~~~\n" + REAL + STATUS, EXPECTED),
    "short_delimiters_are_not_fences": ("``\n~~\n" + REAL + STATUS, EXPECTED),
    "four_space_opener_is_not_fence": ("    ```\n" + REAL + STATUS, EXPECTED),
    "ordinary_wrapping_and_escaping": (
        "## Open <work>\n### 2. Keep <tags> & `code`\n**Asked:** today · **Status:** PARTIAL implemented\nand covered\n\n",
        [["2", "Keep <tags> & code", "PARTIAL implemented and covered", "Open <work>"]]),
}


class Cells(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag == "td":
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def rendered_rows(markup):
    parser = Cells()
    parser.feed(markup)
    return parser.rows


# Execute the actual inline browser program, including fetch/catch and DOM writes.
# Only the browser's document and transport are replaced; no parser is reimplemented.
BROWSER_RUNNER = r'''
const fs = require("fs"), vm = require("vm");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
(async function () {
  const result = {};
  for (const [name, text] of Object.entries(input.cases)) {
    const nodes = {rows: {innerHTML: "FALLBACK"}, src: {textContent: "baked"}};
    const document = {
      getElementById: id => nodes[id],
      createElement: () => ({textContent: "", get innerHTML() {
        return this.textContent.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      }})
    };
    const fetch = () => name === "fetch_failure"
      ? Promise.resolve({ok: false, status: 503})
      : Promise.resolve({ok: true, text: () => Promise.resolve(text)});
    vm.runInNewContext(input.script, {document, fetch}, {timeout: 1000});
    await new Promise(resolve => setImmediate(resolve));
    result[name] = {html: nodes.rows.innerHTML, stamp: nodes.src.textContent};
  }
  process.stdout.write(JSON.stringify(result));
})().catch(error => {console.error(error); process.exitCode = 1;});
'''


class PythonFences(unittest.TestCase):
    pass


@unittest.skipUnless(NODE, "Node.js is required to execute the live browser parser")
class BrowserFences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        page = (ROOT / "todo.html").read_text(encoding="utf-8")
        scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
        scripts = [script for script in scripts if 'fetch("./DIRECTIVES.md"' in script]
        if len(scripts) != 1:
            raise AssertionError("expected exactly one live TODO parser")
        fixtures = {name: case[0] for name, case in CASES.items()}
        fixtures.update(code_only="```md\n" + PHANTOM + "```\n", fetch_failure="")
        run = subprocess.run(
            [NODE, "-e", BROWSER_RUNNER],
            input=json.dumps({"script": scripts[0], "cases": fixtures}),
            text=True, capture_output=True, check=True, timeout=15,
        )
        cls.results = json.loads(run.stdout)

    def test_code_only_keeps_fallback(self):
        result = self.results["code_only"]
        self.assertEqual(result["html"], "FALLBACK")
        self.assertIn("parsed 0 directives", result["stamp"])

    def test_fetch_failure_keeps_fallback(self):
        result = self.results["fetch_failure"]
        self.assertEqual(result["html"], "FALLBACK")
        self.assertIn("503", result["stamp"])


def python_case(name):
    def test(self):
        text, expected = CASES[name]
        self.assertEqual(rendered_rows(todo_gen.render(todo_gen.parse(text))), expected)
    return test


def browser_case(name):
    def test(self):
        text, expected = CASES[name]
        result = self.results[name]
        self.assertEqual(rendered_rows(result["html"]), expected)
        self.assertTrue(result["stamp"].startswith("live — "), result["stamp"])
        self.assertEqual(rendered_rows(result["html"]), rendered_rows(todo_gen.render(todo_gen.parse(text))))
    return test


for case_name in CASES:
    setattr(PythonFences, "test_" + case_name, python_case(case_name))
    setattr(BrowserFences, "test_" + case_name, browser_case(case_name))


class GeneratorCLI(unittest.TestCase):
    def run_generator(self, directives):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = '<header>keep</header><tbody id="rows">FALLBACK</tbody><footer>keep</footer>'
            (root / "todo.html").write_text(page, encoding="utf-8")
            (root / "DIRECTIVES.md").write_text(directives, encoding="utf-8")
            run = subprocess.run([sys.executable, str(ROOT / "todo_gen.py")], cwd=root,
                                 text=True, capture_output=True, timeout=10)
            return run, (root / "todo.html").read_text(encoding="utf-8"), page

    def test_cli_writes_real_rows_only(self):
        run, page, original = self.run_generator(CASES["backtick_example"][0])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("1 directives baked", run.stdout)
        self.assertEqual(rendered_rows(page), EXPECTED)
        self.assertTrue(page.startswith("<header>keep</header>"))
        self.assertTrue(page.endswith("<footer>keep</footer>"))

    def test_cli_code_only_leaves_file_untouched(self):
        run, page, original = self.run_generator("```md\n" + PHANTOM + "```\n")
        self.assertEqual(run.returncode, 1)
        self.assertIn("parsed 0 directives", run.stderr)
        self.assertEqual(page, original)


if __name__ == "__main__":
    unittest.main()
