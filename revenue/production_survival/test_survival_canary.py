import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from survival_canary import run_canary


class SurvivalCanaryTest(unittest.TestCase):
    def test_forced_failure_recovers_exactly_once_and_replay_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            intake = root / "intake.json"
            state = root / "state.json"
            receipt = root / "receipt.json"
            intake.write_text(
                json.dumps(
                    {
                        "sentence": (
                            "My agent should record one customer action, but in production "
                            "it retries after a timeout and records the action twice."
                        )
                    }
                ),
                encoding="utf-8",
            )

            first = run_canary(intake, state, receipt)
            second = run_canary(intake, state, receipt)

            self.assertEqual(first["status"], "LANDED")
            self.assertEqual(first["canary"]["external_effect_count"], 1)
            self.assertEqual(first["canary"]["attempts"], 2)
            self.assertEqual(first["canary"]["recovery_result"], "DEDUPED")
            self.assertTrue(first["acceptance"]["replay_deduped"])
            self.assertEqual(
                first["contract"]["window"]["kind"],
                "PUBLIC_EXAMPLE_NOT_CUSTOMER_SLA",
            )
            self.assertEqual(
                first["artifacts"]["schema"],
                "revenue/production_survival/receipt.schema.json",
            )
            self.assertEqual(second["canary"], first["canary"])


if __name__ == "__main__":
    unittest.main()
