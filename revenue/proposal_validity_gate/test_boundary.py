from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from . import ContractError, strict_json_loads

ROOT = Path(__file__).resolve().parents[2]
MAX_SAFE_INT = 9_007_199_254_740_991


class ProposalValidityBoundaryTests(unittest.TestCase):
    def _assert_cli_hostile(self, hostile: bytes) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            offer_path = root / "offer.json"
            current_path = root / "current.json"
            offer_path.write_bytes(hostile)
            current_path.write_bytes(b"{}")
            env = dict(os.environ)
            env["PYTHONIOENCODING"] = "utf-8:strict"
            for command in ([sys.executable], [sys.executable, "-O"]):
                proc = subprocess.run(
                    command
                    + [
                        "-m",
                        "revenue.proposal_validity_gate",
                        "compile",
                        "--offer",
                        str(offer_path),
                        "--current",
                        str(current_path),
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=30,
                    env=env,
                )
                output = proc.stdout + proc.stderr
                self.assertEqual(proc.returncode, 2, output)
                self.assertIn("proposal-validity-gate:", proc.stderr)
                self.assertNotIn("Traceback", output)
                self.assertNotIn("ValueError", output)
                self.assertNotIn("UnicodeEncodeError", output)

    def test_safe_integer_boundary_is_runtime_independent(self):
        self.assertEqual(
            strict_json_loads(b'{"value":9007199254740991}')["value"],
            MAX_SAFE_INT,
        )
        self.assertEqual(
            strict_json_loads(b'{"value":-9007199254740991}')["value"],
            -MAX_SAFE_INT,
        )
        with self.assertRaisesRegex(ContractError, "unsafe_integer"):
            strict_json_loads(b'{"value":9007199254740992}')
        with self.assertRaisesRegex(ContractError, "unsafe_integer"):
            strict_json_loads(b'{"value":' + (b"9" * 5000) + b"}")

    def test_surrogate_keys_values_and_duplicate_diagnostics_fail_closed(self):
        for hostile in (
            b'{"\\ud800":1}',
            b'{"value":"\\ud800"}',
            b'{"\\ud800":1,"\\ud800":2}',
        ):
            with self.subTest(hostile=hostile):
                with self.assertRaises(ContractError):
                    strict_json_loads(hostile)
        self.assertEqual(
            strict_json_loads(b'{"emoji":"\\ud83d\\ude00"}')["emoji"],
            "😀",
        )

    def test_deep_json_is_translated_to_contract_error(self):
        hostile = (b"[" * 5000) + b"0" + (b"]" * 5000)
        with self.assertRaisesRegex(ContractError, "invalid_json"):
            strict_json_loads(hostile)

    def test_existing_duplicate_float_and_nonfinite_contract_is_preserved(self):
        with self.assertRaisesRegex(ContractError, "duplicate_json_key"):
            strict_json_loads(b'{"a":1,"a":2}')
        with self.assertRaisesRegex(ContractError, "float_not_allowed"):
            strict_json_loads(b'{"a":1.25}')
        with self.assertRaisesRegex(ContractError, "nonfinite_number"):
            strict_json_loads(b'{"a":NaN}')

    def test_real_cli_huge_integer_is_bounded_normal_and_optimized(self):
        self._assert_cli_hostile(b'{"value":' + (b"9" * 5000) + b"}")

    def test_real_cli_duplicate_surrogate_key_is_ascii_safe(self):
        self._assert_cli_hostile(b'{"\\ud800":1,"\\ud800":2}')


if __name__ == "__main__":
    unittest.main(verbosity=2)
