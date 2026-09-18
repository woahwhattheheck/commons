#!/usr/bin/env python3
"""Do not borrow status/prose from the next H2 section."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest

import todo_gen
from test_todo_fenced_examples import BROWSER_RUNNER, rendered_rows

ROOT = Path(__file__).resolve().parent
NODE = shutil.which("node")
FIRST = "## Work\n### 1. First directive\n"
OPEN = ["1", "First directive", "OPEN", "Work"]
PENDING = ["1", "First directive", "OPEN pending", "Work"]
CASES = {
    "no_status_borrowed": (FIRST + "## Notes\n**Status:** LANDED\n", [OPEN]),
    "no_prose_borrowed": (FIRST + "**Status:** OPEN pending\n## Notes\nunrelated prose\n", [PENDING]),
    "new_directive_in_new_section": (
        FIRST + "## Finished (history)\n### 2. Second directive\n**Status:** LANDED\n",
        [OPEN, ["2", "Second directive", "LANDED", "Finished"]]),
    "multiple_empty_sections": (FIRST + "## Next\n## Later\n**Status:** BUILT\n", [OPEN]),
    "same_number_preserved": (
        FIRST + "**Status:** OPEN pending\n## History\n### 1. Previous directive\n**Status:** DONE\n",
        [PENDING, ["1", "Previous directive", "DONE", "History"]]),
    "fenced_section_is_literal": (
        FIRST + "```md\n## Notes\n**Status:** LANDED\n```\n**Status:** OPEN pending\n", [PENDING]),
    "wrapped_status_before_section": (
        FIRST + "**Status:** PARTIAL implemented\nand tested\n## Notes\nnot status\n",
        [["1", "First directive", "PARTIAL implemented and tested", "Work"]]),
    "crlf_section_boundary": ((FIRST + "## Notes\n**Status:** LANDED\n").replace("\n", "\r\n"), [OPEN]),
}


class PythonSections(unittest.TestCase):
    pass


@unittest.skipUnless(NODE, "Node.js is required to execute the live browser parser")
class BrowserSections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        page = (ROOT / "todo.html").read_text(encoding="utf-8")
        scripts = [script for script in re.findall(r"<script>(.*?)</script>", page, re.S)
                   if 'fetch("./DIRECTIVES.md"' in script]
        if len(scripts) != 1:
            raise AssertionError("expected one TODO parser")
        run = subprocess.run([NODE, "-e", BROWSER_RUNNER],
                             input=json.dumps({"script": scripts[0], "cases": {n: c[0] for n, c in CASES.items()}}),
                             text=True, capture_output=True, timeout=15, check=True)
        cls.results = json.loads(run.stdout)


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
    return test


for case_name in CASES:
    setattr(PythonSections, "test_" + case_name, python_case(case_name))
    setattr(BrowserSections, "test_" + case_name, browser_case(case_name))


if __name__ == "__main__":
    unittest.main()
