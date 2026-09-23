import subprocess
import sys
import unittest

from tools.bounded_canonical_json import (
    BoundaryError,
    Limits,
    canonical_bytes,
    loads_strict,
)
from tools.bounded_canonical_json import core


class IntegerLimitClosureTests(unittest.TestCase):
    def assert_code(self, code, fn, *args, **kwargs):
        with self.assertRaises(BoundaryError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def test_supported_custom_ceiling_round_trips(self):
        limits = Limits(max_integer_abs=core.MAX_SUPPORTED_INTEGER_ABS)
        value = core.MAX_SUPPORTED_INTEGER_ABS
        payload = str(value)
        self.assertEqual(payload.encode(), canonical_bytes(value, limits=limits))
        self.assertEqual(value, loads_strict(payload, limits=limits))

    def test_oversized_custom_limit_rejected_before_text_ingress(self):
        huge = 10**5000
        self.assert_code("invalid_limits", Limits, max_integer_abs=huge)
        with self.assertRaises(BoundaryError) as caught:
            loads_strict("1", limits=Limits(max_integer_abs=huge))
        self.assertEqual("invalid_limits", caught.exception.code)

    def test_oversized_custom_limit_rejected_before_direct_object_ingress(self):
        huge = 10**5000
        self.assert_code("invalid_limits", Limits, max_integer_abs=huge)
        with self.assertRaises(BoundaryError) as caught:
            canonical_bytes(huge, limits=Limits(max_integer_abs=huge))
        self.assertEqual("invalid_limits", caught.exception.code)

    def test_supported_custom_ceiling_rejects_oversized_text_before_int(self):
        limits = Limits(max_integer_abs=core.MAX_SUPPORTED_INTEGER_ABS)
        token = "9" * 5000
        self.assert_code("integer_out_of_range", loads_strict, token, limits=limits)

    def test_supported_custom_ceiling_rejects_oversized_direct_int_before_str(self):
        limits = Limits(max_integer_abs=core.MAX_SUPPORTED_INTEGER_ABS)
        huge = 10**5000
        self.assert_code("integer_out_of_range", canonical_bytes, huge, limits=limits)

    def test_optimized_python_runs_same_closure_suite(self):
        if sys.flags.optimize:
            self.skipTest("already optimized")
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-q",
                "test_bounded_canonical_json_giant_int_limit.IntegerLimitClosureTests",
            ],
            cwd=".",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr)


if __name__ == "__main__":
    unittest.main()
