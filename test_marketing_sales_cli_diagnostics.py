"""The projection test must fail closed and report the real child diagnostic."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "marketing_sales_projection_test", ROOT / "test_marketing_sales.py"
)
assert SPEC and SPEC.loader
projection_test = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(projection_test)
REAL_RUN = subprocess.run
VALID_LINE = (
    "VALID 1000 research entities 294 GitHub organizations 50 queued; "
    "0 qualified 0 routes 0 sends USD 0 cash"
)


class MarketingSalesCliDiagnosticsTests(unittest.TestCase):
    def exercise_child(self, program: str) -> None:
        """Replace only the executable fixture, retaining the test's run options."""
        def run_fixture(command, **kwargs):
            self.assertEqual(Path(command[1]), ROOT / "host" / "marketing_sales.py")
            self.assertEqual(command[2:], ["validate"])
            return REAL_RUN([sys.executable, "-c", program], **kwargs)

        case = projection_test.MarketingSalesTests(
            "test_checked_in_projection_validates_and_rebuilds_exactly"
        )
        with mock.patch.object(projection_test.subprocess, "run", side_effect=run_fixture):
            case.test_checked_in_projection_validates_and_rebuilds_exactly()

    def test_nonzero_child_reports_stderr_even_with_success_shaped_stdout(self):
        diagnostic = "pipeline seed audit differs from canonical sources"
        program = (
            "import sys; "
            f"print({VALID_LINE!r}); "
            f"print({diagnostic!r}, file=sys.stderr); sys.exit(7)"
        )
        with self.assertRaises(AssertionError) as caught:
            self.exercise_child(program)
        message = str(caught.exception)
        self.assertIn("code 7", message)
        self.assertIn(diagnostic, message)
        self.assertIn(VALID_LINE, message)

    def test_silent_nonzero_child_still_reports_exit_status(self):
        with self.assertRaises(AssertionError) as caught:
            self.exercise_child("import sys; sys.exit(3)")
        self.assertIn("code 3", str(caught.exception))
        self.assertIn("stderr:", str(caught.exception))

    def test_successful_valid_child_still_passes(self):
        self.exercise_child(f"print({VALID_LINE!r})")

    def test_zero_exit_with_invalid_stdout_still_fails(self):
        with self.assertRaises(AssertionError):
            self.exercise_child("print('not a validation receipt')")

    def test_validation_subprocess_is_bounded_and_captured(self):
        completed = subprocess.CompletedProcess([], 0, VALID_LINE + "\n", "")
        case = projection_test.MarketingSalesTests(
            "test_checked_in_projection_validates_and_rebuilds_exactly"
        )
        with mock.patch.object(projection_test.subprocess, "run", return_value=completed) as run:
            case.test_checked_in_projection_validates_and_rebuilds_exactly()
        options = run.call_args.kwargs
        self.assertEqual(options.get("timeout"), 30)
        self.assertIs(options.get("check"), False)
        self.assertIs(options.get("capture_output"), True)
        self.assertIs(options.get("text"), True)
        self.assertEqual(options.get("cwd"), ROOT)


if __name__ == "__main__":
    unittest.main()
