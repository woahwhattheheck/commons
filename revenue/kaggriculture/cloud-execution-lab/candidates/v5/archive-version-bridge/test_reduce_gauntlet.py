import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import reduce_gauntlet as rg


def write_json(path, value):
    Path(path).write_text(json.dumps(value) + "\n", encoding="utf-8")


class ReduceGauntletTests(unittest.TestCase):
    def index(self, base, count=2):
        path = Path(base) / "index.json"
        opponents = []
        for i in range(count):
            opponents.append({
                "id": f"opp{i:03d}",
                "submission_id": i + 1,
                "seed": 1909000000 + i,
                "family": "A" if i % 2 == 0 else "B",
                "kind": "recorded_trace",
                "memberships": [{"group": "current_top30"}],
                "candidate_seat_for_recorded_orientation": i % 2,
            })
        write_json(path, {"opponents": opponents})
        return path, opponents

    def expected_count(self, count, shard, shards):
        return sum(1 for i in range(count) if i % shards == shard)

    def root(
        self,
        base,
        label,
        index,
        *,
        shard=0,
        shards=1,
        selected_fixtures=None,
        suffix="",
    ):
        path = Path(base) / f"{label}-{shard}{suffix}"
        path.mkdir()
        index_obj = json.loads(Path(index).read_text())
        recorded = [
            r for r in index_obj["opponents"]
            if r["kind"] == "recorded_trace"
        ]
        if selected_fixtures is None:
            selected_fixtures = self.expected_count(
                len(recorded),
                shard,
                shards,
            )
        write_json(path / "run.json", {
            "candidate_sha256": rg.EXACT[label],
            "index_sha256": hashlib.sha256(
                Path(index).read_bytes()
            ).hexdigest(),
            "engine": {"engine.py": "b" * 64},
            "evaluator_sha256": "c" * 64,
            "loader_sha256": "d" * 64,
            "selected_fixtures": selected_fixtures,
            "group": "all",
            "shard": shard,
            "shards": shards,
        })
        return path

    def mutate_run(self, root, **updates):
        path = Path(root) / "run.json"
        run = json.loads(path.read_text())
        run.update(updates)
        write_json(path, run)

    def game(
        self,
        root,
        label,
        row,
        seat,
        scores,
        *,
        status="complete",
        steps=719,
        **overrides,
    ):
        record = {
            "opponent": row["id"],
            "submission_id": row["submission_id"],
            "seed": row["seed"],
            "candidate_seat": seat,
            "family": row["family"],
            "kind": "recorded_trace",
            "adaptive": False,
            "recorded_orientation": seat
            == row["candidate_seat_for_recorded_orientation"],
            "memberships": row["memberships"],
            "candidate_sha256": rg.EXACT[label],
            "status": status,
            "scores": scores if status == "complete" else None,
            "steps": steps,
        }
        record.update(overrides)
        write_json(root / f"{row['id']}-p{seat}.json", record)

    def fill_root(
        self,
        root,
        label,
        rows,
        shard,
        shards,
        score_bias=0,
    ):
        selected = [
            row for i, row in enumerate(rows)
            if i % shards == shard
        ]
        for row in selected:
            self.game(
                root,
                label,
                row,
                0,
                [100 + score_bias, 100],
            )
            self.game(
                root,
                label,
                row,
                1,
                [100, 100 + score_bias],
            )

    def test_complete_panel_and_hotspot_ranking(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 2)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.game(a, "v31", rows[0], 0, [110, 100])
            self.game(a, "v31", rows[0], 1, [100, 100])
            self.game(b, "v4", rows[0], 0, [100, 100])
            self.game(b, "v4", rows[0], 1, [100, 100])
            self.game(a, "v31", rows[1], 0, [130, 100])
            self.game(a, "v31", rows[1], 1, [100, 110])
            self.game(b, "v4", rows[1], 0, [100, 100])
            self.game(b, "v4", rows[1], 1, [100, 100])
            report = rg.reduce_roots([a], [b], index=index)
            self.assertTrue(report["panel_complete"])
            self.assertEqual(report["expected_cells"], 4)
            self.assertEqual(report["summary"]["count"], 4)
            self.assertEqual(
                report["regression_hotspots"][0]["opponent"],
                rows[1]["id"],
            )
            self.assertEqual(
                report["regression_hotspots"][0][
                    "margin_delta_v31_minus_v4"
                ],
                30,
            )
            self.assertEqual(
                [r["family"] for r in report["by_family"]],
                ["B", "A"],
            )

    def test_123_recorded_fixtures_infer_246_cells(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 123)
            v31 = [
                self.root(td, "v31", index, shard=0, shards=2),
                self.root(td, "v31", index, shard=1, shards=2),
            ]
            v4 = [
                self.root(td, "v4", index, shard=0, shards=2),
                self.root(td, "v4", index, shard=1, shards=2),
            ]
            report = rg.reduce_roots(v31, v4, index=index)
            self.assertEqual(report["expected_cells"], 246)
            self.assertFalse(
                report["authority"]["panel_topology"][
                    "complete_cross_version_shard_topology"
                ]
            )
            self.assertFalse(report["panel_complete"])

    def test_incomplete_shard_set_cannot_authorize(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 2)
            a = self.root(td, "v31", index, shard=0, shards=2)
            b = self.root(td, "v4", index, shard=0, shards=2)
            self.fill_root(a, "v31", rows, 0, 2)
            self.fill_root(b, "v4", rows, 0, 2)
            report = rg.reduce_roots(
                [a],
                [b],
                index=index,
                expected_cells=4,
            )
            self.assertFalse(report["panel_complete"])
            self.assertFalse(
                report["authority"]["panel_topology"][
                    "complete_cross_version_shard_topology"
                ]
            )

    def test_favorable_subset_override_cannot_authorize(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 2)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.game(a, "v31", rows[0], 0, [110, 100])
            self.game(a, "v31", rows[0], 1, [100, 100])
            self.game(b, "v4", rows[0], 0, [100, 100])
            self.game(b, "v4", rows[0], 1, [100, 100])
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots(
                    [a],
                    [b],
                    index=index,
                    expected_cells=2,
                )

    def test_limit_truncated_receipt_fails_against_authenticated_index(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 4)
            a = self.root(
                td,
                "v31",
                index,
                shard=0,
                shards=2,
                selected_fixtures=1,
            )
            b = self.root(td, "v4", index, shard=0, shards=2)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_extra_opponent_not_in_authenticated_shard_fails(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 2)
            a = self.root(td, "v31", index, shard=0, shards=2)
            b = self.root(td, "v4", index, shard=0, shards=2)
            self.game(a, "v31", rows[1], 0, [100, 100])
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_missing_pair_is_non_authorizing_not_silent(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.game(a, "v31", rows[0], 0, [110, 100])
            report = rg.reduce_roots([a], [b], index=index)
            self.assertFalse(report["panel_complete"])
            self.assertEqual(
                report["missing_v4"],
                [{"opponent": rows[0]["id"], "seat": 0}],
            )

    def test_candidate_hash_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.mutate_run(a, candidate_sha256="0" * 64)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_cross_version_metadata_mismatch_fails_against_index(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.game(a, "v31", rows[0], 0, [110, 100])
            self.game(
                b,
                "v4",
                rows[0],
                0,
                [100, 100],
                family="wrong",
            )
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_same_opponent_seats_must_share_index_authority(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            for root, label in ((a, "v31"), (b, "v4")):
                self.game(root, label, rows[0], 0, [100, 100])
                self.game(
                    root,
                    label,
                    rows[0],
                    1,
                    [100, 100],
                    submission_id=999,
                    family="other",
                    recorded_orientation=rows[0][
                        "candidate_seat_for_recorded_orientation"
                    ] == 0,
                )
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_cell_seed_and_candidate_seat_must_match_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            for field, wrong in (
                ("seed", rows[0]["seed"] + 1),
                ("candidate_seat", 1),
            ):
                with self.subTest(field=field):
                    a = self.root(
                        td,
                        "v31",
                        index,
                        suffix=f"-{field}-a",
                    )
                    b = self.root(
                        td,
                        "v4",
                        index,
                        suffix=f"-{field}-b",
                    )
                    self.game(
                        a,
                        "v31",
                        rows[0],
                        0,
                        [100, 100],
                        **{field: wrong},
                    )
                    with self.assertRaises(rg.ReductionError):
                        rg.reduce_roots([a], [b], index=index)

    def test_cross_version_index_identity_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.mutate_run(b, index_sha256="e" * 64)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_cross_version_engine_identity_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.mutate_run(b, engine={"engine.py": "f" * 64})
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_cross_version_evaluator_identity_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.mutate_run(b, evaluator_sha256="e" * 64)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_cross_version_loader_identity_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.mutate_run(b, loader_sha256="e" * 64)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_duplicate_shard_receipt_fails_without_cell_collision(self):
        with tempfile.TemporaryDirectory() as td:
            index, _rows = self.index(td, 2)
            a0 = self.root(td, "v31", index, shard=0, shards=2)
            duplicate = self.root(
                td,
                "v31",
                index,
                shard=0,
                shards=2,
                suffix="-dup",
            )
            b0 = self.root(td, "v4", index, shard=0, shards=2)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots(
                    [a0, duplicate],
                    [b0],
                    index=index,
                )

    def test_complete_game_wrong_callback_count_fails(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.game(
                a,
                "v31",
                rows[0],
                0,
                [110, 100],
                steps=718,
            )
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_run_bytes_are_parsed_and_hashed_from_same_capture(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.fill_root(a, "v31", rows, 0, 1)
            self.fill_root(b, "v4", rows, 0, 1)
            original = rg._read_regular_bytes
            original_run = (a / "run.json").read_bytes()
            poisoned = False

            def capture_then_poison(path):
                nonlocal poisoned
                raw = original(path)
                path = Path(path)
                if path == a / "run.json" and not poisoned:
                    poisoned = True
                    changed = json.loads(raw)
                    changed["selected_fixtures"] = 999
                    write_json(path, changed)
                return raw

            with mock.patch.object(
                rg,
                "_read_regular_bytes",
                side_effect=capture_then_poison,
            ):
                report = rg.reduce_roots([a], [b], index=index)
            self.assertTrue(report["panel_complete"])
            self.assertEqual(
                report["authority"]["v31_runs"][0]["run_sha256"],
                hashlib.sha256(original_run).hexdigest(),
            )

    def test_cell_capture_is_sha_bound_and_postread_mutation_does_not_change_parse(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.fill_root(a, "v31", rows, 0, 1, score_bias=10)
            self.fill_root(b, "v4", rows, 0, 1)
            target = a / f"{rows[0]['id']}-p0.json"
            original = rg._read_regular_bytes
            original_cell = target.read_bytes()
            poisoned = False

            def capture_then_poison(path):
                nonlocal poisoned
                raw = original(path)
                path = Path(path)
                if path == target and not poisoned:
                    poisoned = True
                    changed = json.loads(raw)
                    changed["scores"] = [9999, 0]
                    write_json(path, changed)
                return raw

            with mock.patch.object(
                rg,
                "_read_regular_bytes",
                side_effect=capture_then_poison,
            ):
                report = rg.reduce_roots([a], [b], index=index)
            self.assertTrue(report["panel_complete"])
            source = report["authority"]["v31_runs"][0][
                "cell_sources"
            ]
            p0 = next(
                item for item in source
                if item["source_file"] == target.name
            )
            self.assertEqual(
                p0["sha256"],
                hashlib.sha256(original_cell).hexdigest(),
            )
            cell = next(
                row
                for row in report["cells"]
                if row["opponent"] == rows[0]["id"]
                and row["seat"] == 0
            )
            self.assertEqual(cell["v31_scores"], [110, 100])

    def test_score_cell_tamper_changes_authority_digest(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.fill_root(a, "v31", rows, 0, 1)
            self.fill_root(b, "v4", rows, 0, 1)
            before = rg.reduce_roots([a], [b], index=index)
            target = a / f"{rows[0]['id']}-p0.json"
            changed = json.loads(target.read_text())
            changed["scores"] = [101, 100]
            write_json(target, changed)
            after = rg.reduce_roots([a], [b], index=index)
            self.assertNotEqual(
                before["authority_sha256"],
                after["authority_sha256"],
            )

    def test_symlinked_evidence_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            self.fill_root(a, "v31", rows, 0, 1)
            self.fill_root(b, "v4", rows, 0, 1)
            target = a / f"{rows[0]['id']}-p0.json"
            real = a / "real.json"
            target.rename(real)
            target.symlink_to(real.name)
            with self.assertRaises(rg.ReductionError):
                rg.reduce_roots([a], [b], index=index)

    def test_cli_partial_writes_report_and_returns_three(self):
        with tempfile.TemporaryDirectory() as td:
            index, rows = self.index(td, 1)
            a = self.root(td, "v31", index)
            b = self.root(td, "v4", index)
            out = Path(td) / "report.json"
            self.game(a, "v31", rows[0], 0, [110, 100])
            self.game(b, "v4", rows[0], 0, [100, 100])
            code = rg.main([
                "--v31-root",
                str(a),
                "--v4-root",
                str(b),
                "--index",
                str(index),
                "--output",
                str(out),
            ])
            self.assertEqual(code, 3)
            self.assertTrue(out.exists())
            report = json.loads(out.read_text())
            self.assertEqual(report["expected_cells"], 2)
            self.assertFalse(report["panel_complete"])


if __name__ == "__main__":
    unittest.main()
