import subprocess
import sys
import unittest
from unittest import mock

from tools.bounded_canonical_json import (
    BoundaryError,
    Limits,
    canonical_bytes,
    canonical_equal,
    canonical_sha256,
    loads_strict,
)
from tools.bounded_canonical_json import core


class _DictSubclass(dict):
    pass


class _ListSubclass(list):
    pass


class BoundedCanonicalJsonTests(unittest.TestCase):
    def assert_code(self, code, fn, *args, **kwargs):
        with self.assertRaises(BoundaryError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def test_canonical_determinism_and_digest(self):
        left = {"z": [3, 2, 1], "a": {"ok": True}}
        right = {"a": {"ok": True}, "z": [3, 2, 1]}
        expected = b'{"a":{"ok":true},"z":[3,2,1]}'
        self.assertEqual(expected, canonical_bytes(left))
        self.assertEqual(expected, canonical_bytes(right))
        self.assertTrue(canonical_equal(left, right))
        self.assertEqual(64, len(canonical_sha256(left)))

    def test_bool_int_artifact_identity_is_type_sensitive(self):
        self.assertEqual(b'{"authority":false}', canonical_bytes({"authority": False}))
        self.assertEqual(b'{"authority":0}', canonical_bytes({"authority": 0}))
        self.assertFalse(canonical_equal({"authority": False}, {"authority": 0}))
        self.assertFalse(canonical_equal({"authority": True}, {"authority": 1}))

    def test_strict_text_duplicate_key_fails(self):
        self.assert_code("duplicate_key", loads_strict, '{"a":1,"a":2}')

    def test_nonfinite_text_and_direct_float_fail(self):
        self.assert_code("nonfinite_number", loads_strict, '{"x":NaN}')
        self.assert_code("nonfinite_number", loads_strict, '{"x":1e999}')
        self.assert_code("nonfinite_number", canonical_bytes, {"x": float("inf")})

    def test_invalid_utf8_and_surrogates_fail(self):
        self.assert_code("invalid_utf8", loads_strict, b'{"x":"\xff"}')
        self.assert_code("invalid_utf8", loads_strict, '{"x":"\ud800"}')
        self.assert_code("invalid_utf8", canonical_bytes, {"\ud800": "x"})
        self.assert_code("invalid_utf8", canonical_bytes, {"x": "\udfff"})

    def test_integer_token_is_bounded_before_builtin_int_limit(self):
        token = "9" * 5000
        self.assert_code("integer_out_of_range", loads_strict, '{"n":' + token + '}')
        self.assert_code("integer_out_of_range", canonical_bytes, {"n": 10**16})

    def test_only_exact_builtin_json_shapes_are_admitted(self):
        self.assert_code("non_plain_json", canonical_bytes, _DictSubclass(a=1))
        self.assert_code("non_plain_json", canonical_bytes, _ListSubclass([1, 2]))
        self.assert_code("non_string_key", canonical_bytes, {1: "x"})

    def test_cycle_fails_before_serializer(self):
        value = []
        value.append(value)
        with mock.patch.object(
            core.json,
            "dumps",
            side_effect=AssertionError("serializer must not run"),
        ):
            self.assert_code("cycle", canonical_bytes, value)

    def test_depth_limit_fails_before_serializer(self):
        value = [[[[0]]]]
        limits = Limits(max_depth=3, max_nodes=100, max_bytes=1024)
        with mock.patch.object(
            core.json,
            "dumps",
            side_effect=AssertionError("serializer must not run"),
        ):
            self.assert_code("too_deep", canonical_bytes, value, limits=limits)

    def test_node_limit_counts_serialized_occurrences(self):
        limits = Limits(max_depth=10, max_nodes=3, max_bytes=1024)
        self.assert_code("too_complex", canonical_bytes, [1, 2, 3], limits=limits)

    def test_dict_cardinality_is_fenced_before_snapshot_work(self):
        limits = Limits(max_depth=10, max_nodes=4, max_bytes=1024)
        with mock.patch.object(
            core.json,
            "dumps",
            side_effect=AssertionError("serializer must not run"),
        ):
            self.assert_code(
                "too_complex",
                canonical_bytes,
                {"a": 1, "b": 2},
                limits=limits,
            )

    def test_single_huge_scalar_is_rejected_before_serializer(self):
        limits = Limits(max_depth=10, max_nodes=100, max_bytes=64)
        value = {"x": "A" * 100}
        with mock.patch.object(
            core.json,
            "dumps",
            side_effect=AssertionError("serializer must not run"),
        ):
            self.assert_code("too_large", canonical_bytes, value, limits=limits)

    def test_shared_long_scalar_alias_amplification_is_charged_each_time(self):
        limits = Limits(max_depth=10, max_nodes=100, max_bytes=128)
        shared = "A" * 20
        value = [shared] * 10
        with mock.patch.object(
            core.json,
            "dumps",
            side_effect=AssertionError("serializer must not run"),
        ):
            self.assert_code("too_large", canonical_bytes, value, limits=limits)

    def test_serializer_reads_detached_snapshot_not_caller_container(self):
        source = {"x": [1]}
        real_dumps = core.json.dumps

        def inspect_and_mutate(value, *args, **kwargs):
            self.assertIsNot(value, source)
            self.assertIsNot(value["x"], source["x"])
            source["x"].append(2)
            return real_dumps(value, *args, **kwargs)

        with mock.patch.object(core.json, "dumps", side_effect=inspect_and_mutate):
            payload = canonical_bytes(source)
        self.assertEqual(b'{"x":[1]}', payload)
        self.assertEqual({"x": [1, 2]}, source)

    def test_strict_text_round_trip_uses_same_direct_object_budget(self):
        limits = Limits(max_depth=10, max_nodes=100, max_bytes=64)
        raw = '{"x":"' + ("A" * 100) + '"}'
        self.assert_code("too_large", loads_strict, raw, limits=limits)

    def test_optimized_python_runs_the_same_hostile_suite(self):
        if sys.flags.optimize:
            self.skipTest("already running under optimized Python")
        proc = subprocess.run(
            [
                sys.executable,
                "-O",
                "-m",
                "unittest",
                "-q",
                "test_bounded_canonical_json.BoundedCanonicalJsonTests",
            ],
            cwd=".",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            0,
            proc.returncode,
            msg="optimized suite failed:\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (proc.stdout, proc.stderr),
        )


if __name__ == "__main__":
    unittest.main()
