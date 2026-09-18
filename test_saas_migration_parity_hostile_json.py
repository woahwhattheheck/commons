from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


PACKAGE = Path(__file__).resolve().parent / "commercial" / "saas-migration-parity-pilot"
if str(PACKAGE) not in sys.path:
    sys.path.insert(0, str(PACKAGE))

import parity  # noqa: E402
import synthetic_fixture  # noqa: E402


class HostileJsonUnicodeBoundaryTests(unittest.TestCase):
    """Regression tests for the strict, deterministic ParityError boundary."""

    def test_escaped_lone_surrogate_rejected_as_parity_error(self) -> None:
        payload = parity.loads_strict(synthetic_fixture.fixture_bytes())
        payload["source_snapshot"]["records"][0]["fields"]["name"] = "\ud800"
        raw = (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")

        with self.assertRaises(parity.ParityError):
            parity.compile_bytes(raw)

    def test_deeply_nested_json_rejected_as_parity_error(self) -> None:
        raw = (b"[" * 5000) + b"0" + (b"]" * 5000)

        with self.assertRaises(parity.ParityError):
            parity.loads_strict(raw)

    def test_oversized_integer_text_rejected_as_parity_error(self) -> None:
        raw = b'{"value":' + (b"9" * 10000) + b"}"

        with self.assertRaises(parity.ParityError):
            parity.loads_strict(raw)

    def test_canonical_bytes_rejects_nonfinite_and_surrogate_values(self) -> None:
        for value in ({"value": float("nan")}, {"value": "\ud800"}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(parity.ParityError):
                    parity.canonical_bytes(value)


if __name__ == "__main__":
    unittest.main()
