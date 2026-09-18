"""Base-aware JSON composition and real-worktree preservation regressions."""
from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from host import cloud_current_worktree as cc


def encoded(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")


class JsonCompositionTests(unittest.TestCase):
    def assert_composes(self, base, ours, theirs, expected):
        original = copy.deepcopy((base, ours, theirs))
        result = cc.classify_three_way(encoded(base), encoded(ours), encoded(theirs))
        self.assertNotEqual(result["verdict"], "CONFLICT", result)
        self.assertEqual(json.loads(result["merged"]), expected)
        self.assertEqual((base, ours, theirs), original)

    def assert_conflicts(self, base, ours, theirs):
        body = encoded(ours)
        result = cc.classify_three_way(encoded(base), body, encoded(theirs))
        self.assertEqual(result["verdict"], "CONFLICT", result)
        self.assertEqual(result["merged"], body)

    def test_local_scalar_edit_and_remote_addition(self):
        self.assert_composes({"x": "old"}, {"x": "local"},
                             {"x": "old", "remote": 1}, {"x": "local", "remote": 1})

    def test_remote_scalar_edit_and_local_addition(self):
        self.assert_composes({"x": "old"}, {"x": "old", "local": 1},
                             {"x": "remote"}, {"x": "remote", "local": 1})

    def test_disjoint_nested_edits(self):
        self.assert_composes({"n": {"a": 1, "b": 2}}, {"n": {"a": 3, "b": 2}},
                             {"n": {"a": 1, "b": 4}}, {"n": {"a": 3, "b": 4}})

    def test_local_key_deletion_is_not_resurrected(self):
        self.assert_composes({"obsolete": 1, "keep": 2}, {"keep": 2},
                             {"obsolete": 1, "keep": 2, "remote": 3}, {"keep": 2, "remote": 3})

    def test_remote_key_deletion_and_local_addition(self):
        self.assert_composes({"obsolete": 1, "keep": 2},
                             {"obsolete": 1, "keep": 2, "local": 3}, {"keep": 2},
                             {"keep": 2, "local": 3})

    def test_both_delete_key_and_add_disjoint_keys(self):
        self.assert_composes({"obsolete": 1}, {"local": 2}, {"remote": 3},
                             {"local": 2, "remote": 3})

    def test_nested_deletion_and_null_value(self):
        self.assert_composes({"n": {"remove": None, "keep": 1}}, {"n": {"keep": 1}},
                             {"n": {"remove": None, "keep": 1, "add": None}},
                             {"n": {"keep": 1, "add": None}})

    def test_missing_is_not_a_null_baseline(self):
        self.assert_conflicts({}, {"new": None}, {"new": "remote"})
        self.assert_conflicts({}, {"new": "local"}, {"new": None})

    def test_same_key_edit_conflicts(self):
        self.assert_conflicts({"x": "old"}, {"x": "local"}, {"x": "remote"})

    def test_delete_vs_edit_conflicts_in_both_directions(self):
        self.assert_conflicts({"x": 1}, {}, {"x": 2})
        self.assert_conflicts({"x": 1}, {"x": 2}, {})

    def test_subtree_delete_vs_nested_edit_conflicts(self):
        self.assert_conflicts({"n": {"x": 1}}, {}, {"n": {"x": 2}})
        self.assert_conflicts({"n": {"x": 1}}, {"n": {"x": 2}}, {})

    def test_one_sided_type_replacement(self):
        self.assert_composes({"x": {"a": 1}}, {"x": "replacement"},
                             {"x": {"a": 1}, "remote": 2}, {"x": "replacement", "remote": 2})

    def test_one_sided_array_replacement(self):
        self.assert_composes({"x": [1, 2]}, {"x": [9]},
                             {"x": [1, 2], "remote": 3}, {"x": [9], "remote": 3})

    def test_append_only_arrays_still_compose(self):
        self.assert_composes({"x": [1]}, {"x": [1, 2]}, {"x": [1, 3]}, {"x": [1, 2, 3]})

    def test_concurrent_array_replacements_still_conflict(self):
        self.assert_conflicts({"x": [1]}, {"x": [2]}, {"x": [3]})

    def test_concurrent_nested_additions_compose(self):
        self.assert_composes({}, {"n": {"a": 1}}, {"n": {"b": 2}}, {"n": {"a": 1, "b": 2}})

    def test_origin_file_deletion_behavior_is_unchanged(self):
        ours = encoded({"x": "local"})
        result = cc.classify_three_way(encoded({"x": "old"}), ours, None)
        self.assertEqual(result["verdict"], "CONFLICT")
        self.assertEqual(result["merged"], ours)

    def test_scalar_key_three_way_truth_table(self):
        absent = object()
        values = (absent, None, 0, 1, "a", "b")
        for base_value, local_value, remote_value in itertools.product(values, repeat=3):
            def obj(value):
                return {} if value is absent else {"x": value}
            base = obj(base_value)
            ours = {**obj(local_value), "local_marker": 1}
            theirs = {**obj(remote_value), "remote_marker": 2}
            with self.subTest(base=base, ours=ours, theirs=theirs):
                if local_value == remote_value:
                    chosen = local_value
                elif local_value == base_value:
                    chosen = remote_value
                elif remote_value == base_value:
                    chosen = local_value
                else:
                    self.assert_conflicts(base, ours, theirs)
                    continue
                self.assert_composes(base, ours, theirs,
                                     {**obj(chosen), "local_marker": 1, "remote_marker": 2})


@unittest.skipUnless(shutil.which("git"), "git is required")
class JsonRefreshTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cc-json-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.origin = cc._init_fixture_repo(str(root / "origin"))
        self.base = {"remove": None, "setting": "base", "nested": {"keep": 0}}
        cc.write_file_bytes(self.origin, "data.json", encoded(self.base))
        cc.git(["add", "data.json"], cwd=self.origin)
        cc.git(["commit", "-m", "JSON baseline"], cwd=self.origin)
        self.work = cc.open_worktree(peer="json-test", dest=str(root / "work"),
                                     repo=self.origin)["worktree"]

    def advance_origin(self, value):
        cc.write_file_bytes(self.origin, "data.json", encoded(value))
        cc.git(["add", "data.json"], cwd=self.origin)
        cc.git(["commit", "-m", "remote JSON edit"], cwd=self.origin)

    def test_refresh_composes_disjoint_json_and_preserves_snapshot(self):
        ours = {"setting": "local", "nested": {"keep": 0}, "local": True}
        cc.write_file_bytes(self.work, "data.json", encoded(ours))
        cc.write_file_bytes(self.work, "untracked.txt", b"keep these bytes\n")
        self.advance_origin({**self.base, "nested": {"keep": 0, "remote": 1}, "remote": True})
        result = cc.refresh(self.work, peer="json-test")
        self.assertEqual(result["readiness"], "READY", result)
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(json.loads(cc.read_file_bytes(self.work, "data.json")),
                         {"setting": "local", "nested": {"keep": 0, "remote": 1},
                          "local": True, "remote": True})
        self.assertEqual(cc.read_file_bytes(self.work, "untracked.txt"), b"keep these bytes\n")
        snapshot = Path(self.work) / cc.RECEIPTS_DIR / result["snapshot_id"] / "files" / "data.json"
        self.assertEqual(snapshot.read_bytes(), encoded(ours))
        self.assertEqual(cc.head_sha(self.work), cc.head_sha(self.origin))
        self.assertFalse(cc.journal_has_forbidden(self.work))

    def test_refresh_conflict_keeps_local_and_all_three_artifacts(self):
        ours = {**self.base, "setting": "local"}
        theirs = {**self.base, "setting": "remote"}
        cc.write_file_bytes(self.work, "data.json", encoded(ours))
        self.advance_origin(theirs)
        result = cc.refresh(self.work, peer="json-test")
        self.assertEqual(result["readiness"], "READY_WITH_CONFLICTS")
        self.assertEqual(cc.read_file_bytes(self.work, "data.json"), encoded(ours))
        folder = Path(self.work) / cc.RECEIPTS_DIR / result["id"] / "conflicts" / "data.json"
        for name, value in (("base", self.base), ("ours", ours), ("theirs", theirs)):
            self.assertEqual((folder / name).read_bytes(), encoded(value))
        self.assertFalse(result["deleted_user_work"])


if __name__ == "__main__":
    unittest.main()
