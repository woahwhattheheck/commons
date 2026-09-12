#!/usr/bin/env python3
"""Close leftover living KEEP after tests battery 34398152660.

Delayed pull_request battery on already-merged PR #11581
(head 6fa71c1c607171ff39b975d655f375bfb9104cab, merge-ref
38f56323c1c60b2fe2cfafcfe35202287f248eb8) failed 170 files.
Later KEEP-lifts closed living KEEP dicts of reminted shared files.
Remaining graph: leftover KEEP still froze reminted leftover
test_pr7915_closed_unmerged.py 67240310 after live b0fa2ef2, and
chunk helper --write dropped the TYPE Larger-fixed cite already on
commons-slack-chunk.html c4a48395. Lift those living leftover pins
and emit the cite from the chunk helper. Do not remint leftover
receipts. Historical SOURCE_REV maps stay on their frozen trees.
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PR7915 = "b0fa2ef2"
STALE_PR7915 = "67240310"
CHUNK_HTML = "c4a48395"
STALE_CHUNK_HTML = "1304e4ec"
HELPER = "0fc25108"
STALE_HELPER = "95dd6557"
MERGE = "fab64d6a"
ORIGINALS = (
    "test_merge_on_pr.py",
    "test_pr7915_closed_unmerged.py",
    "test_grokbuild_pr8367_verify.py",
    "test_grok_build_tests_34387653822_keep_lift.py",
    "test_coil_harness_schema.py",
    "test_grokbuild_pr8414_verify.py",
)
RECEIPT = ROOT / "p/grokbuild-tests-battery-34398152660-keep-lift-20260910-01.md"
LARGER = (
    '<p class="note"><strong>Larger fixed engagements</strong> '
    "(separate product pages; checkout/intent stays there): "
    '<a href="./diagnostic.html">GGUF diagnostic · $12,000 / 10 days</a> · '
    '<a href="./commercial.html">White Box pilot · $30,000 / 30 days</a>. '
    "Not remints of tip SKUs.</p>"
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildTestsBattery34398152660KeepLift(unittest.TestCase):
    def test_live_pr7915_and_chunk_match_lifted_prefixes(self) -> None:
        pr7915 = git_blob("test_pr7915_closed_unmerged.py")
        html = git_blob("commons-slack-chunk.html")
        helper = git_blob("host/commons_slack_full_body_chunk.py")
        merge = git_blob("test_merge_on_pr.py")
        self.assertTrue(pr7915.startswith(PR7915), pr7915)
        self.assertFalse(pr7915.startswith(STALE_PR7915), pr7915)
        self.assertTrue(html.startswith(CHUNK_HTML), html)
        self.assertFalse(html.startswith(STALE_CHUNK_HTML), html)
        self.assertTrue(helper.startswith(HELPER), helper)
        self.assertFalse(helper.startswith(STALE_HELPER), helper)
        self.assertTrue(merge.startswith(MERGE), merge)

    def test_leftover_keep_carriers_no_longer_freeze_stale_pr7915(self) -> None:
        merge = (ROOT / "test_merge_on_pr.py").read_text(encoding="utf-8")
        readback = (ROOT / "test_cursor_merge_on_pr_readback.py").read_text(
            encoding="utf-8"
        )
        verify = (ROOT / "test_grokbuild_pr8367_verify.py").read_text(encoding="utf-8")
        for text in (merge, readback, verify):
            self.assertIn(f'"{PR7915}"', text)
            self.assertNotIn(f'"{STALE_PR7915}"', text)

    def test_chunk_helper_write_keeps_larger_fixed_cite(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "host"))
        import commons_slack_full_body_chunk as chunk

        rendered = chunk.render_html()
        on_disk = (ROOT / "commons-slack-chunk.html").read_text(encoding="utf-8")
        self.assertEqual(on_disk, rendered)
        self.assertIn(LARGER, rendered)
        self.assertIn('id="titanmcp-pad-pointer"', rendered)
        self.assertIn('id="live-cash"', rendered)
        self.assertNotIn("Authorization", rendered)
        helper = (ROOT / "host/commons_slack_full_body_chunk.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Larger fixed engagements", helper)

    def test_originally_failing_keep_graph_contracts_pass(self) -> None:
        for name in ORIGINALS:
            with self.subTest(name=name):
                proc = subprocess.run(
                    ["python3", name],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    msg=f"{name}\n{proc.stdout}\n{proc.stderr}",
                )

    def test_did_not_remint_leftover_receipts(self) -> None:
        leftover = ROOT / "p/cursor-merge-on-pr-20260902-01.md"
        self.assertTrue(leftover.is_file())
        self.assertTrue(
            git_blob("p/cursor-merge-on-pr-20260902-01.md").startswith("22b63e25")
        )
        self.assertTrue(
            git_blob("p/cursor-commons-slack-full-body-chunk-20260902-01.md").startswith(
                "94770f41"
            )
        )
        receipt = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("34398152660", receipt)
        self.assertIn(
            "woahwhattheheck/commons:tests:6fa71c1c607171ff39b975d655f375bfb9104cab:the whole battery, one failure fails the run",
            receipt,
        )
        self.assertNotIn(
            'type="password"',
            (ROOT / "host/commons_slack_full_body_chunk.py").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
