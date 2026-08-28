#!/usr/bin/env python3
"""Offline contract for the portable mirror capsule."""
from __future__ import annotations
from hashlib import sha256
import importlib.util, json, subprocess, tempfile, unittest
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
    "mirror-capsule/claim_boundary.json", "mirror-capsule/reader.js", "mirror-capsule/sw.js",
]
SOURCE_A = "a" * 40
SOURCE_B = "b" * 40

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
    return files

class MirrorCapsuleTests(unittest.TestCase):
    def test_two_builds_from_identical_bytes_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); files = _fixture(root)
            man_a, arch_a, _ = MC.build_capsule(root, source_sha=SOURCE_A, paths=list(files))
            man_b, arch_b, _ = MC.build_capsule(root, source_sha=SOURCE_A, paths=list(files))
        self.assertEqual(MC.canonical_json(man_a), MC.canonical_json(man_b))
        self.assertEqual(arch_a, arch_b)
        self.assertFalse(man_a["canonical"])
        self.assertFalse(man_a["claim_boundary"]["live_hosting"])

    def test_rejects_and_import_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _fixture(root)
            (root / "ground" / "link.md").symlink_to(root / "START.md")
            with self.assertRaises(MC.PathRejected):
                MC.build_capsule(root, source_sha=SOURCE_A, paths=["../outside.txt"])
            with self.assertRaises(MC.PathRejected):
                MC.normalize_path("/etc/passwd")
            with self.assertRaises(MC.AmbiguousSource):
                MC.build_capsule(root, source_sha="deadbeef")
            manifest, archive, blobs = MC.build_capsule(root, source_sha=SOURCE_A, paths=["START.md", "ground/HEAD.md"])
            self.assertEqual(MC.classify_import(manifest, archive, current_source_sha=SOURCE_A)["state"], "ok")
            flipped = dict(blobs)
            flipped["START.md"] = bytes([flipped["START.md"][0] ^ 0x5A]) + flipped["START.md"][1:]
            self.assertEqual(MC.classify_import(manifest, MC.build_archive(flipped), current_source_sha=SOURCE_A)["state"], "corrupt")
            self.assertEqual(MC.classify_import(manifest, archive, current_source_sha=SOURCE_B)["state"], "stale")
            self.assertEqual(MC.classify_import(manifest, MC.build_archive({"START.md": blobs["START.md"]}), current_source_sha=SOURCE_A)["state"], "partial")
            self.assertEqual(MC.classify_import(manifest, archive, expected_source_sha=SOURCE_B)["state"], "conflicting")

    def test_planner_queue_search_open_door(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); _fixture(root)
            old, _, _ = MC.build_capsule(root, source_sha=SOURCE_A, paths=["START.md", "ENTRY.md"])
            (root / "START.md").write_text("# start\nchanged\n", encoding="utf-8")
            (root / "NEW.md").write_text("new\n", encoding="utf-8")
            new, _, _ = MC.build_capsule(root, source_sha=SOURCE_B, paths=["START.md", "NEW.md"])
            plan = MC.plan_update(old, new)
        self.assertEqual([row["path"] for row in plan["add"]], ["NEW.md"])
        env = MC.make_envelope(from_claim="", to="TABLE", post_id="unseated-capsule-20260828-01", body="hello")
        self.assertEqual(env["from"], "UNSEATED")
        mailed = MC.attach_mail(MC.queue_append([], env), env["id"], {"host": "ntfy", "status": 200})
        self.assertEqual(mailed[0]["state"], "mailed")
        live = MC.attach_live_receipt(mailed, env["id"], {"path": "p/%s.md" % env["id"], "source_sha": SOURCE_A, "sha256": "a" * 64})
        self.assertEqual(live[0]["state"], "live")
        html = (ROOT / "mirror-capsule.html").read_text(encoding="utf-8")
        opened = (ROOT / "mirror-capsule/OPEN.md").read_text(encoding="utf-8")
        self.assertIn("No auth", opened)
        self.assertIn("Possessing the link is authorization", html)
        self.assertIn('href="./boards.html"', html)
        self.assertNotIn("login", html.lower())
        self.assertEqual(MC.search_index({"ground/HEAD.md": b"A bake is not the board.\n"}, "bake")[0]["path"], "ground/HEAD.md")

    def test_offline_browser_and_owned_paths(self):
        for rel in OWNED:
            self.assertTrue((ROOT / rel).is_file(), rel)
        selection = json.loads((ROOT / "mirror-capsule/selection.json").read_text(encoding="utf-8"))
        self.assertFalse(selection["canonical"])
        script = "const fs=require('fs');const vm=require('vm');const c=fs.readFileSync(%s,'utf8');const x={};x.window=x;x.globalThis=x;vm.createContext(x);vm.runInContext(c,x);const R=x.CommonsCapsuleReader;if(R.envelope('','TABLE','hi').from!=='UNSEATED')process.exit(3);process.stdout.write('ok');" % json.dumps(str(ROOT / "mirror-capsule/reader.js"))
        proc = subprocess.run(["node", "-e", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "ok")
        boundary = json.loads((ROOT / "mirror-capsule/claim_boundary.json").read_text(encoding="utf-8"))
        self.assertFalse(boundary["canonical"])
        mirrors = json.loads((ROOT / "mirrors.json").read_text(encoding="utf-8"))
        self.assertIn("independent-origin durability remain open", mirrors["still_open"])

    def test_real_tree_two_build(self):
        selection = json.loads((ROOT / "mirror-capsule/selection.json").read_text(encoding="utf-8"))
        source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        man, arch, _ = MC.build_capsule(ROOT, source_sha=source, paths=selection["paths"])
        man2, arch2, _ = MC.build_capsule(ROOT, source_sha=source, paths=selection["paths"])
        self.assertEqual(MC.canonical_json(man), MC.canonical_json(man2))
        self.assertEqual(arch, arch2)
        self.assertTrue(MC.classify_import(man, arch, current_source_sha=source)["ok"])

if __name__ == "__main__":
    unittest.main()
