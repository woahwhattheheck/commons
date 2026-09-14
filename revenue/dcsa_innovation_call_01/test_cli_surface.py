from .test_support import *  # noqa: F401,F403

class CliTests(unittest.TestCase):
    def test_argument_error_is_json(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["compile-current"])
        self.assertEqual(code, 2)
        payload = json.loads(stderr.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "ValidationError")

    def test_render_acceptance_outputs_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = pathlib.Path(tmp) / "matrix.json"
            md_path = pathlib.Path(tmp) / "matrix.md"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "render-acceptance",
                        "--json-output",
                        str(json_path),
                        "--markdown-output",
                        str(md_path),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertTrue(acceptance.verify_matrix(strict.strict_json_loads(json_path.read_bytes())))
            self.assertIn("PHASE_4", md_path.read_text())


if __name__ == "__main__":
    unittest.main()
