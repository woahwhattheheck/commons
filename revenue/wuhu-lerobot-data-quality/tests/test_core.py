from support import *


class WuhuQualityCoreTests(WuhuQualityCase):
    def test_clean_probe_is_complete_deterministic_and_high_scoring(self) -> None:
        first = wq.inspect_dataset(self.fixture.root, probe_jsonl=self.probe)
        second = wq.inspect_dataset(self.fixture.root, probe_jsonl=self.probe)
        self.assertEqual(wq.canonical_json_bytes(first), wq.canonical_json_bytes(second))
        self.assertTrue(first["coverage_complete"])
        self.assertEqual({"critical": 0, "error": 0, "warning": 0, "info": 0}, first["issue_counts"])
        self.assertEqual(100.0, first["overall"]["quality_score"])
        self.assertGreaterEqual(first["overall"]["training_value_score"], 90.0)
        self.assertEqual(64, len(first["dataset"]["fingerprint"]))
        self.assertEqual(64, len(first["report_digest"]))

    def test_inspection_is_read_only_and_reports_write_outside_dataset(self) -> None:
        before = dataset_snapshot(self.fixture.root)
        report = wq.inspect_dataset(self.fixture.root, probe_jsonl=self.probe)
        self.assertEqual(before, dataset_snapshot(self.fixture.root))
        paths = wq.write_report_bundle(self.fixture.root, self.base / "reports/out", report)
        self.assertEqual(before, dataset_snapshot(self.fixture.root))
        self.assertEqual({"json", "markdown", "html", "issues"}, set(paths))
        for path in paths.values():
            self.assertTrue(path.is_file())
        loaded = json.loads(paths["json"].read_text(encoding="utf-8"))
        self.assertEqual(report["report_digest"], loaded["report_digest"])
        self.assertIn("LeRobot v2.1", paths["markdown"].read_text(encoding="utf-8"))
        self.assertIn("Canonical JSON", paths["html"].read_text(encoding="utf-8"))

    def test_probe_bundle_round_trip_replays_identically(self) -> None:
        sink = wq.IssueSink()
        context = wq.load_context(self.fixture.root, wq.Config(), sink)
        loaded = wq.load_probe(self.probe, context, sink)
        replay_path = wq.write_probe_bundle(self.fixture.root, self.base / "captured/replay.jsonl", context, loaded)
        original_report = wq.inspect_dataset(self.fixture.root, probe_jsonl=self.probe)
        replay_report = wq.inspect_dataset(self.fixture.root, probe_jsonl=replay_path)
        self.assertEqual(wq.canonical_json_bytes(original_report), wq.canonical_json_bytes(replay_report))
        rows = wq.load_jsonl_strict(replay_path)
        self.assertEqual(wq.PROBE_SCHEMA, rows[0]["schema_version"])
        self.assertEqual(self.fixture.fingerprint(), rows[0]["dataset_fingerprint"])

    def test_probe_fingerprint_mismatch_fails_closed(self) -> None:
        rows = self.fixture.clean_rows()
        rows[0]["dataset_fingerprint"] = "0" * 64
        mismatch = self.fixture.write_probe(self.base / "mismatch.jsonl", rows)
        with self.assertRaisesRegex(wq.QualityError, "fingerprint"):
            wq.inspect_dataset(self.fixture.root, probe_jsonl=mismatch)

    def test_duplicate_json_key_is_rejected(self) -> None:
        info_path = self.fixture.root / "meta/info.json"
        info_path.write_text('{"codebase_version":"v2.1","codebase_version":"v3.0"}\n', encoding="utf-8")
        with self.assertRaisesRegex(wq.QualityError, "duplicate JSON key"):
            wq.inspect_dataset(self.fixture.root, probe_jsonl=self.probe)

    def test_output_below_dataset_is_rejected(self) -> None:
        report = wq.inspect_dataset(self.fixture.root, probe_jsonl=self.probe)
        with self.assertRaisesRegex(wq.QualityError, "outside"):
            wq.write_report_bundle(self.fixture.root, self.fixture.root / "report", report)

    def test_html_escapes_untrusted_task_text(self) -> None:
        malicious = '<script>alert("x")</script>'
        write_jsonl(self.fixture.root / "meta/tasks.jsonl", [{"task_index": 0, "task": malicious}])
        write_jsonl(
            self.fixture.root / "meta/episodes.jsonl",
            [
                {"episode_index": episode, "tasks": [malicious], "length": self.fixture.length}
                for episode in range(self.fixture.episodes)
            ],
        )
        rows = self.fixture.clean_rows()
        rows[0]["dataset_fingerprint"] = self.fixture.fingerprint()
        probe = self.fixture.write_probe(self.base / "escaped.jsonl", rows)
        report = wq.inspect_dataset(self.fixture.root, probe_jsonl=probe)
        rendered = wq.report_html(report)
        self.assertNotIn(malicious, rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_cli_writes_bundle_and_has_stable_exit_contract(self) -> None:
        out = self.base / "cli-output"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = wq.main(
                [
                    "inspect",
                    str(self.fixture.root),
                    "--probe-jsonl",
                    str(self.probe),
                    "--out-dir",
                    str(out),
                    "--strict-capabilities",
                    "--fail-on",
                    "critical",
                ]
            )
        self.assertEqual(0, code, stderr.getvalue())
        receipt = json.loads(stdout.getvalue())
        self.assertTrue(receipt["coverage_complete"])
        self.assertEqual(64, len(receipt["report_digest"]))
        self.assertTrue((out / "report.json").is_file())
        self.assertTrue((out / "report.md").is_file())
        self.assertTrue((out / "report.html").is_file())
        self.assertTrue((out / "issues.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
