# SPDX-License-Identifier: Apache-2.0
"""Adversarial contracts for the exact joint transition oracle."""
from test_support import *  # noqa: F403


class JointTransitionContracts(unittest.TestCase):
    def test_032_cli_returns_three_for_failed_protection(self):
            value = payload(
                own_shed={"WHEAT": 1}, baseline=[], candidate=[["SELL", "WHEAT", 1]],
                checkpoints=[{
                    "name": "cash-must-not-change", "baseline_stage": "post_town",
                    "candidate_stage": "post_town", "paths": ["/state/farms/0/money"],
                }],
            )
            with tempfile.TemporaryDirectory() as directory:
                directory = Path(directory)
                input_path = directory / "input.json"
                output_path = directory / "output.json"
                input_path.write_text(json.dumps(value), encoding="utf-8")
                completed = subprocess.run([
                    sys.executable, str(Path(__file__).with_name("joint_transition.py")),
                    "--engine-source", str(ENGINE_SOURCE), "--input", str(input_path),
                    "--output", str(output_path), "--deadline-seconds", "5",
                ], check=False, capture_output=True, text=True)
                self.assertEqual(completed.returncode, 3, completed.stderr)
                report = json.loads(output_path.read_text(encoding="utf-8"))
                self.assertEqual(report["comparison"]["protection"]["status"], "HOLD")

    def test_033_cli_returns_zero_for_exact_pass(self):
            value = payload(checkpoints=[{
                "name": "unchanged-empty-state", "baseline_stage": "post_town",
                "candidate_stage": "post_town", "paths": ["/state/farms/0/money", "/state/market/inventory"],
            }])
            with tempfile.TemporaryDirectory() as directory:
                directory = Path(directory)
                input_path = directory / "input.json"
                output_path = directory / "output.json"
                input_path.write_text(json.dumps(value), encoding="utf-8")
                completed = subprocess.run([
                    sys.executable, str(Path(__file__).with_name("joint_transition.py")),
                    "--engine-source", str(ENGINE_SOURCE), "--input", str(input_path),
                    "--output", str(output_path),
                ], check=False, capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(output_path.read_text())["status"], "complete_conditional")

