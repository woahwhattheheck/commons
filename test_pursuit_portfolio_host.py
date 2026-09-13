from __future__ import annotations

from copy import deepcopy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio import cli, host
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.current import _compile_authorized_at
from test_pursuit_portfolio_current import KEY, NOW, authority_for, source


class HostAuthorityTests(unittest.TestCase):
    def _key_file(self, root: Path, *, key_hex: str | None = None) -> Path:
        path = root / "authority-key.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "pursuit-portfolio-allocation/authority-key/v1",
                    "key_id": KEY.key_id,
                    "key_hex": key_hex or KEY.key.hex(),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        if os.name == "posix":
            path.chmod(0o600)
        return path

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_fixed_host_key_compiles_without_any_key_parameter(self):
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            key_path = self._key_file(Path(tmp))
            with mock.patch.object(host, "HOST_KEY_PATH", key_path):
                compiled = host.compile_current(value, authority)
        self.assertEqual(compiled.authorized.compiled.result["selected_opportunity_ids"], ["alpha"])
        self.assertEqual(compiled.host_seal["input_sha256"], compiled.authorized.compiled.result["input_sha256"])

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_candidate_cannot_substitute_a_different_key_file(self):
        value = source(max_age=86400 * 5)
        attacker_key = type(KEY)(KEY.key_id, b"x" * 32)
        forged = authority_for(value, key=attacker_key)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host_dir = root / "host"
            host_dir.mkdir()
            host_key = self._key_file(host_dir)
            attacker_dir = root / "attacker"
            attacker_dir.mkdir()
            self._key_file(attacker_dir, key_hex=attacker_key.key.hex())
            with mock.patch.object(host, "HOST_KEY_PATH", host_key):
                with self.assertRaisesRegex(PortfolioError, "HMAC mismatch"):
                    host.compile_current(value, forged)

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_host_seal_binds_owner_priority_effort_and_policy_generation(self):
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            key_path = self._key_file(Path(tmp))
            with mock.patch.object(host, "HOST_KEY_PATH", key_path):
                legitimate = host.compile_current(value, authority)
                modified = deepcopy(value)
                modified["opportunities"][0]["priority_units"] = 999
                modified_authorized = _compile_authorized_at(modified, authority, KEY, NOW)
                with self.assertRaisesRegex(PortfolioError, "compiled-generation binding mismatch"):
                    host.verify_current(
                        modified_authorized.compiled.result_bytes,
                        modified_authorized.compiled.markdown_bytes,
                        modified_authorized.compiled.receipt_bytes,
                        modified_authorized.authority_bytes,
                        modified_authorized.current_receipt_bytes,
                        legitimate.host_seal_bytes,
                    )

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_host_seal_and_fresh_current_verification_succeed_together(self):
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            key_path = self._key_file(Path(tmp))
            with mock.patch.object(host, "HOST_KEY_PATH", key_path):
                compiled = host.compile_current(value, authority)
                authorized = compiled.authorized
                verified = host.verify_current(
                    authorized.compiled.result_bytes,
                    authorized.compiled.markdown_bytes,
                    authorized.compiled.receipt_bytes,
                    authorized.authority_bytes,
                    authorized.current_receipt_bytes,
                    compiled.host_seal_bytes,
                )
        self.assertTrue(verified["host_seal_verified"])
        self.assertTrue(verified["verified_current"])

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_host_key_symlink_is_rejected(self):
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = self._key_file(root)
            link = root / "key-link.json"
            link.symlink_to(real)
            with mock.patch.object(host, "HOST_KEY_PATH", link):
                with self.assertRaises(Exception):
                    host.compile_current(value, authority)

    @unittest.skipUnless(os.name == "posix", "permission assertion is POSIX-specific")
    def test_group_readable_host_key_is_rejected(self):
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            key_path = self._key_file(Path(tmp))
            key_path.chmod(0o640)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path):
                with self.assertRaisesRegex(PortfolioError, "owner-only permissions required"):
                    host.compile_current(value, authority)

    def test_cli_does_not_accept_a_candidate_selected_key_argument(self):
        with self.assertRaises(SystemExit) as caught:
            cli.main(["compile", "input.json", "authority.json", "candidate-key.json", "out"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
