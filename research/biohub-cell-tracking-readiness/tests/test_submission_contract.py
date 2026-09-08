from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from submission_contract import COLUMNS, SubmissionError, validate_rows, validate_submission, write_submission
from synthetic_baseline import build_rows, link_nearest, synthetic_frames


class SubmissionContractTests(unittest.TestCase):
    def test_synthetic_baseline_is_deterministic_and_valid(self) -> None:
        rows_a = build_rows()
        rows_b = build_rows()
        self.assertEqual(rows_a, rows_b)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "submission.csv"
            write_submission(path, rows_a)
            counts = validate_submission(path, expected_datasets=["synthetic_embryo_0001"], require_consecutive_edges=True)
        self.assertEqual(counts, {"rows": 16, "nodes": 9, "edges": 7, "datasets": 1, "divisions": 1})

    def test_linker_uses_physical_scale_and_links_every_track(self) -> None:
        nodes, edges = link_nearest(synthetic_frames(), radius_um=8.5)
        self.assertEqual(len(nodes), 9)
        self.assertEqual(len(edges), 7)
        self.assertEqual(edges, [(0, 2), (1, 3), (2, 4), (3, 5), (4, 6), (5, 8), (4, 7)])
        self.assertEqual(sum(1 for source_id, _ in edges if source_id == 4), 2)

    def test_missing_dataset_is_rejected(self) -> None:
        rows = []
        with self.assertRaisesRegex(SubmissionError, "missing datasets"):
            validate_rows(rows, expected_datasets=["wanted"])

    def test_whitespace_padded_dataset_is_rejected(self) -> None:
        rows = [
            {"id": "0", "dataset": " d", "row_type": "node", "node_id": "0", "t": "0", "z": "0", "y": "0", "x": "0", "source_id": "-1", "target_id": "-1"},
        ]
        with self.assertRaisesRegex(SubmissionError, "dataset must not contain leading or trailing whitespace"):
            validate_rows(rows)

    def test_whitespace_padded_row_type_is_rejected(self) -> None:
        rows = [
            {"id": "0", "dataset": "d", "row_type": "node ", "node_id": "0", "t": "0", "z": "0", "y": "0", "x": "0", "source_id": "-1", "target_id": "-1"},
        ]
        with self.assertRaisesRegex(SubmissionError, "row_type must not contain leading or trailing whitespace"):
            validate_rows(rows)

    def test_edge_missing_node_is_rejected(self) -> None:
        rows = [
            {"id": "0", "dataset": "d", "row_type": "node", "node_id": "1", "t": "0", "z": "1", "y": "1", "x": "1", "source_id": "-1", "target_id": "-1"},
            {"id": "1", "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "-1", "z": "-1", "y": "-1", "x": "-1", "source_id": "1", "target_id": "2"},
        ]
        with self.assertRaisesRegex(SubmissionError, "missing target node"):
            validate_rows(rows)

    def test_reverse_time_edge_is_rejected(self) -> None:
        rows = [
            {"id": "0", "dataset": "d", "row_type": "node", "node_id": "1", "t": "1", "z": "1", "y": "1", "x": "1", "source_id": "-1", "target_id": "-1"},
            {"id": "1", "dataset": "d", "row_type": "node", "node_id": "2", "t": "0", "z": "1", "y": "1", "x": "1", "source_id": "-1", "target_id": "-1"},
            {"id": "2", "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "-1", "z": "-1", "y": "-1", "x": "-1", "source_id": "1", "target_id": "2"},
        ]
        with self.assertRaisesRegex(SubmissionError, "move forward in time"):
            validate_rows(rows)

    def test_skipped_frame_edge_is_rejected_by_default(self) -> None:
        rows = [
            {"id": "0", "dataset": "d", "row_type": "node", "node_id": "1", "t": "0", "z": "1", "y": "1", "x": "1", "source_id": "-1", "target_id": "-1"},
            {"id": "1", "dataset": "d", "row_type": "node", "node_id": "2", "t": "2", "z": "1", "y": "1", "x": "1", "source_id": "-1", "target_id": "-1"},
            {"id": "2", "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "-1", "z": "-1", "y": "-1", "x": "-1", "source_id": "1", "target_id": "2"},
        ]
        with self.assertRaisesRegex(SubmissionError, "consecutive frames"):
            validate_rows(rows)

    def test_more_than_one_parent_is_rejected(self) -> None:
        rows = [
            {"id": "0", "dataset": "d", "row_type": "node", "node_id": "0", "t": "0", "z": "0", "y": "0", "x": "0", "source_id": "-1", "target_id": "-1"},
            {"id": "1", "dataset": "d", "row_type": "node", "node_id": "1", "t": "0", "z": "0", "y": "1", "x": "0", "source_id": "-1", "target_id": "-1"},
            {"id": "2", "dataset": "d", "row_type": "node", "node_id": "2", "t": "1", "z": "0", "y": "2", "x": "0", "source_id": "-1", "target_id": "-1"},
            {"id": "3", "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "-1", "z": "-1", "y": "-1", "x": "-1", "source_id": "0", "target_id": "2"},
            {"id": "4", "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "-1", "z": "-1", "y": "-1", "x": "-1", "source_id": "1", "target_id": "2"},
        ]
        with self.assertRaisesRegex(SubmissionError, "more than one parent"):
            validate_rows(rows)

    def test_more_than_two_children_is_rejected(self) -> None:
        rows = [
            {"id": "0", "dataset": "d", "row_type": "node", "node_id": "0", "t": "0", "z": "0", "y": "0", "x": "0", "source_id": "-1", "target_id": "-1"},
        ]
        for i in range(1, 4):
            rows.append({"id": str(len(rows)), "dataset": "d", "row_type": "node", "node_id": str(i), "t": "1", "z": "0", "y": str(i), "x": "0", "source_id": "-1", "target_id": "-1"})
        for i in range(1, 4):
            rows.append({"id": str(len(rows)), "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "-1", "z": "-1", "y": "-1", "x": "-1", "source_id": "0", "target_id": str(i)})
        with self.assertRaisesRegex(SubmissionError, "more than two children"):
            validate_rows(rows)


    def test_duplicate_edge_is_rejected(self) -> None:
        rows = [
            {"id": "0", "dataset": "d", "row_type": "node", "node_id": "0", "t": "0", "z": "0", "y": "0", "x": "0", "source_id": "-1", "target_id": "-1"},
            {"id": "1", "dataset": "d", "row_type": "node", "node_id": "1", "t": "1", "z": "0", "y": "1", "x": "0", "source_id": "-1", "target_id": "-1"},
            {"id": "2", "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "-1", "z": "-1", "y": "-1", "x": "-1", "source_id": "0", "target_id": "1"},
            {"id": "3", "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "-1", "z": "-1", "y": "-1", "x": "-1", "source_id": "0", "target_id": "1"},
        ]
        with self.assertRaisesRegex(SubmissionError, "duplicate edge"):
            validate_rows(rows)

    def test_csv_round_trip_is_byte_deterministic(self) -> None:
        rows = build_rows()
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.csv"
            second = Path(tmp) / "second.csv"
            write_submission(first, rows)
            with first.open("r", encoding="utf-8", newline="") as handle:
                parsed = list(csv.DictReader(handle))
            write_submission(second, parsed)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                validate_submission(second, expected_datasets=["synthetic_embryo_0001"], require_consecutive_edges=True),
                {"rows": 16, "nodes": 9, "edges": 7, "datasets": 1, "divisions": 1},
            )

    def test_node_and_edge_sentinels_are_rejected(self) -> None:
        bad_node = [
            {"id": "0", "dataset": "d", "row_type": "node", "node_id": "0", "t": "0", "z": "0", "y": "0", "x": "0", "source_id": "0", "target_id": "-1"},
        ]
        with self.assertRaisesRegex(SubmissionError, "node source_id must be -1"):
            validate_rows(bad_node)

        bad_edge = [
            {"id": "0", "dataset": "d", "row_type": "edge", "node_id": "-1", "t": "0", "z": "-1", "y": "-1", "x": "-1", "source_id": "0", "target_id": "1"},
        ]
        with self.assertRaisesRegex(SubmissionError, "edge t must be -1"):
            validate_rows(bad_edge)

    def test_header_must_be_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(COLUMNS[:-1])
            with self.assertRaisesRegex(SubmissionError, "header must exactly equal"):
                validate_submission(path)


if __name__ == "__main__":
    unittest.main()
