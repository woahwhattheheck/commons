import copy
import unittest

import tree_preservation_guard as g


def sha(ch):
    return ch * 40


def entry(path, kind="tree", *, mode=None, object_sha=None):
    if mode is None:
        mode = "040000" if kind == "tree" else "100644"
    return {
        "path": path,
        "mode": mode,
        "type": kind,
        "sha": object_sha or sha("a"),
    }


def tree_payload(tree_sha, entries, *, truncated=False):
    return {"sha": tree_sha, "truncated": truncated, "tree": entries}


class RootTreePreservationTests(unittest.TestCase):
    def test_exact_incident_shape_fails(self):
        base = {f"p{i:04d}": g.RootEntry(f"p{i:04d}", "040000", "tree", sha("a")) for i in range(4312)}
        head = {"survivor": g.RootEntry("survivor", "100644", "blob", sha("b"))}
        result = g.evaluate(base, head)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("mass_root_deletion", result["reasons"])
        self.assertEqual(result["removed_root_count"], 4312)

    def test_small_deletion_and_addition_pass(self):
        base = {f"p{i:03d}": g.RootEntry(f"p{i:03d}", "040000", "tree", sha("a")) for i in range(200)}
        head = dict(base)
        for i in range(20):
            head.pop(f"p{i:03d}")
        head["new"] = g.RootEntry("new", "100644", "blob", sha("b"))
        self.assertEqual(g.evaluate(base, head)["status"], "PASS")

    def test_threshold_requires_strict_absolute_and_fraction_excess(self):
        base = {f"p{i:03d}": g.RootEntry(f"p{i:03d}", "040000", "tree", sha("a")) for i in range(250)}
        head = {k: v for i, (k, v) in enumerate(base.items()) if i >= 25}
        self.assertEqual(g.evaluate(base, head)["status"], "PASS")  # exactly 25, exactly 10%
        head = {k: v for i, (k, v) in enumerate(base.items()) if i >= 26}
        self.assertEqual(g.evaluate(base, head)["status"], "FAIL")

    def test_tree_to_blob_fails_but_blob_to_tree_passes(self):
        base = {
            "dir": g.RootEntry("dir", "040000", "tree", sha("a")),
            "file": g.RootEntry("file", "100644", "blob", sha("b")),
        }
        bad = dict(base)
        bad["dir"] = g.RootEntry("dir", "100644", "blob", sha("c"))
        self.assertEqual(g.evaluate(base, bad)["status"], "FAIL")
        good = dict(base)
        good["file"] = g.RootEntry("file", "040000", "tree", sha("c"))
        self.assertEqual(g.evaluate(base, good)["status"], "PASS")

    def test_truncated_and_duplicate_tree_payloads_fail_closed(self):
        with self.assertRaisesRegex(g.GuardError, "truncated"):
            g._parse_root_tree(tree_payload(sha("b"), [], truncated=True), sha("b"), "root")
        dup = [entry("x"), entry("x", object_sha=sha("b"))]
        with self.assertRaisesRegex(g.GuardError, "duplicate"):
            g._parse_root_tree(tree_payload(sha("c"), dup), sha("c"), "root")

    def test_malformed_tree_payload_fails_closed(self):
        malformed = tree_payload(sha("b"), [entry("nested/path")])
        with self.assertRaises(g.GuardError):
            g._parse_root_tree(malformed, sha("b"), "root")
        wrong = tree_payload(sha("c"), [])
        with self.assertRaisesRegex(g.GuardError, "sha mismatch"):
            g._parse_root_tree(wrong, sha("b"), "root")

    def test_inspect_uses_exact_four_metadata_gets_and_exact_event_shas(self):
        base_sha, head_sha = sha("1"), sha("2")
        base_tree_sha, head_tree_sha = sha("3"), sha("4")
        calls = []
        payloads = {
            f"/repos/base/r/git/commits/{base_sha}": {"sha": base_sha, "tree": {"sha": base_tree_sha}},
            f"/repos/fork/r/git/commits/{head_sha}": {"sha": head_sha, "tree": {"sha": head_tree_sha}},
            f"/repos/base/r/git/trees/{base_tree_sha}": tree_payload(base_tree_sha, [entry("a")]),
            f"/repos/fork/r/git/trees/{head_tree_sha}": tree_payload(head_tree_sha, [entry("a"), entry("b", kind="blob")]),
        }
        def getter(path):
            calls.append(path)
            return copy.deepcopy(payloads[path])

        result = g.inspect("base/r", "fork/r", base_sha, head_sha, getter)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(calls, list(payloads))
        self.assertEqual(len(calls), 4)
        self.assertTrue(all("/contents/" not in path and "?recursive=" not in path for path in calls))
        parsed = g._parse_event(
            {
                "repository": {"full_name": "base/r"},
                "pull_request": {
                    "base": {"sha": base_sha, "repo": {"full_name": "base/r"}},
                    "head": {"sha": head_sha, "repo": {"full_name": "fork/r"}},
                },
            }
        )
        self.assertEqual(parsed, ("base/r", "fork/r", base_sha, head_sha))


if __name__ == "__main__":
    unittest.main()
