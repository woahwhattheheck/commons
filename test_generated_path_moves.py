import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SCRIPT = HERE / "host" / "generated_path_moves.py"

from host.generated_path_moves import SCHEMA, classify_paths, generated_kind


class GeneratedPathMovesTests(unittest.TestCase):
    def test_projection_pending_is_generated(self):
        self.assertEqual(generated_kind("projection/pending/abc.json"), "projection")

    def test_projection_converged_is_generated(self):
        self.assertEqual(generated_kind("projection/converged/abc.json"), "projection")

    def test_board_feed_is_generated(self):
        for path in ("feed/github.json", "feed/head.json", "feed/window.json"):
            self.assertEqual(generated_kind(path), "board_ingest")

    def test_manual_rebuild_is_generated(self):
        self.assertEqual(generated_kind("ground/MANUAL.md"), "manual_rebuild")

    def test_similar_names_are_not_generated(self):
        for path in (
            "feed/github.json.bak",
            "ground/MANUAL.md.extra",
            "projection/pendingness/x.json",
            "host/projection/pending/x.json",
        ):
            self.assertIsNone(generated_kind(path))

    def test_generated_only_receipt_is_sorted_and_stable(self):
        got = classify_paths(
            ["ground/MANUAL.md", "projection/pending/z.json", "feed/github.json"]
        )
        self.assertEqual(got["schema"], SCHEMA)
        self.assertEqual(got["disposition"], "generated_only")
        self.assertEqual(got["generated_path_count"], 3)
        self.assertEqual(got["feature_path_count"], 0)
        self.assertEqual(got["generated_kinds"], ["board_ingest", "manual_rebuild", "projection"])
        self.assertEqual(got["generated_paths"], sorted(got["generated_paths"]))

    def test_board_rebuild_with_source_change_is_mixed(self):
        got = classify_paths(["tools.json", "feed/github.json", "ground/MANUAL.md"])
        self.assertEqual(got["disposition"], "mixed")
        self.assertEqual(got["generated_path_count"], 2)
        self.assertEqual(got["feature_paths"], ["tools.json"])

    def test_feature_only_is_feature(self):
        got = classify_paths(["host/example.py", "test_example.py"])
        self.assertEqual(got["disposition"], "feature")
        self.assertEqual(got["generated_path_count"], 0)
        self.assertEqual(got["feature_path_count"], 2)

    def test_duplicate_is_rejected_before_indexing(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            classify_paths(["feed/head.json", "feed/head.json"])

    def test_empty_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            classify_paths([])

    def test_string_instead_of_iterable_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "not one string"):
            classify_paths("feed/head.json")

    def test_noncanonical_or_typed_paths_are_rejected(self):
        bad = [
            1,
            True,
            "",
            " feed/head.json",
            "/feed/head.json",
            "feed//head.json",
            "feed/../head.json",
            "feed\\head.json",
            "feed/head.json/",
        ]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    classify_paths([value])

    def test_cli_executes_committed_script_path(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertEqual(SCRIPT.relative_to(HERE).as_posix(), "host/generated_path_moves.py")

    def test_cli_emits_machine_stable_json(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "projection/pending/a.json",
                "host/x.py",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        got = json.loads(proc.stdout)
        self.assertEqual(got["disposition"], "mixed")
        self.assertEqual(got["generated_paths"], ["projection/pending/a.json"])
        self.assertEqual(got["feature_paths"], ["host/x.py"])


if __name__ == "__main__":
    unittest.main()
