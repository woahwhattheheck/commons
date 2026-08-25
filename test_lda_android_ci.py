#!/usr/bin/env python3
"""LDA Android leftover is a current-main Actions wire, not a Slack map."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from lda_android_ci import (
    STRANDED,
    WORKFLOW,
    classify,
    measure_root,
    parse_workflow,
)


class TestLdaAndroidCi(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not stillness", row["note"])

    def test_stranded_lda_copy_is_not_commons_ci(self):
        stranded = os.path.join(ROOT, STRANDED)
        self.assertTrue(os.path.isfile(stranded), "LDA copy must stay as evidence")
        with open(stranded, "r", encoding="utf-8") as handle:
            body = handle.read()
        measured = parse_workflow(body)
        self.assertTrue(measured["wipes_repo_artifacts"])
        self.assertFalse(measured["has_lda_workdir"])
        self.assertFalse(measured["has_path_filter"])
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")

    def test_blind_copy_stays_not_landed(self):
        body = (
            "on: [push, workflow_dispatch]\n"
            "listArtifactsForRepo\n"
            "deleteArtifact\n"
            "gradle :app:assembleDebug --build-cache\n"
            "setup-java\n"
        )
        measured = parse_workflow(body)
        self.assertEqual(classify(measured)["state"], "NOT_LANDED")
        self.assertIn("wipe", classify(measured)["note"])

    def test_wired_gate_is_integrated(self):
        body = (
            "name: lda-android\n"
            "workflow_dispatch:\n"
            "paths:\n"
            "  - lda/app/**\n"
            "working-directory: lda\n"
            "uses: actions/setup-java@v4\n"
            "gradle :app:assembleDebug --build-cache\n"
        )
        measured = parse_workflow(body)
        self.assertTrue(measured["has_lda_workdir"])
        self.assertTrue(measured["has_assemble"])
        self.assertTrue(measured["has_jdk"])
        self.assertTrue(measured["has_path_filter"])
        self.assertTrue(measured["has_workflow_dispatch"])
        self.assertFalse(measured["wipes_repo_artifacts"])
        self.assertEqual(measured["titan"], "NOT_WRITTEN")
        verdict = classify(measured)
        self.assertEqual(verdict["state"], "INTEGRATED")
        self.assertIn("workflow file is not a run URL", verdict["note"])

    def test_live_workflow_is_the_gate(self):
        measured = measure_root(ROOT)
        self.assertTrue(measured["measured"])
        self.assertTrue(measured["present"])
        self.assertEqual(measured["workflow"], WORKFLOW)
        self.assertEqual(measured["stranded"], STRANDED)
        self.assertTrue(measured["has_lda_workdir"])
        self.assertTrue(measured["has_assemble"])
        self.assertTrue(measured["has_jdk"])
        self.assertTrue(measured["has_path_filter"])
        self.assertTrue(measured["has_workflow_dispatch"])
        self.assertFalse(measured["wipes_repo_artifacts"])
        self.assertEqual(classify(measured)["state"], "INTEGRATED")
        workflow_path = os.path.join(ROOT, WORKFLOW)
        with open(workflow_path, "r", encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("working-directory: lda", text)
        self.assertIn("assembleDebug", text)
        self.assertIn("lda/app/**", text)
        self.assertIn("workflow_dispatch", text)
        self.assertNotIn("listArtifactsForRepo", text)
        self.assertNotIn("gha-remove-artifacts", text)


if __name__ == "__main__":
    unittest.main()
