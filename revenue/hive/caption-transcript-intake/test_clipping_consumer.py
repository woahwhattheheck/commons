from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTION_CLI = HERE / "caption_intake.py"
DEMO_VTT = HERE / "examples" / "demo.vtt"
CLIPPING_DIR = HERE.parent / "managed-clipping"
CLIPPING_CLI = CLIPPING_DIR / "managed_clipping.py"


def _run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(arg) for arg in args],
        check=True,
        text=True,
        capture_output=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_source(path: Path, duration: float = 63.0) -> None:
    _run(
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c=black:size=160x90:rate=30:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "35",
        "-c:a", "aac", "-shortest", str(path),
    )


class ClippingConsumerIntegrationTests(unittest.TestCase):
    def test_supplied_captions_drive_six_distinct_clips_and_editable_handoff(self) -> None:
        self.assertTrue(CAPTION_CLI.is_file())
        self.assertTrue(CLIPPING_CLI.is_file())
        self.assertTrue(DEMO_VTT.is_file())

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "synthetic-source.mp4"
            _make_source(source)
            source_hash = _sha256(source)

            bundle = root / "caption-handoff.zip"
            _run(
                sys.executable, CAPTION_CLI, DEMO_VTT,
                "--title", "Fictional clipping handoff",
                "--duration-seconds", "63",
                "--synthetic-demo",
                "--output", bundle,
            )
            with zipfile.ZipFile(bundle) as archive:
                episode_path = root / "episode-import.json"
                episode_path.write_bytes(archive.read("episode-import.json"))
                transcript = json.loads(archive.read("transcript.json"))

            self.assertEqual(len(transcript["segments"]), 6)
            episode = json.loads(episode_path.read_text(encoding="utf-8"))
            self.assertEqual(len(episode["segments"]), 6)
            self.assertTrue(episode["synthetic_demo"])
            self.assertTrue(all(row["verified"] is False for row in episode["segments"]))

            project_path = root / "clipping-project.json"
            init = _run(
                sys.executable, CLIPPING_CLI, "init", source, project_path,
                "--transcript-json", episode_path,
                "--moments", "6",
                "--synthetic-demo",
            )
            self.assertEqual(json.loads(init.stdout)["moments"], 6)
            project = json.loads(project_path.read_text(encoding="utf-8"))
            refs = [moment["transcript_refs"][0] for moment in project["moments"]]
            self.assertEqual(refs, [f"c{i:05d}" for i in range(1, 7)])
            self.assertEqual(len(set(refs)), 6)
            self.assertTrue(all(moment["source_filename"] == source.name for moment in project["moments"]))
            self.assertEqual(project["source"]["sha256"], source_hash)

            edited_caption = "Edited caption retained in the clipping handoff"
            _run(
                sys.executable, CLIPPING_CLI, "edit", project_path, "clip-003",
                "--caption", edited_caption,
                "--hook", "Edited handoff hook",
            )

            renders = root / "renders"
            rendered = _run(sys.executable, CLIPPING_CLI, "render", project_path, renders)
            self.assertEqual(json.loads(rendered.stdout)["rendered"], 6)

            handoff = root / "handoff"
            exported = _run(sys.executable, CLIPPING_CLI, "handoff", project_path, handoff)
            self.assertEqual(json.loads(exported.stdout)["clip_count"], 6)
            self.assertEqual(len(list((handoff / "videos").glob("*.mp4"))), 6)
            self.assertEqual(len(list((handoff / "captions").glob("*.srt"))), 6)

            with (handoff / "clips.csv").open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 6)
            self.assertEqual(rows[2]["clip_id"], "clip-003")
            self.assertEqual(rows[2]["caption"], edited_caption)
            self.assertIn(edited_caption, (handoff / "captions" / "clip-003.srt").read_text(encoding="utf-8"))
            self.assertEqual(_sha256(source), source_hash)


if __name__ == "__main__":
    unittest.main()
