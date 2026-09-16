from teaming_conversion_test_support import *


class TeamingConversionIoTests(unittest.TestCase):
    def test_tampered_receipt_fails_exact_integrity(self):
        candidate, evidence, roots, receipt = compile_fixture()
        tampered = copy.deepcopy(receipt)
        tampered["disposition"] = "DECLINED"
        self.assertFalse(
            verify_integrity_bytes(candidate, evidence, roots, canonical_bytes(tampered))
        )

    def test_deterministic_decision_survives_nonsemantic_array_order(self):
        candidate, evidence_bytes, roots, receipt = compile_fixture()
        evidence = parse_json_bytes(evidence_bytes)
        evidence["assets"].reverse()
        evidence["qualification_gates"].reverse()
        reordered_bytes, reordered_roots = build_roots(evidence)
        reordered = compile_historical_bytes(
            candidate, reordered_bytes, reordered_roots, evaluated_at=NOW
        )
        self.assertEqual(receipt["decision_sha256"], reordered["decision_sha256"])

    def test_markdown_labels_historical_and_preserves_authority_ceiling(self):
        _, _, _, receipt = compile_fixture()
        markdown = render_markdown(receipt)
        self.assertIn("Historical integrity only", markdown)
        self.assertIn("grants no contact", markdown)
        self.assertIn(receipt["decision_sha256"], markdown)

    def test_exclusive_pair_refuses_overwrite_and_cleans_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "receipt.json"
            markdown_path = root / "receipt.md"
            markdown_path.write_text("occupied", encoding="utf-8")
            with self.assertRaises(ControlError):
                write_exclusive_pair(json_path, b"{}\n", markdown_path, b"x")
            self.assertFalse(json_path.exists())
            self.assertEqual(markdown_path.read_text(encoding="utf-8"), "occupied")

    def test_input_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            link = root / "link.json"
            target.write_text("{}\n", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(ControlError):
                read_bounded_regular(link)

    def test_fifo_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / "input.fifo"
            os.mkfifo(fifo)
            writer_error: list[BaseException] = []

            def writer() -> None:
                try:
                    fd = os.open(fifo, os.O_WRONLY)
                    os.close(fd)
                except BaseException as exc:  # pragma: no cover - diagnostic only
                    writer_error.append(exc)

            thread = threading.Thread(target=writer, daemon=True)
            thread.start()
            with self.assertRaises(ControlError):
                read_bounded_regular(fifo)
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(writer_error, [])

    def test_cli_history_and_integrity_have_distinct_labels(self):
        candidate, evidence, roots, _ = compile_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path = root / "candidate.json"
            evidence_path = root / "evidence.json"
            roots_path = root / "roots.json"
            receipt_path = root / "receipt.json"
            markdown_path = root / "receipt.md"
            candidate_path.write_bytes(candidate)
            evidence_path.write_bytes(evidence)
            roots_path.write_bytes(roots)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = cli_main(
                    [
                        "compile-history",
                        "--candidate",
                        str(candidate_path),
                        "--evidence",
                        str(evidence_path),
                        "--roots",
                        str(roots_path),
                        "--as-of",
                        ts(NOW),
                        "--json-output",
                        str(receipt_path),
                        "--markdown-output",
                        str(markdown_path),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertIn("HISTORICAL_INTEGRITY_ONLY FOLLOWUP_READY", stdout.getvalue())
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = cli_main(
                    [
                        "verify-integrity",
                        "--candidate",
                        str(candidate_path),
                        "--evidence",
                        str(evidence_path),
                        "--roots",
                        str(roots_path),
                        "--receipt",
                        str(receipt_path),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue().strip(), "HISTORICAL_INTEGRITY_VALID")

    def test_cli_current_has_no_policy_or_roots_selector(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli_main(
                    [
                        "compile-current",
                        "--candidate",
                        "candidate.json",
                        "--evidence",
                        "evidence.json",
                        "--roots",
                        "roots.json",
                        "--json-output",
                        "receipt.json",
                        "--markdown-output",
                        "receipt.md",
                    ]
                )

