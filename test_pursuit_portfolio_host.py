from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
import unittest
from pathlib import Path

from revenue.pursuit_portfolio import cli, current, host
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.floor import require_current_authority
from test_pursuit_portfolio_current import KEY, NOW, authority_for, source
from test_pursuit_portfolio_host_support import write_floor, write_key


@unittest.skipUnless(os.name == "posix", "POSIX retained trust files required")
class HostAuthorityComponentTests(unittest.TestCase):
    def test_retained_components_compile_and_seal_v2_generation(self):
        value = source()
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = host._load_host_key_from(write_key(root))
            floor = host._load_host_floor_from(
                write_floor(root, authority, generation=7, updated_at=NOW), key, NOW
            )
            authorized = current.compile_authorized_at(value, authority, key, NOW)
            require_current_authority(floor, authorized.authority_bytes)
            seal = host.seal(authorized, key, floor)
        self.assertEqual(
            authorized.compiled.result["selected_opportunity_ids"], ["alpha"]
        )
        self.assertEqual(seal["authority_floor_generation"], 7)

    def test_floor_key_mismatch_cannot_authorize_generation(self):
        value = source()
        authority = authority_for(value)
        attacker = type(KEY)("attacker-key-v1", b"x" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = host._load_host_key_from(write_key(root))
            floor_path = write_floor(
                root,
                authority,
                attacker,
                generation=1,
                updated_at=NOW,
            )
            with self.assertRaisesRegex(PortfolioError, "key_id mismatch"):
                host._load_host_floor_from(floor_path, key, NOW)

    def test_seal_hmac_binds_exact_core_and_floor_generation(self):
        value = source()
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = host._load_host_key_from(write_key(root))
            floor = host._load_host_floor_from(
                write_floor(root, authority, generation=9, updated_at=NOW), key, NOW
            )
            authorized = current.compile_authorized_at(value, authority, key, NOW)
            seal = host.seal(authorized, key, floor)
        base = dict(seal)
        claimed = base.pop("hmac_sha256")
        self.assertEqual(
            claimed,
            hmac.new(key.key, current._canonical(base), hashlib.sha256).hexdigest(),
        )
        self.assertEqual(
            seal["result_sha256"],
            hashlib.sha256(authorized.compiled.result_bytes).hexdigest(),
        )

    def test_cli_refuses_candidate_selected_key_and_floor_arguments(self):
        with self.assertRaises(SystemExit) as caught:
            cli.main(
                [
                    "compile",
                    "input.json",
                    "authority.json",
                    "key.json",
                    "floor.json",
                    "out",
                ]
            )
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
