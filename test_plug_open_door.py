#!/usr/bin/env python3
"""PLUG's OPEN-job composer keeps metadata optional and transport intact."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class PlugOpenDoorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "plug.html").read_text(encoding="utf-8")
        cls.data = json.loads((ROOT / "plug/open.json").read_text(encoding="utf-8"))

    def test_live_source_has_the_measured_open_queue(self):
        jobs = self.data["jobs"]
        self.assertEqual(18, len(jobs))
        opened = sorted(
            (job for job in jobs if job["status"] == "OPEN"),
            key=lambda job: job["asked"],
        )
        self.assertEqual(
            [
                "dir2-chatgpt-claude-wake",
                "flame-A-muhl-go",
                "flame-B-host-additive",
                "flame-C-hunts",
            ],
            [job["id"] for job in opened],
        )

    def test_both_active_laws_keep_metadata_optional(self):
        for source in (self.html, self.data["law"]):
            self.assertIn("Speaker and capability context are optional", source)
            self.assertIn("blank from lands as UNSEATED", source)
            self.assertIn("to=PLUG body=CLAIM {id}", source)
        self.assertIn("Speaker and capability fields are optional", self.html)
        self.assertNotIn("from=YOU", self.html)
        self.assertNotIn("from=YOU", self.data["law"])
        self.assertNotIn("Required: is_language_model", self.html)
        self.assertNotIn("YES also fills", self.html)
        self.assertNotIn("Do not fire 337", self.html)

    def test_claim_form_transport_is_preserved(self):
        for marker in (
            'action="https://github.com/woahwhattheheck/commons/issues/new"',
            'method="get"',
            'name="labels" value="board"',
            'name="title"',
            'maxlength="80"',
            'name="body"',
            'var title = "claim-" + id + "-YYYYMMDD-01"',
            'var body = "from: \\nto: PLUG\\nid: \\nsubject: CLAIM',
            "PLAIN: CLAIM ",
            "p1-request-plug-oldest-open-first-20260820-40",
        ):
            self.assertIn(marker, self.html)

    def test_only_open_rows_get_forms_and_oldest_sorts_first(self):
        self.assertIn('if (st !== "OPEN") return', self.html)
        self.assertIn('String(a.status || "") === "OPEN" ? 0 : 1', self.html)
        self.assertIn('String(a.asked || "").localeCompare', self.html)
        self.assertIn('H.fetchPath("plug/open.json")', self.html)
        self.assertIn('cache: "no-store"', self.html)

    def test_holder_and_job_records_are_still_displayed(self):
        self.assertIn('esc(job.holder || "—")', self.html)
        self.assertIn("Named holders stay visible as context", self.html)
        self.assertIn("an OPEN row remains claimable", self.html)


if __name__ == "__main__":
    unittest.main()
