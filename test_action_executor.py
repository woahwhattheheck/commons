import hashlib
import io
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

    def test_github_push_creates_or_replaces_and_is_exactly_manifested(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            rec = {
                "meta": {"id": "sol-action-0002", "from": "SOL"},
                "verb": "PUSH", "target": "out/x.txt", "payload": "complete file\n",
            }
            with mock.patch.object(ae, "ROOT", root):
                result = ae.execute(rec, "github")
                self.assertTrue(result["ok"])
                self.assertEqual(result["changed"], ["out/x.txt"])
                self.assertEqual(
                    result["action_outputs"]["out/x.txt"],
                    hashlib.sha256((root / "out/x.txt").read_bytes()).hexdigest(),
                )
                rec["payload"] = "replacement\n"
                result = ae.execute(rec, "github")
                self.assertTrue(result["ok"])
                self.assertEqual((root / "out/x.txt").read_text(encoding="utf-8"), "replacement\n")

    def test_github_patch_is_an_open_hashed_write_verb(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            patch = """diff --git a/open.txt b/open.txt
new file mode 100644
--- /dev/null
+++ b/open.txt
@@ -0,0 +1 @@
+open door
"""
            rec = {"meta": {"id": "sol-action-0012", "from": "SOL"},
                   "verb": "PATCH", "target": "repo", "payload": patch}
            with mock.patch.object(ae, "ROOT", root):
                result = ae.execute(rec, "github")
            self.assertTrue(result["ok"])
            self.assertIn("open.txt", result["action_outputs"])

    def test_github_download_and_open_have_public_network_egress(self):
        class Response(io.BytesIO):
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                self.close()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            download = {"meta": {"id": "sol-action-0015", "from": "SOL"},
                        "verb": "DOWNLOAD", "target": "downloads/data.bin",
                        "payload": "https://public.example/data"}
            opened = {"meta": {"id": "sol-action-0016", "from": "SOL"},
                      "verb": "OPEN", "target": "repo",
                      "payload": "https://public.example/status"}
            with mock.patch.object(ae, "ROOT", root), mock.patch.object(
                ae.urllib.request, "urlopen", side_effect=[Response(b"bytes"), Response(b"")]
            ) as fetch:
                result = ae.execute(download, "github")
                status = ae.execute(opened, "github")
            self.assertTrue(result["ok"])
            self.assertEqual((root / "downloads/data.bin").read_bytes(), b"bytes")
            self.assertEqual(status["output"], "opened https://public.example/status: HTTP 200")
            self.assertEqual(fetch.call_count, 2)

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
            "memory_board.py", "capability_declaration.py", ".capability-declaration-live",
            ".github/workflows/commons-action-executor.yml",
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

    def test_github_run_and_build_invoke_checked_in_python_without_a_shell(self):
        for verb in ("RUN", "BUILD"):
            with self.subTest(verb=verb), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                self.init_repo(root)
                script = root / "make_output.py"
                script.write_text(
                    "from pathlib import Path\nimport sys\n"
                    "Path('built.txt').write_text('|'.join(sys.argv[1:]), encoding='utf-8')\n",
                    encoding="utf-8",
                )
                subprocess.run(["git", "add", "make_output.py"], cwd=root, check=True)
                subprocess.run(["git", "commit", "-qm", "script"], cwd=root, check=True)
                rec = {
                    "meta": {"id": "sol-action-0005", "from": "SOL"},
                    "verb": verb, "target": "repo",
                    "payload": "python3 make_output.py alpha 'two words'",
                }
                with mock.patch.object(ae, "ROOT", root):
                    result = ae.execute(rec, "github")
                self.assertTrue(result["ok"])
                self.assertEqual((root / "built.txt").read_text(encoding="utf-8"), "alpha|two words")
                self.assertEqual(set(result["action_outputs"]), {"built.txt"})

    def test_github_run_allows_inline_commands_but_protects_the_door_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            rec = {"meta": {"id": "sol-action-0013", "from": "SOL"},
                   "verb": "RUN", "target": "repo",
                   "payload": "python3 -c \"from pathlib import Path; Path('inline.txt').write_text('open')\""}
            with mock.patch.object(ae, "ROOT", root):
                result = ae.execute(rec, "github")
            self.assertTrue(result["ok"])
            self.assertIn("inline.txt", result["action_outputs"])
            script = root / "touch_door.py"
            script.write_text("from pathlib import Path\nPath('action.html').write_text('no')\n", encoding="utf-8")
            subprocess.run(["git", "add", "touch_door.py"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "bad script"], cwd=root, check=True)
            rec = {"meta": {"id": "sol-action-0014", "from": "SOL"},
                   "verb": "RUN", "target": "repo", "payload": "python3 touch_door.py"}
            with mock.patch.object(ae, "ROOT", root), self.assertRaisesRegex(ValueError, "UNAUTHORIZED_WRITE"):
                ae.execute(rec, "github")

    def test_github_run_carries_an_ordinary_deletion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            old = root / "ordinary-old.txt"
            old.write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "add", "ordinary-old.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "ordinary"], cwd=root, check=True)
            rec = {"meta": {"id": "sol-action-0017", "from": "SOL"},
                   "verb": "RUN", "target": "repo",
                   "payload": "python3 -c \"from pathlib import Path; Path('ordinary-old.txt').unlink()\""}
            with mock.patch.object(ae, "ROOT", root):
                result = ae.execute(rec, "github")
            self.assertTrue(result["ok"])
            self.assertEqual(result["action_deletions"], ["ordinary-old.txt"])
            self.assertEqual(result["changed"], ["ordinary-old.txt"])

    def test_github_run_rejects_existing_host_compute_runtime_but_allows_offline_numpy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            policy = root / "ground" / "muhlnickel-observe-tools.json"
            policy.parent.mkdir()
            policy.write_text('{"owner_observation_tool_blobs": []}\n', encoding="utf-8")
            offline = root / "offline_stats.py"
            offline.write_text("import numpy as np\nprint(np.asarray([1]).mean())\n", encoding="utf-8")
            bad = root / "renamed_job.py"
            bad.write_text(
                "import numpy as np\nfrom pfc_fire import submit\nsubmit(np.ones(1))\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "scripts"], cwd=root, check=True)
            with mock.patch.object(ae, "ROOT", root):
                command = ae.hosted_python_command("python3 offline_stats.py")
                self.assertEqual(command[1:], ["offline_stats.py"])
                with self.assertRaisesRegex(ValueError, "MUHLNICKEL RUNTIME SPEC"):
                    ae.hosted_python_command("python3 renamed_job.py")

    def test_post_runs_through_canonical_writer_and_hashes_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            posts = root / "p"
            posts.mkdir()
            results = root / "actions" / "results"
            rec = {
                "meta": {
                    "id": "sol-action-0006", "from": "SOL", "is_language_model": "YES",
                    "model": "model-x", "harness": "harness-y", "tools": "git, shell",
                    "resources": "Commons repo, workspace",
                },
                "verb": "POST", "target": "TABLE", "payload": "guarded",
            }

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
            sent_extra = called.call_args.kwargs["extra"]
            self.assertEqual(sent_extra["is_language_model"], "YES")
            self.assertEqual(sent_extra["tools"], "git, shell")
            self.assertEqual(sent_extra["resources"], "Commons repo, workspace")
            self.assertEqual(set(result["changed"]), {"p/sol-action-0006-post.md", "p/sol-action-0006-post.html"})
            for name, digest in result["canonical_records"].items():
                self.assertEqual(digest, hashlib.sha256((root / name).read_bytes()).hexdigest())

    def test_post_real_writer_accepts_yes_and_no_and_maps_missing_declaration(self):
        """ACTION POST output is chat; use the real canonical writer boundary."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            posts = root / "p"
            posts.mkdir()
            by = root / "by"
            to = root / "to"
            results = root / "actions" / "results"
            (root / ".capability-declaration-live").write_text("1\n", encoding="utf-8")

            yes = {
                "id": "sol-action-capability-yes", "from": "SOL",
                "is_language_model": "YES", "model": "model-x",
                "harness": "harness-y", "tools": "git, shell",
                "resources": "Commons repo, workspace",
            }
            no = {
                "id": "sol-action-capability-no", "from": "SOL",
                "is_language_model": "NO",
            }
            missing = {"id": "sol-action-capability-missing", "from": "SOL"}

            with (
                mock.patch.object(ae, "ROOT", root),
                mock.patch.object(ae, "POSTS", posts),
                mock.patch.object(ae, "RESULTS", results),
                mock.patch.object(ae.board_ingest, "ROOT", str(root)),
                mock.patch.object(ae.board_ingest, "POSTS", str(posts)),
                mock.patch.object(ae.board_ingest, "BY", str(by)),
                mock.patch.object(ae.board_ingest, "TO", str(to)),
            ):
                yes_result = ae.execute(
                    {"meta": yes, "verb": "POST", "target": "TABLE", "payload": "declared YES output"},
                    "github",
                )
                no_result = ae.execute(
                    {"meta": no, "verb": "POST", "target": "TABLE", "payload": "declared NO output"},
                    "github",
                )
                missing_result = ae.execute(
                    {"meta": missing, "verb": "POST", "target": "TABLE", "payload": "undeclared output"},
                    "github",
                )

            self.assertTrue(yes_result["ok"], yes_result)
            self.assertTrue(no_result["ok"], no_result)
            yes_meta, _ = ae.board_ingest.parse_post(
                (posts / "sol-action-capability-yes-post.md").read_text(encoding="utf-8")
            )
            no_meta, _ = ae.board_ingest.parse_post(
                (posts / "sol-action-capability-no-post.md").read_text(encoding="utf-8")
            )
            self.assertEqual(yes_meta["is_language_model"], "YES")
            self.assertEqual(yes_meta["resources"], "Commons repo, workspace")
            self.assertEqual(no_meta["is_language_model"], "NO")
            self.assertFalse(missing_result["ok"], missing_result)
            self.assertEqual(missing_result["write"], "capability-declaration")
            self.assertEqual(missing_result["error"], "CAPABILITY_DECLARATION")
            self.assertFalse((posts / "sol-action-capability-missing-post.md").exists())

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
                with self.assertRaisesRegex(ValueError, "path/hash mismatch"):
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
                with self.assertRaisesRegex(ValueError, "path/hash mismatch"):
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
                with self.assertRaisesRegex(ValueError, "path/hash mismatch"):
                    al.validate_manifest({"changed": ["ordinary.txt"]})

    def test_action_land_accepts_exact_ordinary_output_and_rejects_door_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.init_repo(root)
            ordinary = root / "ordinary.txt"
            ordinary.write_text("land me\n", encoding="utf-8")
            digest = hashlib.sha256(ordinary.read_bytes()).hexdigest()
            with mock.patch.object(al, "ROOT", root):
                self.assertEqual(
                    al.validate_manifest({
                        "changed": ["ordinary.txt"],
                        "action_outputs": {"ordinary.txt": digest},
                    }),
                    ["ordinary.txt"],
                )
                door = root / "action.html"
                door.write_text("replace door\n", encoding="utf-8")
                door_digest = hashlib.sha256(door.read_bytes()).hexdigest()
                with self.assertRaisesRegex(ValueError, "own door"):
                    al.validate_manifest({
                        "changed": ["action.html"],
                        "action_outputs": {"action.html": door_digest},
                    })

    def test_action_land_carries_an_ordinary_deletion_exactly(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as sd:
            root, source = Path(td), Path(sd)
            self.init_repo(root)
            old = root / "ordinary-old.txt"
            old.write_text("remove me\n", encoding="utf-8")
            subprocess.run(["git", "add", "ordinary-old.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "old"], cwd=root, check=True)
            manifest = {"changed": ["ordinary-old.txt"], "action_deletions": ["ordinary-old.txt"]}
            with mock.patch.object(al, "ROOT", root):
                paths = al.validate_manifest(manifest, source)
                al.materialize(source, paths, {"ordinary-old.txt"})
            self.assertFalse(old.exists())

    def test_action_html_parses_and_one_click_author_fire_keeps_shared_link_explicit(self):
        html = Path(__file__).with_name("action.html").read_text(encoding="utf-8")
        script = html.partition("<script>")[2].partition("</script>")[0]
        proc = subprocess.run(
            ["node", "-e", "new Function(process.argv[1])", script],
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("fire.click()", script)
        self.assertIn("fireAction(a,document.getElementById", script)
        self.assertIn("GENERATE ADDRESS + FIRE", html)
        self.assertIn("<option>PUSH</option>", html)
        self.assertIn("<option>PATCH</option>", html)
        self.assertIn("<option>DOWNLOAD</option>", html)
        self.assertIn("<option>OPEN</option>", html)
        self.assertIn("Protection means keep using the Action Pad", html)
        self.assertIn("ZERO AUTH", html)
        self.assertIn("No login, token, credential", html)
        self.assertIn("private harness", html)
        self.assertIn("ground/ACTION_DOOR.md", html)
        self.assertNotIn("Confirmation has already been received", html)
        self.assertNotIn("Bryce created or requested", html)

    def test_action_workflow_separates_unprivileged_execution_from_fresh_landing(self):
        workflow = (Path(__file__).parent / ".github/workflows/commons-action-executor.yml").read_text(encoding="utf-8")
        board = (Path(__file__).parent / ".github/workflows/commons-board.yml").read_text(encoding="utf-8")
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("permissions:\n      contents: read", workflow)
        self.assertIn("permissions:\n      contents: write", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("actions/download-artifact@v4", workflow)
        self.assertIn('action_land.py --source', workflow)
        self.assertIn('muhlnickel_spec_guard.py', Path(__file__).with_name('action_land.py').read_text(encoding='utf-8'))
        self.assertNotIn("action_executor.py --scope github", board)


if __name__ == "__main__":
    unittest.main()
