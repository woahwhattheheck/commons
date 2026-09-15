from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio import cli, host
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.current import _canonical, _compile_authorized_at
from revenue.pursuit_portfolio.floor import FLOOR_SCHEMA
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

    def _floor_file(
        self,
        root: Path,
        authority: dict,
        *,
        generation: int = 1,
        key=KEY,
        updated_at: str = NOW,
    ) -> Path:
        path = root / "authority-floor.json"
        unsigned = {
            "authority_sha256": hashlib.sha256(_canonical(authority)).hexdigest(),
            "generation": generation,
            "key_id": key.key_id,
            "schema": FLOOR_SCHEMA,
            "updated_at": updated_at,
        }
        value = {
            **unsigned,
            "hmac_sha256": hmac.new(key.key, _canonical(unsigned), hashlib.sha256).hexdigest(),
        }
        path.write_bytes(_canonical(value))
        if os.name == "posix":
            path.chmod(0o600)
        return path

    def _host_paths(self, root: Path, authority: dict, *, generation: int = 1):
        return self._key_file(root), self._floor_file(root, authority, generation=generation)

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_fixed_host_key_and_floor_compile_without_candidate_selectors(self):
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            key_path, floor_path = self._host_paths(Path(tmp), authority)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ):
                compiled = host.compile_current(value, authority)
        self.assertEqual(compiled.authorized.compiled.result["selected_opportunity_ids"], ["alpha"])
        self.assertEqual(compiled.host_seal["input_sha256"], compiled.authorized.compiled.result["input_sha256"])
        self.assertEqual(compiled.host_seal["authority_floor_generation"], 1)

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
            host_floor = self._floor_file(host_dir, forged)
            attacker_dir = root / "attacker"
            attacker_dir.mkdir()
            self._key_file(attacker_dir, key_hex=attacker_key.key.hex())
            with mock.patch.object(host, "HOST_KEY_PATH", host_key), mock.patch.object(
                host, "HOST_FLOOR_PATH", host_floor
            ):
                with self.assertRaisesRegex(PortfolioError, "HMAC mismatch"):
                    host.compile_current(value, forged)

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_host_seal_binds_owner_priority_effort_and_policy_generation(self):
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            key_path, floor_path = self._host_paths(Path(tmp), authority)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ):
                legitimate = host.compile_current(value, authority)
                modified = deepcopy(value)
                modified["opportunities"][0]["priority_units"] = 999
                modified_authorized = _compile_authorized_at(modified, authority, KEY, NOW)
                with self.assertRaisesRegex(PortfolioError, "compiled-generation"):
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
            key_path, floor_path = self._host_paths(Path(tmp), authority, generation=7)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ):
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
        self.assertEqual(verified["authority_floor_generation"], 7)

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_g1_ready_replay_fails_after_g2_withdrawal_floor(self):
        value_g1 = source(max_age=86400 * 5, state="READY")
        authority_g1 = authority_for(value_g1)
        # G2 is a real host-signed withdrawal generation: the same opportunity
        # no longer has a positive READY/CURABLE authority entry.
        value_g2 = source(max_age=86400 * 5, state="HOLD")
        authority_g2 = authority_for(value_g2, issued_at="2026-09-13T14:01:00Z")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path = self._key_file(root)
            floor_path = self._floor_file(root, authority_g1, generation=1)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ):
                historical = host.compile_current(value_g1, authority_g1)
                self._floor_file(root, authority_g2, generation=2, updated_at="2026-09-13T14:01:00Z")
                with self.assertRaisesRegex(PortfolioError, "superseded"):
                    host.verify_current(
                        historical.authorized.compiled.result_bytes,
                        historical.authorized.compiled.markdown_bytes,
                        historical.authorized.compiled.receipt_bytes,
                        historical.authorized.authority_bytes,
                        historical.authorized.current_receipt_bytes,
                        historical.host_seal_bytes,
                    )

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_same_generation_authority_fork_does_not_revalidate_old_package(self):
        value = source(max_age=86400 * 5)
        authority_a = authority_for(value, issued_at=NOW)
        authority_b = authority_for(value, issued_at="2026-09-13T14:02:00Z")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path = self._key_file(root)
            floor_path = self._floor_file(root, authority_a, generation=9)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ):
                historical = host.compile_current(value, authority_a)
                # Even if an operator/signing bug produced a same-sequence fork,
                # only the exact digest retained by the host floor is current.
                self._floor_file(root, authority_b, generation=9, updated_at="2026-09-13T14:02:00Z")
                with self.assertRaisesRegex(PortfolioError, "superseded"):
                    host.verify_current(
                        historical.authorized.compiled.result_bytes,
                        historical.authorized.compiled.markdown_bytes,
                        historical.authorized.compiled.receipt_bytes,
                        historical.authorized.authority_bytes,
                        historical.authorized.current_receipt_bytes,
                        historical.host_seal_bytes,
                    )

    @unittest.skipUnless(os.name == "posix", "fixed-host descriptor path requires POSIX dir_fd semantics")
    def test_floor_hmac_tamper_fails_before_current_use(self):
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path, floor_path = self._host_paths(root, authority)
            floor = json.loads(floor_path.read_text(encoding="utf-8"))
            floor["generation"] = 2
            floor_path.write_bytes(_canonical(floor))
            floor_path.chmod(0o600)
            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ):
                with self.assertRaisesRegex(PortfolioError, "authority floor: HMAC mismatch"):
                    host.compile_current(value, authority)

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

    def test_cli_does_not_accept_candidate_selected_key_or_floor_arguments(self):
        with self.assertRaises(SystemExit) as caught:
            cli.main(
                [
                    "compile",
                    "input.json",
                    "authority.json",
                    "candidate-key.json",
                    "candidate-floor.json",
                    "out",
                ]
            )
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
