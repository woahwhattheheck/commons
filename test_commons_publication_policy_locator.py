#!/usr/bin/env python3
"""Regression: browser and Node publication classifiers match the Python rules.

Inline source locators still identify a technical report. Initialization,
transactional, and lifecycle wording can carry an ordinary diagnostic. Code
spans stay out of assertion scanning. A link or the word bug alone does not
open the exception.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = (
    ("backtick-sha-init", "Parser initialization failed. Repair tracked at `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`.", True, None),
    ("transactional-url", "Transactional startup failed. Bug filed at https://github.com/example/repo/issues/12.", True, None),
    ("lifecycle-pr", "Lifecycle handling failed. Submitted https://github.com/example/repo/pull/4.", True, None),
    ("code-span-not-assertion", "The build is complete. `I disagree with the result and it failed.`", True, None),
    ("link-alone", "The service failed. See https://github.com/example/repo/issues/9.", False, "unfavorable_finding"),
    ("bug-alone", "There is a bug. The service failed.", False, "unfavorable_finding"),
    ("bug-link-no-detail", "The service failed. Bug at https://github.com/example/repo/issues/9.", False, "unfavorable_finding"),
    ("peer-evaluation-stays-out", "The peer claim failed in the parser. Bug at https://github.com/example/repo/issues/9.", False, "unfavorable_finding"),
    ("fence-sha", "Initialization failed during repair.\n\n```\naaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n```", True, None),
    ("plain-disagree", "I disagree with that approach.", False, "general_disagreement"),
)


def _python_policy():
    spec = importlib.util.spec_from_file_location(
        "commons_publication_policy", ROOT / "commons_publication_policy.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError("commons_publication_policy.py is missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _node_decisions(filename: str) -> dict:
    script = r"""
const fs = require("fs");
const pol = require(process.argv[1]);
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const out = {};
for (const item of cases) {
  const decision = pol.checkPublication(item.body, item.subject || "");
  out[item.name] = {allowed: decision.allowed, rule: decision.rule};
}
process.stdout.write(JSON.stringify(out));
"""
    payload = [{"name": name, "body": body, "subject": ""} for name, body, _allowed, _rule in CASES]
    completed = subprocess.run(
        ["node", "-e", script, str(ROOT / filename)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"node failed for {filename}")
    return json.loads(completed.stdout)


class PublicationLocatorParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python = _python_policy()
        cls.browser = _node_decisions("commons-publication-policy.js")
        cls.node = _node_decisions("commons-publication-policy.cjs")

    def test_browser_and_node_copies_are_the_same_rules(self):
        browser = (ROOT / "commons-publication-policy.js").read_text(encoding="utf-8")
        node = (ROOT / "commons-publication-policy.cjs").read_text(encoding="utf-8")
        self.assertEqual(browser, node)

    def test_inline_locators_and_diagnostic_wording(self):
        for name, body, allowed, rule in CASES:
            with self.subTest(name=name):
                python_decision = self.python.check_publication(body)
                self.assertEqual(python_decision["allowed"], allowed)
                self.assertEqual(python_decision["rule"], rule)
                self.assertEqual(self.browser[name], {"allowed": allowed, "rule": rule})
                self.assertEqual(self.node[name], {"allowed": allowed, "rule": rule})


if __name__ == "__main__":
    unittest.main()
