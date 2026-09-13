from support import *


class WuhuQualityFaultTests(WuhuQualityCase):
    def test_fault_injection_localizes_all_required_anomaly_families(self) -> None:
        rows = self.fixture.clean_rows()
        frames = [row for row in rows if row.get("kind") == "frame" and row["episode_index"] == 0]
        videos = [row for row in rows if row.get("kind") == "video" and row["episode_index"] == 0]

        # Frame 1: malformed/non-finite state vector.
        frames[1]["observation.state"][4] = "NaN"
        # Frame 2: wrong action dimension.
        frames[2]["action"] = frames[2]["action"][:-1]
        frames[2]["timestamp"] = 0.25  # 50% interval jitter without crossing the gap threshold.
        # Frame 3: large legal-dimension action excursion and timestamp reversal.
        frames[3]["action"] = [2_000_000_000.0] * 20
        frames[3]["timestamp"] = 0.05
        # Frame 4: order/gap and unknown task.
        frames[4]["frame_index"] = 40
        frames[4]["task_index"] = 999
        # Frame 5: timestamp gap / FPS jitter.
        frames[5]["timestamp"] = 1.5
        # Frame 6: data jitter spike while remaining in range.
        frames[6]["observation.state"] = [1000.0] * 20

        videos[0].update(
            {
                "decode_ok": False,
                "frame_count": 2,
                "fps": 4.0,
                "start_timestamp": 0.5,
                "end_timestamp": 2.0,
                "duration": 1.5,
                "black_ratio": 0.75,
                "flat_ratio": 0.75,
            }
        )
        videos[1].update({"start_timestamp": 0.0, "end_timestamp": 0.2, "duration": 0.2})
        # Remove the third camera entirely, contradicting complete coverage.
        rows.remove(videos[2])

        fault_probe = self.fixture.write_probe(self.base / "faults.jsonl", rows)
        report = wq.inspect_dataset(self.fixture.root, probe_jsonl=fault_probe)
        codes = {issue["code"] for issue in report["issues"]}
        expected = {
            "CONTENT.VECTOR_NONFINITE",
            "CONTENT.VECTOR_DIMENSION",
            "CONTENT.VECTOR_OUT_OF_RANGE",
            "TEMPORAL.TIMESTAMP_REVERSAL",
            "TEMPORAL.FRAME_ORDER_OR_GAP",
            "STRUCTURE.TASK_INDEX_UNKNOWN",
            "TEMPORAL.FRAME_LOSS_GAP",
            "TEMPORAL.FPS_JITTER",
            "TEMPORAL.DATA_JITTER_SPIKE",
            "CONTENT.VIDEO_CORRUPT",
            "TEMPORAL.VIDEO_FRAME_COUNT_MISMATCH",
            "TEMPORAL.VIDEO_FPS_MISMATCH",
            "SYNCHRONIZATION.LATE_OR_EARLY_START",
            "SYNCHRONIZATION.EARLY_OR_LATE_STOP",
            "SYNCHRONIZATION.CLOCK_DRIFT",
            "CONTENT.BLACK_OR_WHITE_FRAMES",
            "CONTENT.FLAT_OR_OCCLUDED_FRAMES",
            "SYNCHRONIZATION.VIDEO_RECORD_MISSING",
            "CAPABILITY.PROBE_VIDEO_COVERAGE",
            "CAPABILITY.PROBE_VISUAL_COVERAGE",
        }
        self.assertTrue(expected.issubset(codes), sorted(expected - codes))
        self.assertFalse(report["coverage_complete"])
        episode = report["episode_scores"][0]
        self.assertLess(episode["quality_score"], 70)
        self.assertEqual("reject", episode["status"])
        localized = [item for item in report["issues"] if item["code"] == "CONTENT.VECTOR_NONFINITE"]
        self.assertEqual(1, len(localized))
        self.assertEqual(1, localized[0]["frame_start"])
        self.assertEqual("observation.state", localized[0]["modality"])

    def test_unsafe_data_template_is_reported_without_escape(self) -> None:
        self.fixture.info["data_path"] = "../outside/episode_{episode_index:06d}.parquet"
        write_json(self.fixture.root / "meta/info.json", self.fixture.info)
        # Build a new probe bound to the changed metadata fingerprint.
        rows = self.fixture.clean_rows()
        rows[0]["dataset_fingerprint"] = self.fixture.fingerprint()
        probe = self.fixture.write_probe(self.base / "unsafe.jsonl", rows)
        report = wq.inspect_dataset(self.fixture.root, probe_jsonl=probe)
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("STRUCTURE.DATA_PATH_INVALID", codes)
        self.assertFalse((self.base / "outside").exists())

    def test_symlinked_output_ancestor_is_rejected_without_touching_target(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        linked = self.base / "linked"
        try:
            linked.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        report = wq.inspect_dataset(self.fixture.root, probe_jsonl=self.probe)
        with self.assertRaisesRegex(wq.QualityError, "real directories"):
            wq.write_report_bundle(self.fixture.root, linked / "reports", report)
        self.assertEqual([], list(outside.iterdir()))

    def test_missing_optional_decoders_are_explicit_capability_failures(self) -> None:
        with mock.patch.object(wq, "_import_pyarrow", return_value=None), mock.patch.object(wq.shutil, "which", return_value=None):
            report = wq.inspect_dataset(self.fixture.root)
        self.assertFalse(report["coverage_complete"])
        self.assertEqual("unavailable", report["capabilities"]["parquet"]["state"])
        self.assertEqual("unavailable", report["capabilities"]["video_container"]["state"])
        codes = {issue["code"] for issue in report["issues"]}
        self.assertIn("CAPABILITY.PYARROW_UNAVAILABLE", codes)
        self.assertIn("CAPABILITY.FFPROBE_UNAVAILABLE", codes)
        self.assertIn("CONTENT.FRAME_RECORDS_UNAVAILABLE", codes)

    def test_probe_declaring_complete_but_missing_frames_is_downgraded(self) -> None:
        rows = self.fixture.clean_rows()
        victim = next(row for row in rows if row.get("kind") == "frame" and row["episode_index"] == 1 and row["frame_index"] == 7)
        rows.remove(victim)
        probe = self.fixture.write_probe(self.base / "partial.jsonl", rows)
        report = wq.inspect_dataset(self.fixture.root, probe_jsonl=probe)
        self.assertEqual("partial", report["capabilities"]["parquet"]["state"])
        self.assertIn("CAPABILITY.PROBE_FRAME_COVERAGE", {issue["code"] for issue in report["issues"]})

    def test_cli_strict_capability_exit_is_three(self) -> None:
        out = self.base / "incomplete-output"
        with mock.patch.object(wq, "_import_pyarrow", return_value=None), mock.patch.object(wq.shutil, "which", return_value=None):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = wq.main(["inspect", str(self.fixture.root), "--out-dir", str(out), "--strict-capabilities"])
        self.assertEqual(3, code)
        self.assertTrue((out / "report.json").is_file())

    def test_frame_spans_are_compressed_and_stable(self) -> None:
        rows = self.fixture.clean_rows()
        for row in rows:
            if row.get("kind") == "frame" and row["episode_index"] == 0 and 2 <= row["frame_index"] <= 5:
                row["action"][0] = "Infinity"
        probe = self.fixture.write_probe(self.base / "span.jsonl", rows)
        report = wq.inspect_dataset(self.fixture.root, probe_jsonl=probe)
        issues = [issue for issue in report["issues"] if issue["code"] == "CONTENT.VECTOR_NONFINITE"]
        self.assertEqual(1, len(issues))
        self.assertEqual(2, issues[0]["frame_start"])
        self.assertEqual(5, issues[0]["frame_end"])
        self.assertEqual(4, issues[0]["occurrences"])


if __name__ == "__main__":
    unittest.main()
