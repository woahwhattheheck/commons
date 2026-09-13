#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest

# The production module composes with host/coordination_state.py. These pure
# decision tests stub only that import so they remain fully offline.
stub = types.ModuleType("coordination_state")
class _GitHub: pass
class _GitHubError(RuntimeError): pass
stub.GitHub = _GitHub
stub.GitHubError = _GitHubError
stub.discover_token = lambda: ""
sys.modules.setdefault("coordination_state", stub)

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("swarm_preclaim_fence", HERE / "swarm_preclaim_fence.py")
fence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fence)


def report(*, stable=None, exact=None, paths=None, comparisons=None, kind="pull", errors=None):
    return {
        "input": {},
        "slack": {
            "stable_id_hits": stable or [],
            "exact_target_hits": exact or [],
            "path_semantic_hits": paths or [],
        },
        "owner": {"repo": "owner/repo", "default_branch": "main", "head_sha": "owner", "tree_sha": "tree"},
        "upstream": {"kind": kind, "repo": "upstream/repo", "number": 842, "head_sha": "donor", "changed_files": []},
        "blob_comparisons": comparisons or [],
        "errors": errors or [],
    }


class DecisionFixtures(unittest.TestCase):
    def test_red_a_exact_pr_hit_blocks_even_without_stable_id_hit(self):
        value = report(
            exact=[{"text": "TAKE SOURCE+MERGE · upstream/repo#842", "ts": "1"}],
            comparisons=[{"path": "x.py", "comparable": True, "match": False}],
        )
        out = fence.finalize(value)
        self.assertEqual(out["decision"], fence.OWNED)
        self.assertFalse(out["branch_write_allowed"])
        self.assertEqual(out["exit_code"], 20)

    def test_red_b_matching_owner_blob_is_already_absorbed(self):
        value = report(
            comparisons=[{
                "path": "x.py",
                "upstream_blob_oid": "abc",
                "owner_blob_oid": "abc",
                "upstream_status": "modified",
                "comparable": True,
                "match": True,
            }]
        )
        out = fence.finalize(value)
        self.assertEqual(out["decision"], fence.ALREADY_ABSORBED)
        self.assertFalse(out["branch_write_allowed"])
        self.assertEqual(out["exit_code"], 21)

    def test_red_c_different_owner_blob_needs_manual_diff(self):
        value = report(
            comparisons=[{
                "path": "x.py",
                "upstream_blob_oid": "abc",
                "owner_blob_oid": "def",
                "upstream_status": "modified",
                "comparable": True,
                "match": False,
            }]
        )
        out = fence.finalize(value)
        self.assertEqual(out["decision"], fence.NEEDS_MANUAL_DIFF)
        self.assertFalse(out["branch_write_allowed"])
        self.assertEqual(out["exit_code"], 22)

    def test_issue_without_custody_hit_is_safe_to_bind(self):
        out = fence.finalize(report(kind="issue"))
        self.assertEqual(out["decision"], fence.SAFE_TO_BIND_BRANCH)
        self.assertTrue(out["branch_write_allowed"])
        self.assertEqual(out["exit_code"], 0)

    def test_evidence_reader_error_fails_closed(self):
        out = fence.finalize(report(kind="issue", errors=["slack: rate_limited"]))
        self.assertEqual(out["decision"], fence.NEEDS_MANUAL_DIFF)
        self.assertFalse(out["branch_write_allowed"])

    def test_release_hit_is_not_ownership(self):
        out = fence.finalize(report(
            kind="issue",
            exact=[{"text": "YIELD/RELEASE upstream/repo#842 to queue"}],
        ))
        self.assertEqual(out["decision"], fence.SAFE_TO_BIND_BRANCH)

    def test_candidate_path_missing_from_pr_fails_closed(self):
        out = fence.finalize(report(comparisons=[{
            "path": "expected.py",
            "upstream_status": "not_in_pr",
            "upstream_blob_oid": None,
            "owner_blob_oid": None,
            "comparable": False,
            "match": False,
        }]))
        self.assertEqual(out["decision"], fence.NEEDS_MANUAL_DIFF)

    def test_offline_report_exit_code_is_machine_gate(self):
        payload = report(comparisons=[{
            "path": "x.py", "comparable": True, "match": True,
            "upstream_blob_oid": "abc", "owner_blob_oid": "abc",
            "upstream_status": "modified",
        }])
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "report.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(fence.main(["--offline-report", str(path), "--json"]), 21)


class CollectorTests(unittest.TestCase):
    def test_parse_target_accepts_urls_and_shorthand(self):
        self.assertEqual(
            fence.parse_target("https://github.com/up/repo/pull/842"),
            {"repo": "up/repo", "number": 842, "kind": "pull"},
        )
        self.assertEqual(
            fence.parse_target("up/repo#842"),
            {"repo": "up/repo", "number": 842, "kind": None},
        )

    def test_collect_github_compares_owner_tree_to_pr_blob_oids(self):
        class FakeGitHub:
            def rest(self, path, params=None):
                if path == "/repos/owner/repo":
                    return {"default_branch": "main"}
                if path == "/repos/owner/repo/branches/main":
                    return {"commit": {"sha": "owner-head", "commit": {"tree": {"sha": "owner-tree"}}}}
                if path == "/repos/owner/repo/git/trees/owner-tree":
                    return {"truncated": False, "tree": [
                        {"path": "same.py", "type": "blob", "sha": "abc"},
                        {"path": "different.py", "type": "blob", "sha": "owner-def"},
                    ]}
                if path == "/repos/up/repo/pulls/842":
                    return {"state": "open", "title": "x", "html_url": "u", "head": {"sha": "donor-head"}, "base": {"sha": "base"}}
                if path == "/repos/up/repo/pulls/842/files":
                    return [
                        {"filename": "same.py", "status": "modified", "sha": "abc"},
                        {"filename": "different.py", "status": "modified", "sha": "donor-def"},
                    ]
                raise AssertionError((path, params))

        owner, upstream, comparisons = fence.collect_github(
            FakeGitHub(), "owner/repo", {"repo": "up/repo", "number": 842, "kind": "pull"}, []
        )
        self.assertEqual(owner["head_sha"], "owner-head")
        self.assertEqual(upstream["head_sha"], "donor-head")
        self.assertEqual([c["match"] for c in comparisons], [True, False])
        self.assertEqual(fence.finalize(report(comparisons=comparisons))["decision"], fence.NEEDS_MANUAL_DIFF)


if __name__ == "__main__":
    unittest.main()
