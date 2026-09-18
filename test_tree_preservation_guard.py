"""Offline metadata, transport, CLI, workflow, and real-Git regression tests."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import tree_preservation_guard as guard

BASE, HEAD, BT, HT, BLOB = (char * 40 for char in "abcde")


def entry(path, kind="blob", mode=None, sha=BLOB):
    return {"path": path, "mode": mode or {"tree": "040000", "blob": "100644",
                                          "commit": "160000"}[kind],
            "type": kind, "sha": sha}


def tree(sha, entries):
    return {"sha": sha, "truncated": False, "tree": entries}


def event():
    return {"repository": {"full_name": "owner/repo"},
            "pull_request": {"number": 19, "base": {"sha": BASE},
                             "head": {"sha": HEAD}}}


class FakeAPI:
    def __init__(self, before, after):
        self.calls = []
        prefix = "/repos/owner/repo/git"
        self.responses = {
            f"{prefix}/commits/{BASE}": {"sha": BASE, "tree": {"sha": BT}},
            f"{prefix}/commits/{HEAD}": {"sha": HEAD, "tree": {"sha": HT}},
            f"{prefix}/trees/{BT}": tree(BT, before),
            f"{prefix}/trees/{HT}": tree(HT, after),
        }

    def __call__(self, path):
        self.calls.append(path)
        return copy.deepcopy(self.responses[path])


class RootTests(unittest.TestCase):
    def compare(self, before, after):
        return guard.compare_roots(tree(BT, before), tree(HT, after), BT, HT)

    def test_incident_4312_roots_to_one(self):
        before = [entry(f"p{i:04}") for i in range(4312)]
        result = self.compare(before, [before[0]])
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["removed_count"], 4311)
        self.assertEqual(result["reasons"], ["CATASTROPHIC_ROOT_LOSS"])
        self.assertEqual(len(result["removed_sample"]), 25)

    def test_focused_additions_and_blob_subtree_changes_pass(self):
        before = [entry("readme"), entry("src", "tree")]
        after = [entry("readme", sha="f" * 40), entry("src", "tree", sha="0" * 40), entry("new")]
        result = self.compare(before, after)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["added_count"], 1)
        self.assertFalse(result["merge_authorized"])
        self.assertFalse(result["branch_protection_modified"])

    def test_exact_thresholds_and_minimum_population(self):
        for count, removed, expected in [(99, 99, "PASS"), (100, 25, "PASS"),
                (100, 26, "FAIL"), (260, 26, "PASS"), (260, 27, "FAIL"),
                (1000, 100, "PASS"), (1000, 101, "FAIL")]:
            with self.subTest(count=count, removed=removed):
                before = [entry(f"p{i:04}") for i in range(count)]
                self.assertEqual(self.compare(before, before[removed:])["status"], expected)

    def test_tree_replaced_by_file_symlink_or_submodule_fails(self):
        for kind, mode in [("blob", "100644"), ("blob", "100755"),
                           ("blob", "120000"), ("commit", "160000")]:
            with self.subTest(mode=mode):
                result = self.compare([entry("src", "tree")], [entry("src", kind, mode)])
                self.assertEqual(result["reasons"], ["ROOT_DIRECTORY_REPLACED"])
                self.assertEqual(result["directory_replacement_sample"], ["src"])

    def test_file_to_tree_and_normal_mode_change_pass(self):
        self.assertEqual(self.compare([entry("src")], [entry("src", "tree")])["status"], "PASS")
        self.assertEqual(self.compare([entry("script")], [entry("script", mode="100755")])["status"], "PASS")

    def test_empty_complete_tree_is_not_missing_evidence(self):
        self.assertEqual(self.compare([], [entry("new")])["status"], "PASS")
        self.assertEqual(self.compare([], [])["status"], "PASS")

    def test_combined_failures_have_stable_reason_order(self):
        before = [entry("src", "tree")] + [entry(f"p{i:04}") for i in range(100)]
        result = self.compare(before, [entry("src")])
        self.assertEqual(result["reasons"], ["CATASTROPHIC_ROOT_LOSS", "ROOT_DIRECTORY_REPLACED"])

    def test_input_order_independent(self):
        before = [entry(f"p{i:04}") for i in range(300)]
        after = before[100:] + [entry("new")]
        self.assertEqual(self.compare(before, after), self.compare(before[::-1], after[::-1]))

    def test_literal_unusual_git_names_are_preserved(self):
        names = ["tabs\there", "new\nline", "space name", "back\\slash", "\u96ea", "::warning::"]
        result = self.compare([], [entry(n) for n in names])
        self.assertEqual(result["added_sample"], sorted(names))
        # One-line JSON diagnostics cannot turn a filename into a workflow command.
        self.assertNotIn("\n", json.dumps(result))

    def test_truncated_missing_or_nonboolean_completeness_rejected(self):
        for value in [True, 0, 1, None, "false"]:
            payload = tree(BT, [])
            payload["truncated"] = value
            with self.subTest(value=value), self.assertRaises(guard.EvidenceError):
                guard.root_entries(payload, BT)
        payload.pop("truncated")
        with self.assertRaises(guard.EvidenceError):
            guard.root_entries(payload, BT)

    def test_duplicate_recursive_and_invalid_root_paths_rejected(self):
        bad_lists = [[entry("same"), entry("same")]]
        bad_lists += [[entry(path)] for path in ["", ".", "..", "a/b", "nul\x00", "\ud800", None, 7]]
        for entries in bad_lists:
            with self.subTest(entries=entries), self.assertRaises(guard.EvidenceError):
                guard.root_entries(tree(BT, entries), BT)

    def test_invalid_entry_shape_mode_type_and_sha_rejected(self):
        for row in [None, [], {}, entry("a", mode="040000"),
                    entry("a", mode=100644), entry("a", sha="main"),
                    entry("a", sha="A" * 40), entry("a", kind="blob", mode="160000")]:
            with self.subTest(row=row), self.assertRaises(guard.EvidenceError):
                guard.root_entries(tree(BT, [row]), BT)

    def test_incomplete_mismatched_or_oversized_tree_shape_rejected(self):
        for payload in [[], None, {}, tree(HT, []), {"sha": BT, "truncated": False, "tree": {} }]:
            with self.subTest(payload=payload), self.assertRaises(guard.EvidenceError):
                guard.root_entries(payload, BT)
        with patch.object(guard, "MAX_ROOTS", 1), self.assertRaises(guard.EvidenceError):
            guard.root_entries(tree(BT, [entry("a"), entry("b")]), BT)

    def test_four_immutable_metadata_gets_only(self):
        api = FakeAPI([entry("a")], [entry("a"), entry("b")])
        result = guard.evaluate(event(), api, "owner/repo")
        self.assertEqual(api.calls, [f"/repos/owner/repo/git/commits/{BASE}",
            f"/repos/owner/repo/git/commits/{HEAD}", f"/repos/owner/repo/git/trees/{BT}",
            f"/repos/owner/repo/git/trees/{HT}"])
        self.assertEqual(result["base_commit_sha"], BASE)
        self.assertEqual(result["head_commit_sha"], HEAD)
        self.assertEqual(result["pull_request"], 19)
        self.assertEqual(result["status"], "PASS")

    def test_event_rejected_before_network(self):
        cases = [None, {}, {"repository": {"full_name": "owner/repo"}}]
        for repo in ["../repo", "owner/..", "owner/repo/extra", "https://other/x", "owner/repo?x", None]:
            row = event(); row["repository"]["full_name"] = repo; cases.append(row)
        for number in [True, 0, -1, 1.5, "19", 2**53]:
            row = event(); row["pull_request"]["number"] = number; cases.append(row)
        row = event(); row["pull_request"]["head"]["sha"] = "main"; cases.append(row)
        for row in cases:
            api = FakeAPI([], [])
            with self.subTest(row=row), self.assertRaises(guard.EvidenceError):
                guard.evaluate(row, api)
            self.assertEqual(api.calls, [])

    def test_workflow_repository_mismatch_rejected(self):
        api = FakeAPI([], [])
        with self.assertRaises(guard.EvidenceError):
            guard.evaluate(event(), api, "other/repo")
        self.assertEqual(api.calls, [])

    def test_commit_identity_and_missing_tree_rejected(self):
        for payload in [None, {}, {"sha": HEAD, "tree": {"sha": BT}},
                        {"sha": BASE, "tree": {}}, {"sha": BASE, "tree": {"sha": "main"}}]:
            with self.subTest(payload=payload), self.assertRaises(guard.EvidenceError):
                guard.commit_tree(payload, BASE)

    def test_duplicate_key_invalid_utf8_nonfinite_and_bounds(self):
        for raw in [b'{"sha":1,"sha":2}', b'{"x":NaN}', b'{"x":Infinity}', b'\xff', b'{']:
            with self.subTest(raw=raw), self.assertRaises(guard.EvidenceError):
                guard.decode_json(raw)
        with patch.object(guard, "MAX_BYTES", 2), self.assertRaises(guard.EvidenceError):
            guard.decode_json(b'{} ')


class TransportCLITests(unittest.TestCase):
    def test_transport_is_get_only_bounded_and_fixed_origin(self):
        seen = []
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return None
            def read(self, size):
                seen.append(size)
                return b'{"ok":true}'
        class Opener:
            def open(self, request, timeout):
                seen.extend([request, timeout]); return Response()
        reader = guard.MetadataReader("sentinel-secret")
        reader._opener = Opener()
        self.assertEqual(reader(f"/repos/owner/repo/git/trees/{BT}"), {"ok": True})
        request, timeout, size = seen
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url, f"https://api.github.com/repos/owner/repo/git/trees/{BT}")
        self.assertEqual(timeout, 30)
        self.assertEqual(size, guard.MAX_BYTES + 1)
        self.assertIsNone(request.data)

    def test_unsupported_or_recursive_paths_never_open(self):
        reader = guard.MetadataReader()
        with patch.object(reader._opener, "open") as opened:
            for path in ["https://evil.invalid/", "/repos/owner/repo/contents/x",
                         f"/repos/owner/repo/git/trees/{BT}?recursive=false",
                         "/repos/owner/repo/git/trees/main"]:
                with self.subTest(path=path), self.assertRaises(guard.EvidenceError):
                    reader(path)
            opened.assert_not_called()

    def test_redirect_refused(self):
        with self.assertRaises(guard.EvidenceError):
            guard._NoRedirect().redirect_request(None, None, 302, "found", {}, "https://other.invalid")

    def test_http_and_network_failures_do_not_retry_or_echo_secrets(self):
        errors = [urllib.error.HTTPError("https://api.github.com", 429, "sentinel-secret", {}, None),
                  urllib.error.URLError("sentinel-secret")]
        for exc in errors:
            reader = guard.MetadataReader("sentinel-secret")
            with patch.object(reader._opener, "open", side_effect=exc) as opened:
                with self.assertRaises(guard.EvidenceError) as caught:
                    reader(f"/repos/owner/repo/git/trees/{BT}")
                self.assertEqual(opened.call_count, 1)
                self.assertNotIn("sentinel-secret", str(caught.exception))

    def run_main(self, payload, api):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "event.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            output = io.StringIO()
            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo"}), \
                    patch.object(guard, "MetadataReader", return_value=api), \
                    contextlib.redirect_stdout(output):
                code = guard.main(["--event", str(path)])
            return code, json.loads(output.getvalue())

    def test_cli_pass_fail_and_evidence_error_exit_codes(self):
        code, report = self.run_main(event(), FakeAPI([], [entry("new")]))
        self.assertEqual((code, report["status"]), (0, "PASS"))
        code, report = self.run_main(event(), FakeAPI([entry("src", "tree")], [entry("src")]))
        self.assertEqual((code, report["status"]), (1, "FAIL"))
        code, report = self.run_main({}, FakeAPI([], []))
        self.assertEqual((code, report["status"]), (2, "ERROR"))
        self.assertFalse(report["merge_authorized"])

    def test_cli_provider_failure_is_non_green(self):
        def unavailable(_): raise guard.EvidenceError("provider: HTTP 429")
        code, report = self.run_main(event(), unavailable)
        self.assertEqual((code, report["status"]), (2, "ERROR"))

    def test_cli_missing_event_is_structured_error(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as output:
            code = guard.main(["--event", str(Path(temp) / "absent")])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["detail"], "event: read failed")

    def test_existing_trusted_workflow_contains_guard_without_head_execution(self):
        text = (Path(__file__).parent / ".github/workflows/pr-collision-notice.yml").read_text()
        self.assertIn("pull_request_target:", text)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", text)
        self.assertIn("            tree_preservation_guard.py\n", text)
        self.assertNotIn("ref: ${{ github.event.pull_request.head", text)
        step = text.split("- name: verify exact PR root-tree retention", 1)[1]
        self.assertIn("if: ${{ !cancelled() }}", step)
        self.assertIn("run: python3 listener/tree_preservation_guard.py", step)
        self.assertNotIn("continue-on-error", step)
        self.assertIn("run: python3 listener/pr_collision_notice.py --repo-root target", text)
        self.assertEqual(text.count("runs-on:"), 1)


class RealGitTests(unittest.TestCase):
    def test_real_git_sparse_root_incident_and_focused_successor(self):
        with tempfile.TemporaryDirectory() as temp:
            def git(*args, data=None):
                return subprocess.check_output(["git", "-C", temp, *args], input=data,
                                               stderr=subprocess.PIPE)
            git("init", "-q")
            blob = git("hash-object", "-w", "--stdin", data=b"retained\n").decode().strip()
            names = [f"root-{i:04}" for i in range(4312)]
            def make_tree(paths):
                raw = b"".join(f"100644 blob {blob}\t{name}\0".encode() for name in paths)
                return git("mktree", "-z", data=raw).decode().strip()
            before, sparse, additive = make_tree(names), make_tree(names[:1]), make_tree(names + ["unique-new"])
            def metadata(sha):
                records = []
                for raw in git("ls-tree", "-z", sha).split(b"\0"):
                    if not raw: continue
                    header, path = raw.split(b"\t", 1)
                    mode, kind, object_sha = header.decode().split()
                    records.append(entry(path.decode(), kind, mode, object_sha))
                return tree(sha, records)
            failed = guard.compare_roots(metadata(before), metadata(sparse), before, sparse)
            passed = guard.compare_roots(metadata(before), metadata(additive), before, additive)
            self.assertEqual((failed["status"], failed["removed_count"]), ("FAIL", 4311))
            self.assertEqual((passed["status"], passed["added_count"]), ("PASS", 1))
            self.assertEqual(passed["removed_count"], 0)


if __name__ == "__main__":
    unittest.main()
