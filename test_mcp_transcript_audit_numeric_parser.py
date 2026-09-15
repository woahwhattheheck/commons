from __future__ import annotations

import unittest

from test_mcp_transcript_audit import CLIENT, raw_line, reason_codes
from tools.mcp_transcript_audit import audit_transcript


class NumericParserFailClosedTests(unittest.TestCase):
    def test_huge_numeric_exponent_holds_instead_of_escaping_decimal_exception(self):
        exponent = b"9" * 100
        payload = (
            b'{"jsonrpc":"2.0","id":1e'
            + exponent
            + b',"method":"initialize","params":'
            + b'{"protocolVersion":"2025-11-25","capabilities":{},'
            + b'"clientInfo":{"name":"probe","version":"1.0"}}}'
        )
        receipt = audit_transcript(raw_line(CLIENT, payload) + b"\n")
        self.assertEqual(receipt["status"], "HOLD")
        self.assertIn("INVALID_CAPTURE_EVENT", reason_codes(receipt))


if __name__ == "__main__":
    unittest.main()
