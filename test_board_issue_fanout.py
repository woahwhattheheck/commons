import json
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent
COMMONS_BOARD = ROOT / ".github" / "workflows" / "commons-board.yml"
BOARD_LABEL = ROOT / ".github" / "workflows" / "board-label.yml"

def _extract_named_script(workflow: str, name: str) -> str:
    tail = workflow.split(f"      - name: {name}\n", 1)[1]
    tail = tail.split("          script: |\n", 1)[1]
    lines = []
    for line in tail.splitlines():
        if line.startswith("            "):
            lines.append(line[12:])
        elif not line:
            lines.append("")
        else:
            break
    return "\n".join(lines)

NODE_HARNESS = r"""
const src = process.env.LABEL_SCRIPT;
const issue = JSON.parse(process.env.ISSUE);
const failures = Number(process.env.FAILURES || "0");
let attempts = 0;
const calls = [];
global.setTimeout = (fn) => { fn(); return 0; };
const context = {payload: {issue}, repo: {owner: "owner", repo: "repo"}};
const github = {rest: {issues: {addLabels: async (args) => {
  attempts += 1;
  if (attempts <= failures) throw new Error("simulated");
  calls.push(args);
}}}};
const core = {warning: () => {}};
(async () => {
  let thrown = null;
  try {
    const run = new Function("context", "github", "core",
      "return (async () => {\n" + src + "\n})();");
    await run(context, github, core);
  } catch (error) {
    thrown = String(error && error.message || error);
  }
  process.stdout.write(JSON.stringify({attempts, calls, thrown}));
})().catch((error) => { process.stderr.write(String(error)); process.exit(2); });
"""

class BoardIssueFanoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.commons = COMMONS_BOARD.read_text(encoding="utf-8")
        cls.manual = BOARD_LABEL.read_text(encoding="utf-8")
        cls.script = _extract_named_script(
            cls.commons, "label template-matching board issue"
        )

    def run_label(self, issue, failures=0):
        env = dict(os.environ)
        env.update(LABEL_SCRIPT=self.script, ISSUE=json.dumps(issue),
                   FAILURES=str(failures))
        result = subprocess.run(["node", "-e", NODE_HARNESS], check=True,
                                capture_output=True, text=True, env=env)
        return json.loads(result.stdout)

    def test_only_commons_board_labels_opened_issues_automatically(self):
        automatic = []
        for path, text in ((COMMONS_BOARD, self.commons),
                           (BOARD_LABEL, self.manual)):
            opened = re.search(r"(?m)^  issues:\n    types: \[opened\]$", text)
            if opened and 'labels: ["board"]' in text:
                automatic.append(path.name)
        self.assertEqual(automatic, ["commons-board.yml"])
        self.assertIn("workflow_dispatch:", self.manual)
        self.assertNotRegex(self.manual,
                            r"(?m)^  issues:\n    types: \[opened\]$")
        self.assertRegex(
            self.manual,
            r"(?ms)^      issue_number:\n        description: .+\n"
            r"        required: true\n        type: number$",
        )

    def test_issue_runs_preserve_lossless_current_main_concurrency(self):
        self.assertIn("'carrier: slack-connector'", self.commons)
        self.assertIn("&& 'slack-batch' || github.event_name", self.commons)
        self.assertIn("&& 'queue' || github.event.issue.number || 'poll'", self.commons)
        self.assertIn("cancel-in-progress: false", self.commons)

    def test_label_failure_keeps_completed_ingest_and_device_eligible(self):
        label_at = self.commons.index(
            "      - name: label template-matching board issue")
        complete_at = self.commons.index(
            "      - name: mark successful ingest for reusable device work")
        device_at = self.commons.index("\n  device:\n")
        self.assertLess(complete_at, label_at)
        self.assertLess(label_at, device_at)
        self.assertIn("if: always() && github.event_name == 'issues'",
                      self.commons[label_at:device_at])
        self.assertNotIn("continue-on-error:",
                         self.commons[label_at:device_at])
        self.assertIn(
            "ingest_complete: ${{ steps.ingest_complete.outputs.complete }}",
            self.commons,
        )
        self.assertIn(
            "if: always() && needs.ingest.outputs.ingest_complete == 'true' "
            "&& needs.ingest.outputs.has_pending_device == 'true'",
            self.commons,
        )

    def test_matching_issue_adds_board_once(self):
        result = self.run_label(
            {"number": 41, "body": "from: a\nto: b\nid: abcdefgh\n---\nbody"})
        self.assertIsNone(result["thrown"])
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(len(result["calls"]), 1)
        self.assertEqual(result["calls"][0]["labels"], ["board"])
        self.assertEqual(result["calls"][0]["issue_number"], 41)

    def test_nonmatching_or_pull_request_is_noop(self):
        bodies = [
            "from: a\nto: b\nid: abcdefgh",
            "to: b\nid: abcdefgh\n---",
            "from: a\nid: abcdefgh\n---",
            "from: a\nto: b\n---",
            "from: a\nto: b\nid: short\n---",
            "from: a\nto: b\n---\nid: abcdefgh",
        ]
        for body in bodies:
            with self.subTest(body=body):
                result = self.run_label({"number": 42, "body": body})
                self.assertEqual(result["attempts"], 0)
                self.assertEqual(result["calls"], [])
                self.assertIsNone(result["thrown"])
        result = self.run_label({
            "number": 43,
            "body": "from: a\nto: b\nid: abcdefgh\n---",
            "pull_request": {},
        })
        self.assertEqual(result["attempts"], 0)
        self.assertEqual(result["calls"], [])

    def test_two_transient_failures_then_one_label(self):
        result = self.run_label(
            {"number": 44, "body": "from: a\nto: b\nid: abcdefgh\n---"},
            failures=2)
        self.assertIsNone(result["thrown"])
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(len(result["calls"]), 1)
        self.assertEqual(result["calls"][0]["labels"], ["board"])

    def test_permanent_failure_is_bounded_and_red(self):
        result = self.run_label(
            {"number": 45, "body": "from: a\nto: b\nid: abcdefgh\n---"},
            failures=3)
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(result["calls"], [])
        self.assertEqual(result["thrown"], "simulated")

if __name__ == "__main__":
    unittest.main()
