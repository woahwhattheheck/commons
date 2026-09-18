from teaming_conversion_test_support import *

import subprocess
import sys


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

    def test_strict_json_normalizes_resource_errors_and_non_scalar_unicode(self):
        huge_integer = b'{"n":' + (b"9" * 5000) + b"}\n"
        nested = (b"[" * 2000) + (b"]" * 2000) + b"\n"
        with self.assertRaises(ControlError):
            parse_json_bytes(huge_integer)
        with self.assertRaises(ControlError):
            parse_json_bytes(nested)
        with self.assertRaises(ControlError):
            canonical_bytes({"bad": "\ud800"})

    def test_historical_clis_fail_closed_on_hostile_valid_json_normal_and_optimized(self):
        candidate, evidence, roots, receipt = compile_fixture()
        del candidate
        hostile_inputs = {
            "surrogate": b'{"schema":"\\ud800"}\n',
            "huge-int": b'{"n":' + (b"9" * 5000) + b"}\n",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path = root / "candidate.json"
            evidence_path = root / "evidence.json"
            roots_path = root / "roots.json"
            receipt_path = root / "receipt.json"
            evidence_path.write_bytes(evidence)
            roots_path.write_bytes(roots)
            receipt_path.write_bytes(canonical_bytes(receipt))

            for optimize in (False, True):
                for label, hostile in hostile_inputs.items():
                    candidate_path.write_bytes(hostile)
                    json_output = root / f"{label}-{int(optimize)}.json"
                    markdown_output = root / f"{label}-{int(optimize)}.md"
                    prefix = [sys.executable]
                    if optimize:
                        prefix.append("-O")
                    compile_result = subprocess.run(
                        [
                            *prefix,
                            "-m",
                            "revenue.teaming_conversion.cli",
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
                            str(json_output),
                            "--markdown-output",
                            str(markdown_output),
                        ],
                        cwd=Path(__file__).resolve().parent,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    self.assertEqual(
                        compile_result.returncode,
                        2,
                        (optimize, label, compile_result.stdout, compile_result.stderr),
                    )
                    self.assertIn("ERROR:", compile_result.stderr)
                    self.assertNotIn("Traceback", compile_result.stderr)
                    self.assertEqual(compile_result.stdout, "")
                    self.assertFalse(json_output.exists())
                    self.assertFalse(markdown_output.exists())

                    verify_result = subprocess.run(
                        [
                            *prefix,
                            "-m",
                            "revenue.teaming_conversion.cli",
                            "verify-integrity",
                            "--candidate",
                            str(candidate_path),
                            "--evidence",
                            str(evidence_path),
                            "--roots",
                            str(roots_path),
                            "--receipt",
                            str(receipt_path),
                        ],
                        cwd=Path(__file__).resolve().parent,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False,
                    )
                    self.assertEqual(
                        verify_result.returncode,
                        2,
                        (optimize, label, verify_result.stdout, verify_result.stderr),
                    )
                    self.assertIn("ERROR:", verify_result.stderr)
                    self.assertNotIn("Traceback", verify_result.stderr)
                    self.assertEqual(verify_result.stdout, "")

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
