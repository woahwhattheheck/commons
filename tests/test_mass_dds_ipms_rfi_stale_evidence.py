import unittest

from opportunities.mass_dds_ipms_rfi.compiler import CompileError, compile_packet
from tests.test_mass_dds_ipms_rfi import evidence, load


class TestMassDDSStaleEvidence(unittest.TestCase):
    def test_stale_source_cannot_support_affirmative_capability(self):
        doc = load()
        doc["sources"][0]["current"] = False
        evidence(doc, "ev.cap", "cap.video-analytics", source_id="src.notice.header.20260915")
        doc["capabilities"][0]["state"] = "SUPPORTED"
        doc["capabilities"][0]["evidence_refs"] = ["ev.cap"]
        with self.assertRaisesRegex(CompileError, "stale_source:src.notice.header.20260915"):
            compile_packet(doc)


if __name__ == "__main__":
    unittest.main()
