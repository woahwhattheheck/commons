#!/usr/bin/env python3
"""Offline contract for the portable mirror capsule."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host" / "mirror_capsule.py"
SPEC = importlib.util.spec_from_file_location("mirror_capsule", HOST)
MC = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MC)

OWNED = [
    "host/mirror_capsule.py", "test_mirror_capsule.py", "mirror-capsule.html",
    "mirror-capsule/OPEN.md", "mirror-capsule/schema.json", "mirror-capsule/selection.json",
    "mirror-capsule/claim_boundary.json", "mirror-capsule/reader.js", "mirror-capsule/sw.js", "test_mirror_capsule.js",
]
SOURCE_A = "a" * 40
SOURCE_B = "b" * 40
RUNTIME_COPIES = [
    "mirror-capsule/OPEN.md",
    "mirror-capsule/schema.json",
    "mirror-capsule/selection.json",
    "mirror-capsule/claim_boundary.json",
    "mirror-capsule/reader.js",
    "mirror-capsule/sw.js",
    "mirror-capsule.html",
]


def _fixture(base: Path):
    files = {
        "START.md": "# start\nOpen door. No seat. git HEAD is canonical.\n",
        "ENTRY.md": "entry door\n", "CRAWLERS.md": "crawler access\n",
        "ISSUE.md": "Road B is a GitHub issue.\n",
        "mirrors.json": '{"law":"git HEAD is canonical"}\n',
        "mirror.html": "<!doctype html><title>mirror</title>\n",
        "ground/HEAD.md": "A bake is not the board.\n",
        "ground/OPEN_DOOR.md": "If you have the link, post.\n",
        "ground/EXECUTE.md": "Execute immediately.\n",
        "ground/LAND.md": "Land on current main.\n",
        "relay-manifest.schema.json": '{"schema":"commons-relay-manifest-v1"}\n',
    }
    for rel, text in files.items():
        path = base.joinpath(*rel.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return {k: v.encode("utf-8") for k, v in files.items()}


def _copy_runtime(base: Path):
    for rel in RUNTIME_COPIES:
        src = ROOT / rel
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())


def _git_env():
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "capsule-test",
        "GIT_AUTHOR_EMAIL": "capsule-test@example.invalid",
        "GIT_COMMITTER_NAME": "capsule-test",
        "GIT_COMMITTER_EMAIL": "capsule-test@example.invalid",
        "GIT_AUTHOR_DATE": "2026-08-28T00:00:00 +0000",
        "GIT_COMMITTER_DATE": "2026-08-28T00:00:00 +0000",
        "GIT_CONFIG_NOSYSTEM": "1",
    })
    return env


def _git_init(base: Path):
    files = _fixture(base)
    _copy_runtime(base)
    env = _git_env()
    subprocess.run(["git", "init"], cwd=base, check=True, capture_output=True, env=env)
    subprocess.run(["git", "config", "user.email", "capsule-test@example.invalid"], cwd=base, check=True, capture_output=True, env=env)
    subprocess.run(["git", "config", "user.name", "capsule-test"], cwd=base, check=True, capture_output=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=base, check=True, capture_output=True, env=env)
    subprocess.run(["git", "commit", "-m", "init"], cwd=base, check=True, capture_output=True, env=env)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=base, text=True, env=env).strip()
    return files, sha


def _reader(files, source_sha=SOURCE_A, **kwargs):
    return MC.MemoryReader(files, source_sha, **kwargs)


def _craft_tar(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for name, data, extra in members:
            info = tarfile.TarInfo(name=name)
            if extra:
                for key, value in extra.items():
                    setattr(info, key, value)
            if info.isfile() or extra.get("type", tarfile.REGTYPE) == tarfile.REGTYPE:
                payload = data if isinstance(data, (bytes, bytearray)) else b""
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
            else:
                info.size = 0
                tar.addfile(info)
    return buf.getvalue()


class MirrorCapsuleTests(unittest.TestCase):
    def test_two_builds_from_identical_bytes_match(self):
        files = _fixture(Path(tempfile.mkdtemp()))
        reader = _reader(files)
        man_a, arch_a, _ = MC.build_capsule(Path("."), source_sha=SOURCE_A, paths=list(files), reader=reader)
        man_b, arch_b, _ = MC.build_capsule(Path("."), source_sha=SOURCE_A, paths=list(files), reader=reader)
        self.assertEqual(MC.canonical_json(man_a), MC.canonical_json(man_b))
        self.assertEqual(arch_a, arch_b)
        self.assertFalse(man_a["canonical"])
        self.assertFalse(man_a["claim_boundary"]["live_hosting"])

    def test_dirty_selected_bytes_cannot_be_labeled_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files, sha = _git_init(root)
            (root / "START.md").write_text("DIRTY WORKING TREE\n", encoding="utf-8")
            man, arch, blobs = MC.build_capsule(root, source_sha=sha, paths=["START.md"])
            self.assertNotIn(b"DIRTY WORKING TREE", blobs["START.md"])
            self.assertEqual(blobs["START.md"], files["START.md"])
            self.assertEqual(man["source_sha"], sha)
            unpacked = MC.read_archive(arch)
            self.assertEqual(unpacked["START.md"], files["START.md"])

    def test_explicit_source_sha_uses_git_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files, sha1 = _git_init(root)
            (root / "START.md").write_text("second commit\n", encoding="utf-8")
            env = _git_env()
            subprocess.run(["git", "add", "START.md"], cwd=root, check=True, capture_output=True, env=env)
            subprocess.run(["git", "commit", "-m", "second"], cwd=root, check=True, capture_output=True, env=env)
            sha2 = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            self.assertNotEqual(sha1, sha2)
            man, _, blobs = MC.build_capsule(root, source_sha=sha1, paths=["START.md"])
            self.assertEqual(man["source_sha"], sha1)
            self.assertEqual(blobs["START.md"], files["START.md"])
            man2, _, blobs2 = MC.build_capsule(root, source_sha=sha2, paths=["START.md"])
            self.assertEqual(blobs2["START.md"], b"second commit\n")

    def test_refuses_working_tree_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fixture(root)
            with self.assertRaises(MC.AmbiguousSource):
                MC.build_capsule(root, source_sha=SOURCE_A, paths=["START.md"])

    def test_invalid_or_all_zero_manifest_digest_rejected(self):
        files = {"START.md": b"hello\n"}
        man, arch, _ = MC.build_capsule(Path("."), source_sha=SOURCE_A, paths=["START.md"], reader=_reader(files))
        broken = dict(man)
        broken["manifest_sha256"] = "0" * 64
        with self.assertRaises(MC.HashCorrupt):
            MC.verify_manifest(broken)
        self.assertEqual(MC.classify_import(broken, arch)["state"], "corrupt")
        broken2 = dict(man)
        broken2["manifest_sha256"] = "a" * 64
        with self.assertRaises(MC.HashCorrupt):
            MC.verify_manifest(broken2)

    def test_duplicate_tar_members_rejected_before_map(self):
        blob = _craft_tar([
            ("START.md", b"one\n", {"type": tarfile.REGTYPE, "mtime": 0, "mode": 0o644}),
            ("START.md", b"two\n", {"type": tarfile.REGTYPE, "mtime": 0, "mode": 0o644}),
        ])
        with self.assertRaises(MC.PathRejected) as ctx:
            MC.read_archive(blob)
        self.assertIn("duplicate", str(ctx.exception))

    def test_duplicate_normalized_selection_and_entry_paths_rejected(self):
        files = {"START.md": b"hello\n"}
        with self.assertRaises(MC.PathRejected):
            MC.build_capsule(Path("."), source_sha=SOURCE_A, paths=["START.md", "START.md"], reader=_reader(files))
        entries = [
            {"path": "START.md", "bytes": 6, "sha256": sha256(b"hello\n").hexdigest(), "source_sha": SOURCE_A, "media_type": "text/markdown; charset=utf-8"},
            {"path": "START.md", "bytes": 6, "sha256": sha256(b"hello\n").hexdigest(), "source_sha": SOURCE_A, "media_type": "text/markdown; charset=utf-8"},
        ]
        with self.assertRaises(MC.PathRejected):
            MC.build_manifest(entries, SOURCE_A, ["START.md", "START.md"])

    def test_links_traversal_absolute_devices_nonregular_rejected(self):
        with self.assertRaises(MC.PathRejected):
            MC.normalize_path("../outside.txt")
        with self.assertRaises(MC.PathRejected):
            MC.normalize_path("/etc/passwd")
        with self.assertRaises(MC.PathRejected):
            MC.normalize_path("foo/../../etc/passwd")
        files = {"START.md": b"ok\n"}
        reader = _reader(files, modes={"link.md": "120000"})
        reader.files["link.md"] = b"not-used"
        with self.assertRaises(MC.PathRejected):
            MC.build_capsule(Path("."), source_sha=SOURCE_A, paths=["link.md"], reader=reader)
        with self.assertRaises(MC.PathRejected):
            MC.read_archive(_craft_tar([("../etc/passwd", b"x", {"type": tarfile.REGTYPE, "mtime": 0, "mode": 0o644})]))
        with self.assertRaises(MC.PathRejected):
            MC.read_archive(_craft_tar([("/etc/passwd", b"x", {"type": tarfile.REGTYPE, "mtime": 0, "mode": 0o644})]))
        with self.assertRaises(MC.PathRejected):
            MC.read_archive(_craft_tar([("s", b"", {"type": tarfile.SYMTYPE, "linkname": "START.md"})]))
        with self.assertRaises(MC.PathRejected):
            MC.read_archive(_craft_tar([("d", b"", {"type": tarfile.DIRTYPE})]))
        with self.assertRaises(MC.PathRejected):
            MC.read_archive(_craft_tar([("c", b"", {"type": tarfile.CHRTYPE, "devmajor": 1, "devminor": 3})]))

    def test_import_states_partial_extra_corrupt_stale_conflicting(self):
        files = {"START.md": b"alpha\n", "ENTRY.md": b"beta\n"}
        manifest, archive, blobs = MC.build_capsule(Path("."), source_sha=SOURCE_A, paths=list(files), reader=_reader(files))
        self.assertEqual(MC.classify_import(manifest, archive, current_source_sha=SOURCE_A)["state"], "ok")
        flipped = dict(blobs)
        flipped["START.md"] = bytes([flipped["START.md"][0] ^ 0x5A]) + flipped["START.md"][1:]
        self.assertEqual(MC.classify_import(manifest, MC.build_archive(flipped), current_source_sha=SOURCE_A)["state"], "corrupt")
        self.assertEqual(MC.classify_import(manifest, archive, current_source_sha=SOURCE_B)["state"], "stale")
        self.assertEqual(MC.classify_import(manifest, MC.build_archive({"START.md": blobs["START.md"]}), current_source_sha=SOURCE_A)["state"], "partial")
        extra = dict(blobs)
        extra["BONUS.md"] = b"nope\n"
        classified = MC.classify_import(manifest, MC.build_archive(extra), current_source_sha=SOURCE_A)
        self.assertEqual(classified["state"], "extra")
        self.assertEqual(MC.classify_import(manifest, archive, expected_source_sha=SOURCE_B)["state"], "conflicting")
        mixed = dict(manifest)
        mixed["entries"] = list(manifest["entries"])
        mixed["entries"][0] = dict(mixed["entries"][0], source_sha=SOURCE_B)
        mixed["manifest_sha256"] = MC.compute_manifest_digest(mixed)
        self.assertEqual(MC.classify_import(mixed, archive, current_source_sha=SOURCE_A)["state"], "conflicting")

    def test_shape_only_live_receipt_does_not_transition(self):
        env = MC.make_envelope("", "TABLE", "unseated-capsule-20260828-01", "hello")
        mailed = MC.attach_mail(MC.queue_append([], env), env["id"], {"host": "ntfy", "status": 200})
        self.assertEqual(mailed[0]["state"], "mailed")
        out, info = MC.attach_live_receipt(mailed, env["id"], {"path": "p/%s.md" % env["id"], "source_sha": SOURCE_A, "sha256": "a" * 64})
        self.assertEqual(info["state"], "LIVE_RECEIPT_UNVERIFIED")
        self.assertEqual(out[0]["state"], "mailed")

    def test_exact_pinned_bytes_transition_to_live(self):
        env = MC.make_envelope("", "TABLE", "unseated-capsule-20260828-02", "hello")
        queued = MC.queue_append([], env)
        payload = b"# live\nexact bytes\n"
        digest = sha256(payload).hexdigest()
        blob = MC.git_blob_sha1(payload)
        path = "p/%s.md" % env["id"]
        reader = MC.MemoryReader({"START.md": b"x"}, SOURCE_A, by_sha={(SOURCE_A, path): payload})
        out, info = MC.attach_live_receipt(queued, env["id"], {"path": path, "source_sha": SOURCE_A, "sha256": digest, "git_blob": blob}, reader=reader)
        self.assertTrue(info["ok"])
        self.assertEqual(out[0]["state"], "live")
        self.assertEqual(out[0]["live_receipt"]["sha256"], digest)

    def test_wrong_path_source_sha256_blob_or_id_rejected(self):
        env = MC.make_envelope("", "TABLE", "unseated-capsule-20260828-03", "hello")
        queued = MC.queue_append([], env)
        payload = b"# live\nexact bytes\n"
        digest = sha256(payload).hexdigest()
        path = "p/%s.md" % env["id"]
        reader = MC.MemoryReader({"START.md": b"x"}, SOURCE_A, by_sha={(SOURCE_A, path): payload})
        with self.assertRaises(MC.CapsuleError):
            MC.attach_live_receipt(queued, env["id"], {"path": "p/other-id-123.md", "source_sha": SOURCE_A, "sha256": digest}, bytes_blob=payload)
        with self.assertRaises(MC.CapsuleError):
            MC.attach_live_receipt(queued, "short", {"path": "p/short.md", "source_sha": SOURCE_A, "sha256": digest}, bytes_blob=payload)
        out_b, info_b = MC.attach_live_receipt(queued, env["id"], {"path": path, "source_sha": SOURCE_B, "sha256": digest}, reader=reader)
        self.assertEqual(info_b["state"], "LIVE_RECEIPT_UNVERIFIED")
        self.assertEqual(out_b[0]["state"], "queued")
        with self.assertRaises(MC.CapsuleError):
            MC.attach_live_receipt(queued, env["id"], {"path": path, "source_sha": SOURCE_A, "sha256": "b" * 64}, bytes_blob=payload)
        with self.assertRaises(MC.CapsuleError):
            MC.attach_live_receipt(queued, env["id"], {"path": path, "source_sha": SOURCE_A, "sha256": digest, "git_blob": "c" * 40}, bytes_blob=payload)

    def test_canonical_ids_python(self):
        self.assertTrue(MC.valid_post_id("unseated-capsule-20260828-01"))
        self.assertTrue(MC.valid_post_id("A" * 8))
        self.assertTrue(MC.valid_post_id("A" * 80))
        self.assertTrue(MC.valid_post_id("g1234567"))
        self.assertFalse(MC.valid_post_id("short"))
        self.assertFalse(MC.valid_post_id("A" * 7))
        self.assertFalse(MC.valid_post_id("A" * 81))
        self.assertFalse(MC.valid_post_id("foo:bar-01"))
        self.assertFalse(MC.valid_post_id("../escape"))
        self.assertFalse(MC.valid_post_id("id with space"))
        self.assertFalse(MC.valid_post_id("-leading1"))
        with self.assertRaises(MC.CapsuleError):
            MC.make_envelope("", "TABLE", "bad:id", "x")

    def test_cli_build_verify_plan_success_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            files, sha = _git_init(root)
            out = Path(tmp) / "dist"
            proc = subprocess.run([sys.executable, str(HOST), "build", "--root", str(root), "--source-sha", sha, "--selection", "mirror-capsule/selection.json", "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["source_sha"], sha)
            self.assertGreater(payload["entry_count"], 0)
            proc2 = subprocess.run([sys.executable, str(HOST), "verify", "--distribution", str(out)], capture_output=True, text=True)
            self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)
            man_path = out / "manifest.json"
            proc3 = subprocess.run([sys.executable, str(HOST), "plan", "--old", str(man_path), "--new", str(man_path)], capture_output=True, text=True)
            self.assertEqual(proc3.returncode, 0, proc3.stdout + proc3.stderr)
            plan = json.loads(proc3.stdout)
            self.assertEqual(plan["unchanged"], payload["entry_count"])
            proc4 = subprocess.run([sys.executable, str(HOST), "verify", "--distribution", str(Path(tmp) / "missing")], capture_output=True, text=True)
            self.assertNotEqual(proc4.returncode, 0)
            proc5 = subprocess.run([sys.executable, str(HOST)], capture_output=True, text=True)
            self.assertEqual(proc5.returncode, 2)
            bad = json.loads(man_path.read_text(encoding="utf-8"))
            bad["manifest_sha256"] = "0" * 64
            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text(json.dumps(bad), encoding="utf-8")
            proc6 = subprocess.run([sys.executable, str(HOST), "plan", "--old", str(bad_path), "--new", str(man_path)], capture_output=True, text=True)
            self.assertNotEqual(proc6.returncode, 0)

    def test_atomic_build_failure_leaves_no_partial_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            files, sha = _git_init(root)
            out = Path(tmp) / "dist"
            man, arch, blobs = MC.build_capsule(root, source_sha=sha, paths=["START.md", "ground/HEAD.md"])
            runtime = MC._copy_runtime(root, sha, None)
            tree = MC.assemble_distribution(man, arch, blobs, runtime)
            with self.assertRaises(MC.CapsuleError):
                MC.write_distribution(tree, out, root, ["START.md"], fail_after_write=True)
            self.assertFalse(out.exists())
            leftovers = [p for p in Path(tmp).iterdir() if p.name.startswith("dist.")]
            self.assertEqual(leftovers, [])

    def test_two_full_output_trees_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            files, sha = _git_init(root)
            out1 = Path(tmp) / "d1"
            out2 = Path(tmp) / "d2"
            for dest in (out1, out2):
                proc = subprocess.run([sys.executable, str(HOST), "build", "--root", str(root), "--source-sha", sha, "--output", str(dest)], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            tree1 = MC.tree_bytes(out1)
            tree2 = MC.tree_bytes(out2)
            self.assertEqual(sorted(tree1), sorted(tree2))
            for name in tree1:
                self.assertEqual(tree1[name], tree2[name], name)

    def test_generated_search_index_covers_every_textual_file_and_is_deterministic(self):
        files = _fixture(Path(tempfile.mkdtemp()))
        reader = _reader(files)
        man, arch, blobs = MC.build_capsule(Path("."), source_sha=SOURCE_A, paths=list(files), reader=reader)
        idx1 = MC.build_search_index(blobs, SOURCE_A)
        idx2 = MC.build_search_index(blobs, SOURCE_A)
        self.assertEqual(MC.canonical_json(idx1), MC.canonical_json(idx2))
        self.assertEqual(sorted(row["path"] for row in idx1["entries"]), sorted(files))
        hits = MC.search_index(blobs, "bake")
        self.assertEqual(hits[0]["path"], "ground/HEAD.md")

    def test_built_reader_consumes_generated_manifest_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            _files, sha = _git_init(root)
            out = Path(tmp) / "dist"
            proc = subprocess.run([sys.executable, str(HOST), "build", "--root", str(root), "--source-sha", sha, "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            html = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn("manifest.json", html)
            self.assertIn("index.json", html)
            self.assertIn('data-capsule="built"', html)
            self.assertNotIn("innerHTML", html)
            sw = (out / "sw.js").read_text(encoding="utf-8")
            owned = MC._parse_sw_owned(sw)
            for url in owned:
                rel = url[2:] if url.startswith("./") else url
                self.assertTrue((out / rel).is_file(), rel)
            source_sw = (ROOT / "mirror-capsule" / "sw.js").read_text(encoding="utf-8")
            self.assertNotIn("./manifest.json", source_sw)
            self.assertNotIn("./index.json", source_sw)

    def test_open_door_contract_intact(self):
        html = (ROOT / "mirror-capsule.html").read_text(encoding="utf-8")
        opened = (ROOT / "mirror-capsule/OPEN.md").read_text(encoding="utf-8")
        self.assertIn("No auth", opened)
        self.assertIn("Possessing the link is authorization", html)
        self.assertIn('href="./boards.html"', html)
        self.assertNotIn("login", html.lower())
        self.assertIn("unbuilt source door", html.lower())
        self.assertNotIn("serviceWorker.register", html)
        boundary = json.loads((ROOT / "mirror-capsule/claim_boundary.json").read_text(encoding="utf-8"))
        self.assertFalse(boundary["canonical"])
        self.assertFalse(boundary["live_hosting"])
        self.assertTrue(boundary["portable_snapshot"])
        mirrors = json.loads((ROOT / "mirrors.json").read_text(encoding="utf-8"))
        self.assertIn("EXTERNAL_PROVIDER_ACTION", mirrors["still_open"])
        self.assertNotIn("HTTP 523", mirrors["still_open"])
        internet_archive = next(row for row in mirrors["read"] if row["id"] == "internet-archive")
        self.assertIn("HTTP 200", internet_archive["notes"])
        self.assertIn("Historical 523 receipt", internet_archive["notes"])
        historical_523 = ROOT / "ci/moving_main/receipts/ia-save-523.json"
        self.assertTrue(historical_523.is_file())

    def test_planner_queue_search_open_door(self):
        files = _fixture(Path(tempfile.mkdtemp()))
        old, _, _ = MC.build_capsule(Path("."), source_sha=SOURCE_A, paths=["START.md", "ENTRY.md"], reader=_reader({k: files[k] for k in ("START.md", "ENTRY.md")}))
        changed = dict(files)
        changed["START.md"] = b"# start\nchanged\n"
        changed["NEW.md"] = b"new\n"
        new, _, _ = MC.build_capsule(Path("."), source_sha=SOURCE_B, paths=["START.md", "NEW.md"], reader=_reader({k: changed[k] for k in ("START.md", "NEW.md")}, SOURCE_B))
        plan = MC.plan_update(old, new)
        self.assertEqual([row["path"] for row in plan["add"]], ["NEW.md"])
        env = MC.make_envelope(from_claim="", to="TABLE", post_id="unseated-capsule-20260828-01", body="hello")
        self.assertEqual(env["from"], "UNSEATED")
        mailed = MC.attach_mail(MC.queue_append([], env), env["id"], {"host": "ntfy", "status": 200})
        self.assertEqual(mailed[0]["state"], "mailed")
        exported = MC.queue_export(mailed)
        imported = MC.queue_import(exported)
        self.assertEqual(imported[0]["envelope"]["id"], env["id"])
        dup = json.loads(exported.decode())
        dup["items"] = dup["items"] + dup["items"]
        with self.assertRaises(MC.CapsuleError):
            MC.queue_import(json.dumps(dup).encode())
        with self.assertRaises(MC.CapsuleError):
            MC.queue_import(b"{not json")
        self.assertEqual(MC.queue_forget(mailed), [])

    def test_offline_browser_and_owned_paths(self):
        for rel in OWNED:
            self.assertTrue((ROOT / rel).is_file(), rel)
        selection = json.loads((ROOT / "mirror-capsule/selection.json").read_text(encoding="utf-8"))
        self.assertFalse(selection["canonical"])
        script = (
            "const fs=require('fs');const vm=require('vm');"
            "const c=fs.readFileSync(%s,'utf8');const x={};x.window=x;x.globalThis=x;"
            "x.localStorage={_s:{},getItem(k){return this._s[k]||null;},setItem(k,v){this._s[k]=String(v);},removeItem(k){delete this._s[k];}};"
            "vm.createContext(x);vm.runInContext(c,x);const R=x.CommonsCapsuleReader;"
            "if(R.envelope('','TABLE','hi').from!=='UNSEATED')process.exit(3);"
            "if(R.ID_PATTERN!==%s)process.exit(4);"
            "process.stdout.write('ok');"
            % (json.dumps(str(ROOT / "mirror-capsule/reader.js")), json.dumps(MC.ID_PATTERN))
        )
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "ok")

    def test_js_suite_and_syntax(self):
        js_test = ROOT / "test_mirror_capsule.js"
        self.assertTrue(js_test.is_file())
        check = subprocess.run(["node", "--check", str(ROOT / "mirror-capsule/reader.js")], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        check2 = subprocess.run(["node", "--check", str(ROOT / "mirror-capsule/sw.js")], capture_output=True, text=True)
        self.assertEqual(check2.returncode, 0, check2.stderr)
        check3 = subprocess.run(["node", "--check", str(js_test)], capture_output=True, text=True)
        self.assertEqual(check3.returncode, 0, check3.stderr)
        proc = subprocess.run(["node", str(js_test)], capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_real_tree_two_build(self):
        selection = json.loads((ROOT / "mirror-capsule/selection.json").read_text(encoding="utf-8"))
        source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        man, arch, _ = MC.build_capsule(ROOT, source_sha=source, paths=selection["paths"])
        man2, arch2, _ = MC.build_capsule(ROOT, source_sha=source, paths=selection["paths"])
        self.assertEqual(MC.canonical_json(man), MC.canonical_json(man2))
        self.assertEqual(arch, arch2)
        self.assertTrue(MC.classify_import(man, arch, current_source_sha=source)["ok"])

    def test_output_refuses_repo_root_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files, sha = _git_init(root)
            man, arch, blobs = MC.build_capsule(root, source_sha=sha, paths=["START.md"])
            runtime = MC._copy_runtime(root, sha, None)
            tree = MC.assemble_distribution(man, arch, blobs, runtime)
            with self.assertRaises(MC.PathRejected):
                MC.write_distribution(tree, root, root, ["START.md"])


if __name__ == "__main__":
    unittest.main()
