from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from revenue.pursuit_portfolio import current, host
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.floor import require_current_authority
from test_pursuit_portfolio_current import KEY, NOW, authority_for, source
from test_pursuit_portfolio_host_support import write_floor, write_key


@unittest.skipUnless(os.name == "posix", "POSIX retained trust files required")
class HostFloorTests(unittest.TestCase):
    def test_ready_replay_fails_after_withdrawal_floor(self):
        value = source()
        ready = authority_for(value, state="READY")
        withdrawn = authority_for(
            value, state="HOLD", issued_at="2026-09-13T14:01:00Z"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = host._load_host_key_from(write_key(root))
            historical = current.compile_authorized_at(value, ready, key, NOW)
            floor = host._load_host_floor_from(
                write_floor(
                    root,
                    withdrawn,
                    generation=2,
                    updated_at="2026-09-13T14:01:00Z",
                ),
                key,
                "2026-09-13T14:02:00Z",
            )
            with self.assertRaisesRegex(PortfolioError, "superseded"):
                require_current_authority(floor, historical.authority_bytes)

    def test_floor_hmac_tamper_fails_before_use(self):
        value = source()
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = host._load_host_key_from(write_key(root))
            floor_path = write_floor(root, authority, updated_at=NOW)
            floor = json.loads(floor_path.read_text(encoding="utf-8"))
            floor["generation"] = 2
            floor_path.write_bytes(current._canonical(floor))
            floor_path.chmod(0o600)
            with self.assertRaisesRegex(PortfolioError, "HMAC mismatch"):
                host._load_host_floor_from(floor_path, key, NOW)

    def test_key_symlink_group_readability_and_hardlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = write_key(root)
            link = root / "key-link.json"
            link.symlink_to(real)
            with self.assertRaises(PortfolioError):
                host._load_host_key_from(link)
            real.chmod(0o640)
            with self.assertRaisesRegex(PortfolioError, "owner-only permissions"):
                host._load_host_key_from(real)
            real.chmod(0o600)
            os.link(real, root / "authority-key-alias.json")
            with self.assertRaisesRegex(PortfolioError, "single-link"):
                host._load_host_key_from(real)


if __name__ == "__main__":
    unittest.main(verbosity=2)
