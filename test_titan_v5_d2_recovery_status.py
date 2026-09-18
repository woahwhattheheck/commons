import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
D2_DIR = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/lean-feed-carry-economics"
VALIDATOR_PATH = D2_DIR / "d2_recovery_status.py"
STATUS_PATH = D2_DIR / "D2_RECOVERY_STATUS.json"

_spec = importlib.util.spec_from_file_location("titan_v5_d2_recovery_status", VALIDATOR_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"unable to load {VALIDATOR_PATH}")
validator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validator)


def current_status():
    return validator.load_status(STATUS_PATH)


class TitanV5D2RecoveryStatusTests(unittest.TestCase):
    def test_current_status_is_machine_consistent(self):
        result = validator.validate_status(current_status())
        self.assertTrue(result["valid"])
        self.assertEqual(result["state"], validator.STATE_SOURCE_AUTHENTICATED)
        self.assertTrue(result["source_authority_verified"])
        self.assertTrue(result["execution_inputs_ready"])
        self.assertFalse(result["candidate_build_authorized"])
        self.assertFalse(result["promotion_authorized"])

    def test_root_source_truth_cannot_lag_authenticated_nested_receipt(self):
        status = current_status()
        status["source_authority_verified"] = False
        with self.assertRaisesRegex(
            validator.RecoveryStatusError,
            "root/nested source_authority_verified mismatch",
        ):
            validator.validate_status(status)

    def test_root_input_readiness_cannot_lag_authenticated_sidecars(self):
        status = current_status()
        status["execution_inputs_ready"] = False
        with self.assertRaisesRegex(
            validator.RecoveryStatusError,
            "root/nested execution_inputs_ready mismatch",
        ):
            validator.validate_status(status)

    def test_authenticated_source_cannot_claim_bytes_absent(self):
        status = current_status()
        status["state"] = validator.STATE_SOURCE_ABSENT
        with self.assertRaisesRegex(
            validator.RecoveryStatusError,
            "authenticated source must use D2_SOURCE_AUTHENTICATED",
        ):
            validator.validate_status(status)

    def test_authenticated_source_cannot_retain_pre_recovery_next_step(self):
        status = current_status()
        status["next_step"] = (
            "provide exact D2 archive bytes to this verifier; run official-engine "
            "census/dev/holdout only after source_authority_verified=true"
        )
        with self.assertRaisesRegex(
            validator.RecoveryStatusError,
            "cannot retain the pre-recovery provide-bytes next step",
        ):
            validator.validate_status(status)

    def test_candidate_or_promotion_authority_cannot_be_reminted(self):
        for field in ("candidate_build_authorized", "promotion_authorized"):
            with self.subTest(field=field):
                status = current_status()
                status[field] = True
                with self.assertRaisesRegex(
                    validator.RecoveryStatusError,
                    f"{field} must remain false",
                ):
                    validator.validate_status(status)

    def test_bool_int_alias_is_rejected(self):
        status = current_status()
        status["promotion_authorized"] = 0
        with self.assertRaisesRegex(
            validator.RecoveryStatusError,
            "promotion_authorized must be a JSON boolean",
        ):
            validator.validate_status(status)

    def test_duplicate_keys_and_nonfinite_json_are_rejected(self):
        with self.assertRaisesRegex(validator.RecoveryStatusError, "duplicate JSON key"):
            validator.loads_status('{"schema":"a","schema":"b"}')
        with self.assertRaisesRegex(validator.RecoveryStatusError, "non-finite JSON constant"):
            validator.loads_status('{"x":NaN}')

    def test_optimized_python_runs_same_contract(self):
        if os.environ.get("TITAN_D2_STATUS_OPT_CHILD") == "1":
            return
        env = os.environ.copy()
        env["TITAN_D2_STATUS_OPT_CHILD"] = "1"
        proc = subprocess.run(
            [sys.executable, "-O", str(Path(__file__).resolve())],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertRegex(proc.stdout, r"Ran [1-9][0-9]* tests?")
        self.assertNotIn("FAILED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
