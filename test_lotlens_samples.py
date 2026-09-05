#!/usr/bin/env python3
"""The committed sample answers under lotlens/samples/ are what the CLI prints today.

Regenerates each sample from the synthetic fixture and compares: same content_sha256, same
report body apart from the clock fields, same Markdown apart from the Generated line.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLI = ROOT / "lotlens" / "lotlens.py"
FIXTURE = ROOT / "lotlens" / "fixtures" / "synthetic_pilot"
SAMPLES = ROOT / "lotlens" / "samples"
QUERIES = {
    "citric-forward": ["sup-acme/lot/LOT-CITRIC-01"],
    "citric-forward-assumed": ["sup-acme/lot/LOT-CITRIC-01", "--assume", "unlinked_package_same_product_day"],
    "ship3-backward": ["pilot-plant/shipment/SHIP-3", "--backward"],
}


def without_clock(report: dict) -> dict:
    out = json.loads(json.dumps(report))
    out.pop("generated_at", None)
    for imp in out.get("imports", []):
        imp.pop("imported_at", None)
    return out


def without_generated_line(markdown: str) -> str:
    return "\n".join(line for line in markdown.splitlines() if not line.startswith("Generated "))


class SampleAnswersTests(unittest.TestCase):
    def run_cli(self, *args) -> None:
        proc = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd=ROOT, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_every_sample_has_both_files_and_a_readme_row(self):
        readme = (SAMPLES / "README.md").read_text(encoding="utf-8")
        for name in QUERIES:
            self.assertTrue((SAMPLES / f"{name}.json").is_file(), name)
            self.assertTrue((SAMPLES / f"{name}.md").is_file(), name)
            self.assertIn(f"`{name}`", readme)
        extra = {p.stem for p in SAMPLES.glob("*.json")} - set(QUERIES)
        self.assertEqual(extra, set(), "a sample without a query in this test cannot be kept honest")

    def test_samples_are_what_the_cli_prints_today(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            self.run_cli("-w", str(ws), "import", str(FIXTURE), "--label", "pilot")
            for name, args in QUERIES.items():
                fresh_json, fresh_md = Path(tmp) / f"{name}.json", Path(tmp) / f"{name}.md"
                self.run_cli("-w", str(ws), "impact", *args, "--out", str(fresh_json), "--md", str(fresh_md))
                fresh = json.loads(fresh_json.read_text(encoding="utf-8"))
                kept = json.loads((SAMPLES / f"{name}.json").read_text(encoding="utf-8"))
                self.assertEqual(fresh["content_sha256"], kept["content_sha256"], name)
                self.assertEqual(without_clock(fresh), without_clock(kept), name)
                self.assertEqual(
                    without_generated_line(fresh_md.read_text(encoding="utf-8")),
                    without_generated_line((SAMPLES / f"{name}.md").read_text(encoding="utf-8")),
                    name,
                )
                self.assertIn(kept["content_sha256"], (SAMPLES / f"{name}.md").read_text(encoding="utf-8"), "markdown names its own hash")

    def test_samples_show_each_kind_of_statement(self):
        forward = json.loads((SAMPLES / "citric-forward.json").read_text(encoding="utf-8"))["impact"]
        assumed = json.loads((SAMPLES / "citric-forward-assumed.json").read_text(encoding="utf-8"))["impact"]
        backward = json.loads((SAMPLES / "ship3-backward.json").read_text(encoding="utf-8"))["impact"]
        self.assertEqual(forward["counts"]["KNOWN_AFFECTED"], 16)
        self.assertEqual(forward["counts"]["POTENTIALLY_AFFECTED"], 0)
        self.assertEqual(forward["counts"]["coverage_gaps"], 1)
        self.assertEqual(forward["counts"]["contradictions"], 2)
        self.assertEqual(assumed["counts"]["KNOWN_AFFECTED"], 16, "an assumption promotes nothing to known")
        self.assertEqual(assumed["counts"]["POTENTIALLY_AFFECTED"], 2)
        self.assertEqual(assumed["query"]["assumptions"], ["unlinked_package_same_product_day"])
        self.assertEqual(backward["query"]["direction"], "backward")
        self.assertEqual(backward["counts"]["KNOWN_AFFECTED"], 8)
        keys = {a["key"] for a in backward["affected"]}
        self.assertIn("sup-h2o/lot/LOT-WATER-01", keys)
        self.assertIn("sup-aqua/lot/LOT-WATER-01", keys)


if __name__ == "__main__":
    unittest.main()
