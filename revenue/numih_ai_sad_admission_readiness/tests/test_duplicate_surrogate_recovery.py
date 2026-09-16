from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from revenue.numih_ai_sad_admission_readiness import cli
from revenue.numih_ai_sad_admission_readiness.compiler import ValidationError, loads_strict


class _StrictUtf8Stderr(io.TextIOBase):
    def __init__(self) -> None:
        super().__init__()
        self._data = bytearray()

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        encoded = text.encode("utf-8", errors="strict")
        self._data.extend(encoded)
        return len(text)

    def getvalue(self) -> str:
        return bytes(self._data).decode("utf-8", errors="strict")


class DuplicateSurrogateRecoveryTests(unittest.TestCase):
    HOSTILE = '{"\\ud800":1,"\\ud800":2}'

    def test_duplicate_surrogate_key_uses_fixed_scalar_safe_error(self) -> None:
        with self.assertRaisesRegex(ValidationError, r"^duplicate JSON key$"):
            loads_strict(self.HOSTILE)

    def test_cli_duplicate_surrogate_key_is_bounded_and_traceback_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet_path = root / "packet.json"
            bundle_path = root / "bundle.json"
            packet_path.write_text(self.HOSTILE, encoding="ascii")
            bundle_path.write_text("{}", encoding="ascii")
            stderr = _StrictUtf8Stderr()
            with contextlib.redirect_stderr(stderr):
                rc = cli.main(
                    [
                        str(packet_path),
                        "--evidence-bundle",
                        str(bundle_path),
                    ]
                )
            rendered = stderr.getvalue()
            self.assertEqual(rc, 2)
            self.assertEqual(rendered, "numih error: duplicate JSON key\n")
            self.assertLessEqual(len(rendered.encode("utf-8")), 128)
            self.assertNotIn("Traceback", rendered)
            self.assertNotIn("UnicodeEncodeError", rendered)


if __name__ == "__main__":
    unittest.main()
