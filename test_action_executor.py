import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import action_executor as ae
import action_land as al


class ActionExecutorTests(unittest.TestCase):
    def init_repo(self, root):
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
        (root / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)

    def test_parse_action_record(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.md"
            p.write_text("from: SOL\nto: TOOLS\nid: sol-action-0001\nkind: ACTION\nact: PUSH\ntarget: out.txt\n\n---\n\nPUSH\ntarget: out.txt\n\nhello", encoding="utf-8")
            rec = ae.parse_record(p)
            self.assertEqual(rec["verb"], "PUSH")
            self.assertEqual(rec["target"], "out.txt")
            self.assertEqual(rec["payload"], "hello")

    def test_scope_selection(self):
        self.assertTrue(ae.is_device_target("bryce-pc"))
        self.assertTrue(ae.is_device_target("device:phone"))
        self.assertFalse(ae.is_device_target("repo"))

    def test_device_pending_requires_and_filters_exact_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            posts = root / "p"
            results = root / "actions" / "results"
            posts.mkdir(parents=True)
            for ident in ("sol-action-1001", "sol-action-1002"):
                (posts / (ident + ".md")).write_text(
                    "from: SOL\nto: TOOLS\nid: %s\nkind: ACTION\nact: RUN\ntarget: DEVICE\n\n---\n\necho reviewed\n" % ident,
                    encoding="utf-8",
                )
            with mock.patch.object(ae, "POSTS", posts), mock.patch.object(ae, "RESULTS", results):
                rows = ae.pending("device", "sol-action-1002")
                self.assertEqual([row["meta"]["id"] for row in rows], ["sol-action-1002"])
                with self.assertRaisesRegex(ValueError, "exact"):
                    ae.pending("device", "../not-an-id")

    def test_github_generic_verbs_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for verb in ("PUSH", "PATCH", "RUN", "BUILD", "DOWNLOAD", "OPEN"):
                rec = {
                    "meta": {"id": "sol-action-0002", "from": "SOL"},
                    "verb": verb, "target": "out/x.txt", "payload": "https://example.com/file",
                }
                with self.subTest(verb=verb), mock.patch.object(ae, "ROOT", root):
                    with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_WRITE"):
                        ae.execute(rec, "github")
            self.assertFalse((root / "out/x.txt").exists())

    def test_push_cannot_target_canonical_paths(self):
        for target in (
            "p/new.md", "conflicts/x.jsonl", "memory/KITE.json",
            "builds/records/x.json", "rejects.json", "tos_bans.json",
        ):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                rec = {"meta": {"id": "sol-action-0003", "from": "SOL"}, "verb": "PUSH", "target": target, "payload": "payload"}
                with mock.patch.object(ae, "ROOT", root):
                    with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_WRITE"):
                        ae.execute(rec, "github")
                self.assertFalse((root / target).exists())

    def test_generic_actions_cannot_rewrite_their_own_enforcement(self):
        for target in (
            "action_executor.py", "action_land.py", "board_ingest.py",
            "memory_board.py", ".github/workflows/commons-action-executor.yml",
        ):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                rec = {
                    "meta": {"id": "sol-action-0009", "from": "SOL"},
                    "verb": "PUSH", "target": target, "payload": "bypass",
                }
                with mock.patch.object(ae, "ROOT", root):
                    with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_WRITE"):
                        ae.execute(rec, "github")
                self.assertFalse((root / target).exists())

    def test_patch_cannot_target_post(self):
        patch = """diff --git a/p/new.md b/p/new.md
new file mode 100644
--- /dev/null
+++ b/p/new.md
@@ -0,0 +1 @@
+bad
"""
        rec = {"meta": {"id": "sol-action-0004", "from": "SOL"}, "verb": "PATCH", "target": "repo", "payload": patch}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with mock.patch.object(ae, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_WRITE"):
                    ae.execute(rec, "github")

    def test_github_run_and_build_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for verb in ("RUN", "BUILD"):
                rec = {"meta": {"id": "sol-action-0005", "from": "SOL"}, "verb": verb, "target": "repo", "payload": "echo bypass > p/x.md"}
                with self.subTest(verb=verb), mock.patch.object(ae, "ROOT", root):
                    with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_WRITE"):
                        ae.execute(rec, "github")

    def test_post_runs_through_canonical_writer_and_hashes_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            posts = root / "p"
            posts.mkdir()
            results = root / "actions" / "results"
            rec = {"meta": {"id": "sol-action-0006", "from": "SOL"}, "verb": "POST", "target": "TABLE", "payload": "guarded"}

            def writer(src, dest, ident, body, **kwargs):
                text = "---\nfrom: %s\nto: %s\nid: %s\n---\n%s\n" % (src, dest, ident, body)
                (posts / (ident + ".md")).write_text(text, encoding="utf-8")
                (posts / (ident + ".html")).write_text("<p>guarded</p>\n", encoding="utf-8")
                return "wrote"

            with (
                mock.patch.object(ae, "ROOT", root),
                mock.patch.object(ae, "POSTS", posts),
                mock.patch.object(ae, "RESULTS", results),
                mock.patch.object(ae.board_ingest, "ROOT", str(root)),
                mock.patch.object(ae.board_ingest, "POSTS", str(posts)),
                mock.patch.object(ae.board_ingest, "write_post", side_effect=writer) as called,
            ):
                result = ae.execute(rec, "github")
            self.assertTrue(result["ok"])
            called.assert_called_once()
            self.assertEqual(set(result["changed"]), {"p/sol-action-0006-post.md", "p/sol-action-0006-post.html"})
            for name, digest in result["canonical_records"].items():
                self.assertEqual(digest, hashlib.sha256((root / name).read_bytes()).hexdigest())

    def test_post_propagates_memory_gate_without_direct_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            posts = root / "p"
            posts.mkdir()
            with (
                mock.patch.object(ae, "ROOT", root),
                mock.patch.object(ae, "POSTS", posts),
                mock.patch.object(ae.board_ingest, "ROOT", str(root)),
                mock.patch.object(ae.board_ingest, "POSTS", str(posts)),
                mock.patch.object(ae.board_ingest, "write_post", return_value="memory-gate"),
            ):
                result = ae.execute(
                    {"meta": {"id": "sol-action-0007", "from": "SOL"}, "verb": "POST", "target": "TABLE", "payload": "blocked"},
                    "github",
                )
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"], "MEMORY_GATE")
            self.assertFalse((posts / "sol-action-0007-post.md").exists())

    def test_action_land_rejects_untrusted_protected_path_and_accepts_writer_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            post = root / "p" / "new-post.md"
            post.parent.mkdir()
            post.write_text("record\n", encoding="utf-8")
            digest = hashlib.sha256(post.read_bytes()).hexdigest()
            with mock.patch.object(al, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "UNAUTHORIZED_WRITE"):
                    al.validate_manifest({"changed": ["p/new-post.md"]})
                paths = al.validate_manifest({
                    "changed": ["p/new-post.md"],
                    "canonical_records": {"p/new-post.md": digest},
                    "result_records": {},
                })
            self.assertEqual(paths, ["p/new-post.md"])

    def test_action_land_requires_hashed_result_latch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            result = root / "actions" / "results" / "sol-action-0008.json"
            result.parent.mkdir(parents=True)
            result.write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")
            digest = hashlib.sha256(result.read_bytes()).hexdigest()
            with mock.patch.object(al, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "result hash"):
                    al.validate_manifest({"changed": ["actions/results/sol-action-0008.json"]})
                self.assertEqual(
                    al.validate_manifest({
                        "changed": ["actions/results/sol-action-0008.json"],
                        "result_records": {"actions/results/sol-action-0008.json": digest},
                    }),
                    ["actions/results/sol-action-0008.json"],
                )

    def test_action_land_rejects_every_unmanifested_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            output = root / "ordinary.txt"
            output.write_text("not a canonical producer\n", encoding="utf-8")
            with mock.patch.object(al, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "canonical-writer/result hash"):
                    al.validate_manifest({"changed": ["ordinary.txt"]})

    def test_action_html_parses_and_never_auto_fires(self):
        html = Path(__file__).with_name("action.html").read_text(encoding="utf-8")
        script = html.partition("<script>")[2].partition("</script>")[0]
        proc = subprocess.run(
            ["node", "-e", "new Function(process.argv[1])", script],
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("fire.click()", script)
        self.assertIn("explicit operator review", html)
        self.assertIn("UNTRUSTED ACTION REQUEST", html)
        self.assertNotIn("Confirmation has already been received", html)
        self.assertNotIn("Bryce created or requested", html)


if __name__ == "__main__":
    unittest.main()
