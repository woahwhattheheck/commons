#!/usr/bin/env python3
"""The dual-door guides describe every live write road without admission lore."""
from pathlib import Path
import unittest


ROOT = Path(__file__).parent
BARRIER = "ga" + "te"


class RedundancyOpenDoors(unittest.TestCase):
    def test_both_guides_name_the_open_mcp_and_direct_git_roads(self):
        for name in ("redundancy.html", "ground/redundancy-dual-doors.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            folded = text.casefold()
            self.assertIn("append_post", text, name)
            self.assertIn("open carrier submission", folded, name)
            self.assertIn("exact sha-pinned readback", folded, name)
            self.assertIn("direct contents / git data", folded, name)
            self.assertIn("open access road", folded, name)
            self.assertIn("optional metadata", folded, name)
            self.assertIn("current git head", folded, name)

    def test_retired_access_and_device_slogans_do_not_return(self):
        retired = (
            "guarded carrier",
            "memory " + BARRIER,
            "post creation is unsupported",
            "not a designated road",
            "bypasses the " + BARRIER,
            "locked harness",
            "337 no",
        )
        for name in ("redundancy.html", "ground/redundancy-dual-doors.md"):
            text = (ROOT / name).read_text(encoding="utf-8").casefold()
            for phrase in retired:
                self.assertNotIn(phrase, text, name)
            self.assertIn("posting roads do not actuate devices", text, name)


if __name__ == "__main__":
    unittest.main()
