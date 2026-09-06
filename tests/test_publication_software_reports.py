"""Replay the September 6 native Slack incident without publishing messages."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import commons_publication_policy as policy

EVENT = json.loads((ROOT / "tests/fixtures/publication_tarsnap_819.json").read_text(encoding="utf-8"))
INCIDENT = EVENT["tool_input"]["message"]
REPORT = "Submitted parser fix: https://github.com/example/parser/pull/42\n\n"

ALLOWED = [
    INCIDENT,
    REPORT + "The parser failed on an empty input. The patch adds the missing null check.",
    REPORT + "CI failed because the package was unavailable. Waiting for the registry to recover.",
    REPORT + "The API returned an incorrect total for empty input. The fix handles that case.",
    REPORT + "The CLI rejects unsupported argument values. The patch reports the valid range.",
    "CLAIM: https://github.com/example/parser/issues/42\n\nDefect: the CLI parser crashes on empty input. Preparing a fix.",
]
REJECTED = [
    "Can you prove that again?",
    REPORT + "I doubt the parser result.",
    REPORT + "The peer's accepted parser result is incorrect.",
    REPORT + "The already completed parser result is incorrect.",
    REPORT + "The peer's verified CLI implementation failed.",
    REPORT + "The peer's accepted parser result is here. It failed the API test.",
    REPORT + "Their parser implementation failed.",
    REPORT + "The parser errors show the peer's claim is unverified.",
    REPORT + "The parser failed on empty input.\n\nThe owner result is unverified.",
    REPORT + "After compaction, please re-prove the peer's established parser result.",
    REPORT + "We will withhold unfavorable findings about the parser.",
    "The service failed.",
]


class SoftwarePublicationTests(unittest.TestCase):
    def test_incident_and_technical_reports_are_allowed(self):
        for body in ALLOWED:
            with self.subTest(body=body[:100]):
                self.assertTrue(policy.check_publication(body)["allowed"])

    def test_other_rules_still_reject_with_report_context(self):
        for body in REJECTED:
            with self.subTest(body=body[:100]):
                self.assertFalse(policy.check_publication(body)["allowed"])

    def test_native_hook_replays_original_tool_event(self):
        hook = ROOT / "integrations/commons_publication_hooks/hook.py"
        for body, allowed in [(INCIDENT, True), (REJECTED[0], False), (REJECTED[4], False)]:
            event = dict(EVENT, tool_input=dict(EVENT["tool_input"], message=body))
            run = subprocess.run([sys.executable, str(hook)], input=json.dumps(event),
                                 capture_output=True, text=True, check=True)
            result = json.loads(run.stdout)
            if allowed:
                self.assertEqual(result, {})
            else:
                self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertFalse(result["continue"])
                self.assertNotIn(body, run.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node is required for companion parity")
    def test_javascript_companions_preserve_decisions(self):
        paths = ["commons-publication-policy.js", "commons-publication-policy.cjs"]
        script = "const p=require(process.argv[1]);let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(JSON.parse(s).map(b=>p.checkPublication(b).allowed))));"
        expected = [True] * len(ALLOWED) + [False] * len(REJECTED)
        for path in paths:
            with self.subTest(path=path):
                run = subprocess.run(["node", "-e", script, str(ROOT / path)],
                                     input=json.dumps(ALLOWED + REJECTED), capture_output=True,
                                     text=True, check=True)
                self.assertEqual(json.loads(run.stdout), expected)


if __name__ == "__main__":
    unittest.main()
