# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

from market_microstack_current import (
    DONOR_COMMIT,
    FULL_ROUTER_GIT_BLOB,
    FULL_ROUTER_PATH,
    L3_GIT_BLOB,
    L3_PATH,
)


class SubmittedSourceAuthorityTests(unittest.TestCase):
    def _rev_parse(self, spec):
        return subprocess.check_output(
            ["git", "rev-parse", spec],
            cwd=Path(__file__).resolve().parent,
            text=True,
        ).strip()

    def test_exact_submitted_full_router_blob(self):
        self.assertEqual(
            self._rev_parse(f"{DONOR_COMMIT}:{FULL_ROUTER_PATH}"),
            FULL_ROUTER_GIT_BLOB,
        )

    def test_exact_submitted_l3_blob(self):
        self.assertEqual(
            self._rev_parse(f"{DONOR_COMMIT}:{L3_PATH}"),
            L3_GIT_BLOB,
        )


if __name__ == "__main__":
    unittest.main()
