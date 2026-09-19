"""The operator view retains real computations and usable replay inputs."""
from contextlib import redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("petrel_walkthrough", HERE / "walkthrough.py")
walkthrough = importlib.util.module_from_spec(spec)
spec.loader.exec_module(walkthrough)


class WalkthroughTests(unittest.TestCase):
    def test_all_rows_run_and_retain_replayable_inputs(self):
        result = walkthrough.build()
        case, source_blob = walkthrough.load_case()
        self.assertEqual(result["case_source_git_blob"], source_blob)
        self.assertEqual(len(result["stages"]), 6)
        self.assertEqual(len(result["scenarios"]), 7)
        for row in result["stages"] + result["scenarios"]:
            self.assertEqual(case.run(row["ledger"]), row["report"])
        values = [row["report"]["summary"]["release_linked_recovery_minutes"] for row in result["stages"]]
        self.assertEqual(values, [None, None, None, None, 27, 27])

    def test_unknown_is_not_zero_and_text_is_not_interpreted(self):
        self.assertEqual(walkthrough.cell(None), "UNKNOWN")
        self.assertEqual(walkthrough.cell(0), "0")
        self.assertEqual(walkthrough.cell("<tag>|`x`\nnext"), "&lt;tag&gt;&#124;&#96;x&#96; next")

    def test_rendered_walkthrough_retains_its_scope_and_sources(self):
        result = walkthrough.build()
        text = walkthrough.markdown(result)
        self.assertIn("SYNTHETIC REHEARSAL", text)
        self.assertIn("not a fresh service-health check", text)
        self.assertIn("E_BEHAVIOR, E_HEALTH", text)
        self.assertIn(result["case_source_git_blob"], text)
        for value in result["component_bindings"].values():
            self.assertIn(value["git_blob"], text)

    def test_exports_replay_and_refuses_to_replace_an_existing_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "walkthrough"
            self.assertEqual(walkthrough.main(["--output", str(out)]), 0)
            content = (out / "walkthrough.json").read_bytes()
            rendered = (out / "walkthrough.md").read_text()
            self.assertEqual(walkthrough.markdown(json.loads(content)), rendered)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(walkthrough.main(["--output", str(out)]), 2)
            self.assertEqual((out / "walkthrough.json").read_bytes(), content)

    def test_two_executions_are_byte_reproducible(self):
        first, second = walkthrough.build(), walkthrough.build()
        self.assertEqual(first, second)
        self.assertEqual(walkthrough.markdown(first), walkthrough.markdown(second))


if __name__ == "__main__":
    unittest.main()
