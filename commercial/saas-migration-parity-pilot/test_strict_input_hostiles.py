from __future__ import annotations

import json
import unittest

import parity
import synthetic_fixture


class StrictInputHostiles(unittest.TestCase):
    def test_escaped_lone_surrogate_is_closed_error(self):
        obj = parity.loads_strict(synthetic_fixture.fixture_bytes())
        obj["source_snapshot"]["records"][0]["fields"]["name"] = "\ud800"
        raw = (json.dumps(obj, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
        with self.assertRaises(parity.ParityError):
            parity.compile_bytes(raw)

    def test_deep_json_is_closed_error(self):
        raw = ("[" * 2000 + "0" + "]" * 2000).encode("ascii")
        with self.assertRaises(parity.ParityError):
            parity.loads_strict(raw)

    def test_over_limit_integer_text_is_closed_error(self):
        raw = ('{"x":' + ('9' * 10000) + '}').encode("ascii")
        with self.assertRaises(parity.ParityError):
            parity.loads_strict(raw)

    def test_canonicalizer_refuses_nonfinite(self):
        with self.assertRaises(parity.ParityError):
            parity.canonical_bytes({"x": float("nan")})


if __name__ == "__main__":
    unittest.main()
