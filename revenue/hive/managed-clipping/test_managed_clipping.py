#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("managed_clipping", HERE / "managed_clipping.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class ManagedClippingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_external_moment_adapter(self):
        normalized = mod.normalize_external_moments({
            "segments": [
                {"start_millis": "10", "end_millis": 50, "transcript": "hello"},
                {"start_ms": 60, "end_ms": 100, "caption": "world"},
            ]
        })
        self.assertEqual(normalized, [
            {"start_ms": 10, "end_ms": 50, "caption": "hello"},
            {"start_ms": 60, "end_ms": 100, "caption": "world"},
        ])

    def test_twenty_clip_demo_rerender_and_handoff(self):
        paths = mod.build_demo(self.root / "demo")
        project_path = paths["project"]
        outputs = paths["outputs"]
        project = mod.load_project(project_path)
        self.assertEqual(project["label"], "SELF-AUTHORED SYNTHETIC DEMONSTRATION")
        self.assertEqual(len(project["clips"]), 20)
        self.assertEqual(len({(c["start_ms"], c["end_ms"]) for c in project["clips"]}), 20)
        self.assertEqual({c["source_filename"] for c in project["clips"]}, {"demo_source.mp4"})

        video_paths = [outputs / c["output"] for c in project["clips"]]
        caption_paths = [outputs / c["caption_file"] for c in project["clips"]]
        self.assertTrue(all(mod.probe_playable(p) for p in video_paths))
        self.assertTrue(all(p.is_file() and p.read_text(encoding="utf-8").startswith("1\n00:00:00,000") for p in caption_paths))

        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in video_paths}
        original = next(c for c in project["clips"] if c["id"] == "clip-07")
        mod.edit_clip(project_path, "clip-07", start_ms=original["start_ms"] + 100,
                      end_ms=original["end_ms"] + 100,
                      caption="Edited clip seven caption.")
        reopened = mod.load_project(project_path)
        edited = next(c for c in reopened["clips"] if c["id"] == "clip-07")
        self.assertEqual(edited["revision"], 2)
        self.assertEqual(edited["caption"], "Edited clip seven caption.")
        self.assertEqual(reopened["source"]["sha256"], mod.sha256_file(paths["source"]))

        mod.render_project(project_path, outputs, ["clip-07"])
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in video_paths}
        changed = {name for name in before if before[name] != after[name]}
        self.assertEqual(changed, {"clip-07.mp4"})
        self.assertTrue(all(mod.probe_playable(p) for p in video_paths))

        bundle = mod.export_handoff(project_path, outputs, paths["handoff"])
        self.assertTrue(bundle.is_file())
        with (paths["handoff"] / "clips.csv").open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 20)
        self.assertEqual(rows[6]["caption"], "Edited clip seven caption.")
        self.assertEqual(rows[6]["revision"], "2")
        with zipfile.ZipFile(bundle) as zf:
            names = set(zf.namelist())
        self.assertIn("project.json", names)
        self.assertIn("clips.csv", names)
        self.assertIn("demo_source.mp4", names)
        self.assertEqual(len([n for n in names if n.startswith("clips/") and n.endswith(".mp4")]), 20)
        self.assertEqual(len([n for n in names if n.startswith("captions/") and n.endswith(".srt")]), 20)

    def test_source_hash_change_blocks_render(self):
        demo_dir = self.root / "hash"
        demo_dir.mkdir()
        source = mod.create_demo_source(demo_dir / "demo_source.mp4", seconds=4)
        project = demo_dir / "project.json"
        mod.create_project(source, project, [{"start_ms": 100, "end_ms": 900, "caption": "one"}])
        source.write_bytes(source.read_bytes() + b"tamper")
        with self.assertRaisesRegex(mod.ClipError, "source recording hash changed"):
            mod.render_project(project, demo_dir / "renders")

    def test_bounds_validation(self):
        demo_dir = self.root / "bounds"
        demo_dir.mkdir()
        source = mod.create_demo_source(demo_dir / "demo_source.mp4", seconds=2)
        project = demo_dir / "project.json"
        with self.assertRaises(mod.ClipError):
            mod.create_project(source, project, [{"start_ms": 1000, "end_ms": 3000, "caption": "bad"}])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
