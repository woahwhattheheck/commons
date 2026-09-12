# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import gzip
import io
from pathlib import Path
import tarfile
import unittest

import paired


def pack(rows):
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            for name, data in rows:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


class PairedRunnerPureContracts(unittest.TestCase):
    def test_archive_parser_requires_main_and_source_and_rejects_unsafe_names(self):
        good = pack([
            ("main.py", b"print('x')\n"),
            ("SOURCE.json", b"{}\n"),
            ("reference/titan-current/redundant_hire.py", b"x=1\n"),
        ])
        rows = paired.archive_members(good)
        self.assertEqual(rows["main.py"], b"print('x')\n")
        self.assertIn("reference/titan-current/redundant_hire.py", rows)

        for name in ("../escape", "/absolute", "a\\b"):
            with self.subTest(name=name):
                bad = pack([
                    ("main.py", b"x"),
                    ("SOURCE.json", b"{}"),
                    (name, b"bad"),
                ])
                with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
                    paired.archive_members(bad)

    def test_archive_parser_rejects_duplicate_member(self):
        duplicate = pack([
            ("main.py", b"one"),
            ("SOURCE.json", b"{}"),
            ("main.py", b"two"),
        ])
        with self.assertRaisesRegex(ValueError, "unsafe or duplicate"):
            paired.archive_members(duplicate)

    def test_summary_separates_all_and_opponent_engagement(self):
        cells = [
            {
                "opponent": "apex_v7",
                "status": "complete_pair",
                "engaged": True,
                "score_delta": {"own": 3, "rival": -2, "margin": 5},
            },
            {
                "opponent": "apex_v7",
                "status": "complete_pair",
                "engaged": False,
                "score_delta": {"own": 0, "rival": 0, "margin": 0},
            },
            {
                "opponent": "arlene_v14",
                "status": "incomplete_pair",
                "engaged": None,
                "score_delta": None,
            },
        ]
        summary = paired.summarize(cells)
        self.assertEqual(summary["all"]["pairs"], 3)
        self.assertEqual(summary["all"]["complete_pairs"], 2)
        self.assertEqual(summary["all"]["engaged_pairs"], 1)
        self.assertEqual(summary["all"]["cold_pairs"], 1)
        self.assertEqual(summary["all"]["mean_margin_delta"], 2.5)
        self.assertEqual(summary["all"]["engaged_mean_margin_delta"], 5)
        self.assertEqual(summary["apex_v7"]["margin_improved"], 1)
        self.assertEqual(summary["apex_v7"]["margin_unchanged"], 1)
        self.assertEqual(summary["arlene_v14"]["complete_pairs"], 0)

    def test_candidate_and_opponent_execution_never_uses_public_evidence_root(self):
        source = Path(paired.__file__).read_text(encoding="utf-8")
        self.assertIn(
            'private_runtime = tempfile.TemporaryDirectory(',
            source,
        )
        self.assertIn(
            'runtime[opponent] = private_root / "opponents" / opponent',
            source,
        )
        self.assertIn(
            'prefix=f"{cell_id}-{arm}-", dir=private_root',
            source,
        )
        self.assertIn(
            'shutil.copytree(snapshot_root, output / ".harness-snapshot")',
            source,
        )
        self.assertNotIn('runtime[opponent] = output / "opponents" / opponent', source)
        self.assertNotIn('prefix=f"{cell_id}-{arm}-", dir=output', source)
        self.assertIn('"public_harness_copy": "evidence_only_never_executed"', source)
        self.assertIn('"engine_root": "external_verified_path_pending_shared_private_ingest"', source)

    def test_authority_constants_match_merged_sources(self):
        self.assertEqual(
            paired.HELPER_GIT_BLOB,
            "fbc5e320b8a2ee63af11dc9856c956a679823409",
        )
        self.assertEqual(paired.ARMS, ("control", "e20_detour_off"))
        self.assertEqual(len(paired.DEFAULT_SEEDS), 16)
        self.assertEqual(len(set(paired.DEFAULT_SEEDS)), 16)


if __name__ == "__main__":
    unittest.main()
