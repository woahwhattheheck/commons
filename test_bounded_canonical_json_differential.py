"""Independent public-API compatibility proof for the bounded JSON primitive.

Run this module with unittest under both normal Python and real ``python -O``.
The deterministic 5,000-case corpus checks this project's documented Python
JSON encoding, not RFC 8785/JCS or cross-language numeric normalization. It does
not replace policy-generation, forged-Limits, or interpreter-boundary tests.

Original library: Sol-Z; integer-limit donor: Z-QuorumForge. This complementary
proof: ZZ-QUARTZLINE / GPT-6 Astra Pro, coordinated on Commons PR #15732.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import struct
import unittest
from functools import lru_cache
from typing import Any

from tools.bounded_canonical_json import (
    BoundaryError,
    Limits,
    canonical_bytes,
    canonical_equal,
    canonical_sha256,
    loads_strict,
)


SEED = 15732
CASE_COUNT = 5000
ALPHABET = ('a', 'Z', '0', '"', '\\', '\0', '\b', '\t', '\n', '\f', '\r',
            '\x1f', '\x7f', '\x80', '\u07ff', '\u0800', '\ud7ff', '\ue000',
            '\uffff', '\U00010000', '\U0010ffff', '\u00e9', 'e\u0301')
FINITE_EDGES = (0.0, -0.0, 0.1, -0.1, 1.0, -1.0, 1e-7, 1e20,
                5e-324, -5e-324, float.fromhex('0x1.fffffffffffffp+1023'))


def reference_bytes(value: Any) -> bytes:
    """Use only the documented standard encoder, not a production helper."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def reference_shape(value: Any, depth: int = 1) -> tuple[int, int]:
    """Independently count serialized occurrences and open-container depth."""
    if type(value) is dict:
        children = [reference_shape(child, depth + 1) for child in value.values()]
        return (1 + len(value) + sum(n for n, _ in children),
                max([depth] + [d for _, d in children]))
    if type(value) is list:
        children = [reference_shape(child, depth + 1) for child in value]
        return (1 + sum(n for n, _ in children),
                max([depth] + [d for _, d in children]))
    return 1, 0


def reverse_mappings(value: Any) -> Any:
    if type(value) is dict:
        return {key: reverse_mappings(value[key]) for key in reversed(value)}
    if type(value) is list:
        return [reverse_mappings(child) for child in value]
    return value


@lru_cache(maxsize=1)
def corpus() -> tuple[Any, ...]:
    rng = random.Random(SEED)

    def make(depth: int = 0) -> Any:
        kind = rng.randrange(8 if depth < 4 else 6)
        if kind == 0:
            return None
        if kind == 1:
            return bool(rng.randrange(2))
        if kind == 2:
            return rng.randint(-(10**15), 10**15)
        if kind == 3:
            return rng.choice(FINITE_EDGES)
        if kind == 4:
            return ''.join(rng.choice(ALPHABET) for _ in range(rng.randrange(12)))
        if kind == 5:
            return rng.uniform(-1e12, 1e12)
        if kind == 6:
            return [make(depth + 1) for _ in range(rng.randrange(5))]
        # Prefixes keep generated keys distinct without normalizing Unicode.
        return {str(i) + rng.choice(ALPHABET): make(depth + 1)
                for i in range(rng.randrange(5))}

    return tuple(make() for _ in range(CASE_COUNT))


def corpus_sha256() -> str:
    digest = hashlib.sha256()
    for value in corpus():
        payload = reference_bytes(value)
        digest.update(len(payload).to_bytes(8, 'big'))
        digest.update(payload)
    return digest.hexdigest()


class BoundedCanonicalJsonDifferentialTests(unittest.TestCase):
    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(BoundaryError) as caught:
            function(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def test_5000_canonical_roundtrip_and_digest_cases(self):
        self.assertEqual(CASE_COUNT, len(corpus()))
        for index, value in enumerate(corpus()):
            with self.subTest(case=index, seed=SEED):
                expected = reference_bytes(value)
                self.assertEqual(expected, canonical_bytes(value))
                self.assertEqual(hashlib.sha256(expected).hexdigest(),
                                 canonical_sha256(value))
                for raw in (expected, expected.decode('utf-8')):
                    self.assertEqual(expected, canonical_bytes(loads_strict(raw)))

    def test_nested_mapping_permutation_is_canonical(self):
        for index, value in enumerate(corpus()[:512]):
            with self.subTest(case=index):
                reversed_value = reverse_mappings(value)
                self.assertEqual(reference_bytes(value), canonical_bytes(reversed_value))
                self.assertTrue(canonical_equal(value, reversed_value))

    def test_byte_budget_has_an_exact_accept_reject_boundary(self):
        for index, value in enumerate(corpus()[:512]):
            expected = reference_bytes(value)
            size = len(expected)
            with self.subTest(case=index, bytes=size):
                exact = Limits(max_bytes=max(2, size))
                self.assertEqual(expected, canonical_bytes(value, limits=exact))
                self.assertEqual(expected, canonical_bytes(loads_strict(expected, limits=exact), limits=exact))
                self.assertEqual(expected, canonical_bytes(loads_strict(expected.decode(), limits=exact), limits=exact))
                if size > 2:
                    tight = Limits(max_bytes=size - 1)
                    self.assert_code('too_large', canonical_bytes, value, limits=tight)
                    self.assert_code('too_large', loads_strict, expected, limits=tight)

    def test_node_budget_counts_keys_values_and_every_alias_occurrence(self):
        shared = {'nested': [False, None, '\U00010000']}
        values = list(corpus()[:512]) + [[shared] * 9, {'a': shared, 'b': shared}]
        for index, value in enumerate(values):
            nodes, _ = reference_shape(value)
            with self.subTest(case=index, nodes=nodes):
                exact = Limits(max_nodes=nodes)
                expected = reference_bytes(value)
                self.assertEqual(expected, canonical_bytes(value, limits=exact))
                self.assertEqual(expected, canonical_bytes(loads_strict(expected, limits=exact), limits=exact))
                if nodes > 1:
                    tight = Limits(max_nodes=nodes - 1)
                    self.assert_code('too_complex', canonical_bytes, value, limits=tight)
                    self.assert_code('too_complex', loads_strict, expected, limits=tight)

    def test_open_container_depth_boundaries(self):
        for container in (lambda child: [child], lambda child: {'x': child}):
            value = 0
            for depth in range(1, 66):
                value = container(value)
                with self.subTest(depth=depth, root_type=type(value).__name__):
                    expected = reference_bytes(value)
                    exact = Limits(max_depth=depth)
                    self.assertEqual(expected, canonical_bytes(value, limits=exact))
                    self.assertEqual(expected, canonical_bytes(loads_strict(expected, limits=exact), limits=exact))
                    if depth > 1:
                        tight = Limits(max_depth=depth - 1)
                        self.assert_code('too_deep', canonical_bytes, value, limits=tight)
                        self.assert_code('too_deep', loads_strict, expected, limits=tight)
        self.assertEqual(b'0', canonical_bytes(0, limits=Limits(max_depth=1)))

    def test_all_ascii_and_unicode_width_boundaries(self):
        points = list(range(128)) + [128, 0x7ff, 0x800, 0xd7ff, 0xe000,
                                     0xffff, 0x10000, 0x10ffff]
        for cp in points:
            char = chr(cp)
            for value in (char, {char: char}, [char, char]):
                with self.subTest(codepoint=cp, root_type=type(value).__name__):
                    expected = reference_bytes(value)
                    self.assertEqual(expected, canonical_bytes(value, limits=Limits(max_bytes=len(expected))))
        pair = loads_strict('"\\ud800\\udc00"')
        self.assertEqual('\U00010000', pair)
        self.assertEqual(b'"\xf0\x90\x80\x80"', canonical_bytes(pair))

    def test_unicode_normalization_is_not_silently_applied(self):
        left = {'\u00e9': '\u00e9'}
        right = {'e\u0301': 'e\u0301'}
        self.assertFalse(canonical_equal(left, right))
        # Python scalar ordering is deliberately not a JCS/UTF-16 assertion.
        value = {'\U00010000': 1, '\ue000': 2}
        self.assertEqual(reference_bytes(value), canonical_bytes(value))

    def test_finite_ieee754_values_preserve_encoder_identity(self):
        rng = random.Random(SEED + 1)
        floats = list(FINITE_EDGES)
        while len(floats) < 512:
            candidate = struct.unpack('!d', rng.getrandbits(64).to_bytes(8, 'big'))[0]
            if math.isfinite(candidate):
                floats.append(candidate)
        for index, number in enumerate(floats):
            with self.subTest(case=index):
                expected = reference_bytes(number)
                self.assertEqual(expected, canonical_bytes(number))
                self.assertEqual(expected, canonical_bytes(loads_strict(expected)))

    def test_python_equal_scalars_do_not_alias_byte_identity(self):
        values = [False, True, 0, 1, 0.0, -0.0, 1.0, '0', '1', None]
        for left, right in itertools.product(values, repeat=2):
            with self.subTest(left=repr(left), right=repr(right)):
                expected = reference_bytes(left) == reference_bytes(right)
                self.assertIs(expected, canonical_equal(left, right))
                self.assertIs(expected, canonical_equal({'v': left}, {'v': right}))

    def test_custom_integer_range_both_signs_and_text_paths(self):
        for maximum in (0, 1, 9, 10, 99, 100, 10**15, (10**100) - 1):
            limits = Limits(max_integer_abs=maximum)
            for sign in (-1, 1):
                with self.subTest(maximum_digits=len(str(maximum)), sign=sign):
                    value = sign * maximum
                    self.assertEqual(str(value).encode(), canonical_bytes(value, limits=limits))
                    self.assertEqual(value, loads_strict(str(value), limits=limits))
                    self.assertEqual(value, loads_strict(str(value).encode(), limits=limits))
                    outside = sign * (maximum + 1)
                    for function, argument in ((canonical_bytes, outside),
                                               (loads_strict, str(outside)),
                                               (loads_strict, str(outside).encode())):
                        self.assert_code('integer_out_of_range', function, argument, limits=limits)
        self.assertEqual(0, loads_strict('-0', limits=Limits(max_integer_abs=0)))

    def test_duplicate_keys_are_checked_after_escape_decoding(self):
        packets = ('{"a":1,"\\u0061":2}', '{"x":{"a":1,"a":2}}',
                   '{"\\ud800\\udc00":1,"\U00010000":2}',
                   '{"\\n":1,"\\u000a":2}')
        for packet in packets:
            for raw in (packet, packet.encode()):
                with self.subTest(packet=repr(raw)):
                    self.assert_code('duplicate_key', loads_strict, raw)

    def test_malformed_input_and_nonfinite_values_keep_typed_errors(self):
        for packet in ('', ' ', '01', '--1', '1.', '+1', '[1,]',
                       '{"x":}', '{}{}', 'true false', '"\\x00"', '\ufeff{}'):
            with self.subTest(packet=repr(packet)):
                self.assert_code('invalid_json', loads_strict, packet)
        for packet in ('NaN', 'Infinity', '-Infinity', '1e999', '-1e999'):
            self.assert_code('nonfinite_number', loads_strict, packet)
        for value in (float('nan'), float('inf'), -float('inf')):
            self.assert_code('nonfinite_number', canonical_bytes, value)

    def test_raw_input_budget_is_separate_from_compact_output(self):
        limits = Limits(max_bytes=7)
        self.assertEqual(b'{"a":1}', canonical_bytes({'a': 1}, limits=limits))
        self.assertEqual({'a': 1}, loads_strict('{"a":1}', limits=limits))
        for raw in (' {"a":1}', b' {"a":1}', '"\U00010000\U00010000"'):
            self.assert_code('too_large', loads_strict, raw, limits=limits)

    def test_input_snapshots_are_not_modified_by_read_only_apis(self):
        value = {'a': [1, {'b': '\u00e9'}], 'z': [False, 0]}
        before = reference_bytes(value)
        child, grandchild = value['a'], value['a'][1]
        canonical_bytes(value)
        canonical_sha256(value)
        canonical_equal(value, reverse_mappings(value))
        self.assertEqual(before, reference_bytes(value))
        self.assertIs(child, value['a'])
        self.assertIs(grandchild, value['a'][1])


if __name__ == '__main__':
    unittest.main()
