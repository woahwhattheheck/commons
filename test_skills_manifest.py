#!/usr/bin/env python3
"""Live skill dirs must be named in skills.json. A missing row is a hole."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / ".agents" / "skills"
MANIFEST = ROOT / "skills.json"
CHECK = ROOT / "skills" / "check.py"

# Originally red on tests.yml run 33190244509 (chargeable-checkout PR #4918):
# skill dirs not in skills.json: ['distribution']. Later peers added more
# live packs without catalog rows; the same check still requires every dir.
PINNED_LIVE_SKILLS = (
    "distribution",
    "feature-tracker",
    "listing-registry",
    "experience-compiler",
)


def live_skill_dirs() -> set[str]:
    return {
        name
        for name in os.listdir(SKILLS)
        if (SKILLS / name).is_dir()
    }


def manifest_ids() -> list[str]:
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))["skills"]
    return [row["id"] for row in rows]


class SkillsManifestTests(unittest.TestCase):
    def test_every_live_skill_dir_is_in_skills_json(self):
        ids = set(manifest_ids())
        dirs = live_skill_dirs()
        self.assertEqual(dirs, ids, "skill dirs not in skills.json: %s" % sorted(dirs - ids))

    def test_chargeable_checkout_era_packs_remain_registered(self):
        ids = set(manifest_ids())
        dirs = live_skill_dirs()
        for sid in PINNED_LIVE_SKILLS:
            self.assertIn(sid, dirs, "live pack vanished: %s" % sid)
            self.assertIn(sid, ids, "live pack unregistered: %s" % sid)
            self.assertTrue((SKILLS / sid / "SKILL.md").is_file(), SKILLS / sid / "SKILL.md")

    def test_skills_check_passes(self):
        result = subprocess.run(
            ["python3", str(CHECK)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("PASS"), result.stdout)

    def test_omitting_distribution_from_a_copy_fails_check(self):
        """Regression: the exact hole from run 33190244509 stays detectable."""
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        payload["skills"] = [row for row in payload["skills"] if row["id"] != "distribution"]
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp)
            (clone / "skills").mkdir()
            (clone / ".agents" / "skills" / "distribution").mkdir(parents=True)
            (clone / ".agents" / "skills" / "distribution" / "SKILL.md").write_text(
                "---\nname: distribution\ndescription: x\n---\n\n# Distribution\n",
                encoding="utf-8",
            )
            (clone / "skills" / "MANUAL.md").write_text("distribution\n", encoding="utf-8")
            (clone / "skills.json").write_text(json.dumps(payload), encoding="utf-8")
            # Point check.py at the clone by copying it; check.py derives ROOT
            # from its own file location, so copy the checker too.
            (clone / "skills" / "check.py").write_text(
                CHECK.read_text(encoding="utf-8"), encoding="utf-8"
            )
            result = subprocess.run(
                ["python3", str(clone / "skills" / "check.py")],
                cwd=clone,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("skill dirs not in skills.json", result.stdout)
        self.assertIn("distribution", result.stdout)


if __name__ == "__main__":
    unittest.main()
