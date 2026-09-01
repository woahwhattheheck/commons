"""Authority pack date, URL, and applicability tests."""

from __future__ import annotations

import unittest

from charttrace.grounding.loader import load_pack, load_pack_library, pack_applies_to_care_dates


class GroundingPackTests(unittest.TestCase):
    def test_primary_source_effective_dates(self):
        hosp = load_pack("42_cfr_482_24")
        clia = load_pack("42_cfr_493_1291")
        self.assertEqual(hosp.effective_from, "1986-09-15")
        self.assertEqual(hosp.publication_date, "1986-06-17")
        self.assertNotEqual(hosp.effective_from, hosp.publication_date)
        self.assertEqual(clia.effective_from, "2003-04-24")
        self.assertEqual(clia.publication_date, "2003-01-24")
        self.assertTrue(hosp.primary_url.startswith("https://"))
        self.assertIn("482.24", hosp.pinpoint)
        self.assertTrue(clia.primary_url.startswith("https://"))
        self.assertIn("493.1291", clia.pinpoint)

    def test_library_has_unique_ids(self):
        lib = load_pack_library()
        self.assertEqual(len(lib), len(set(lib)))
        self.assertEqual(set(lib), {"42_cfr_482_24", "42_cfr_493_1291"})

    def test_stale_care_dates_are_inapplicable(self):
        hosp = load_pack("42_cfr_482_24")
        self.assertFalse(pack_applies_to_care_dates(hosp, "1986-09-01", "1986-09-14"))
        self.assertTrue(pack_applies_to_care_dates(hosp, "1986-09-15", "1986-09-16"))


if __name__ == "__main__":
    unittest.main()
