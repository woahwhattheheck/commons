from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import revenue.pursuit_portfolio.current as current
from revenue.pursuit_portfolio import host
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.current import AuthorityKey, KEY_SCHEMA, _canonical
from revenue.pursuit_portfolio.floor import FLOOR_SCHEMA
from test_pursuit_portfolio import NOW
from test_pursuit_portfolio_current import KEY, portfolio_source, signed_authority_for


def write_key(path: Path, key: AuthorityKey = KEY) -> None:
    path.write_bytes(
        _canonical(
            {
                "schema": KEY_SCHEMA,
                "key_id": key.key_id,
                "key_hex": key.key.hex(),
            }
        )
    )
    path.chmod(0o600)


def write_floor(
    path: Path,
    authority_raw: bytes,
    *,
    key: AuthorityKey = KEY,
    generation: int = 1,
    updated_at: str = NOW,
) -> None:
    unsigned = {
        "authority_sha256": hashlib.sha256(authority_raw).hexdigest(),
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
    path.chmod(0o600)


@unittest.skipUnless(os.name == "posix", "fixed-host descriptor custody requires POSIX")
class HostCurrentTests(unittest.TestCase):
    def host_state(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        host_dir = root / "host"
        host_dir.mkdir(mode=0o700)
        key_path = host_dir / "authority-key.json"
        floor_path = host_dir / "authority-floor.json"
        write_key(key_path)
        return tmp, host_dir, key_path, floor_path

    def fixed_clock(self):
        return (
            mock.patch.object(current, "_now", return_value=NOW),
            mock.patch.object(host, "_now", return_value=NOW),
        )

    def test_compile_and_verify_use_fixed_key_floor_and_host_seal(self):
        tmp, _host_dir, key_path, floor_path = self.host_state()
        self.addCleanup(tmp.cleanup)
        data = portfolio_source()
        signed = signed_authority_for(data)
        signed_raw = _canonical(signed)
        write_floor(floor_path, signed_raw)
        current_clock, host_clock = self.fixed_clock()

        with current_clock, host_clock, mock.patch.object(
            host, "HOST_KEY_PATH", key_path
        ), mock.patch.object(host, "HOST_FLOOR_PATH", floor_path):
            value = host.compile_current(data, signed)
            verified = host.verify_current(
                value.authorized.compiled.result_bytes,
                value.authorized.compiled.markdown_bytes,
                value.authorized.compiled.receipt_bytes,
                value.authorized.authority_bytes,
                value.authorized.current_receipt_bytes,
                value.host_seal_bytes,
            )
        self.assertTrue(verified["verified_current"])
        self.assertTrue(verified["host_seal_verified"])
        self.assertEqual(value.authorized.compiled.result["selected_opportunity_ids"], ["A"])

    def test_floor_supersession_rejects_historically_valid_signed_generation(self):
        tmp, _host_dir, key_path, floor_path = self.host_state()
        self.addCleanup(tmp.cleanup)
        data = portfolio_source()
        signed1 = signed_authority_for(data)
        raw1 = _canonical(signed1)
        write_floor(floor_path, raw1, generation=1)
        current_clock, host_clock = self.fixed_clock()

        with current_clock, host_clock, mock.patch.object(
            host, "HOST_KEY_PATH", key_path
        ), mock.patch.object(host, "HOST_FLOOR_PATH", floor_path):
            value1 = host.compile_current(data, signed1)

            signed2 = signed_authority_for(data)
            signed2["upstream_authority"]["revision"] = 2
            unsigned2 = {
                "schema": signed2["schema"],
                "key_id": signed2["key_id"],
                "issued_at": signed2["issued_at"],
                "upstream_authority": signed2["upstream_authority"],
            }
            signed2["hmac_sha256"] = hmac.new(
                KEY.key, _canonical(unsigned2), hashlib.sha256
            ).hexdigest()
            write_floor(floor_path, _canonical(signed2), generation=2)

            with self.assertRaisesRegex(PortfolioError, "superseded"):
                host.verify_current(
                    value1.authorized.compiled.result_bytes,
                    value1.authorized.compiled.markdown_bytes,
                    value1.authorized.compiled.receipt_bytes,
                    value1.authorized.authority_bytes,
                    value1.authorized.current_receipt_bytes,
                    value1.host_seal_bytes,
                )

    def test_floor_exact_digest_rejects_same_generation_fork(self):
        tmp, _host_dir, key_path, floor_path = self.host_state()
        self.addCleanup(tmp.cleanup)
        data = portfolio_source()
        signed_a = signed_authority_for(data)
        signed_b = signed_authority_for(data)
        signed_b["upstream_authority"]["revision"] = 2
        unsigned_b = {
            "schema": signed_b["schema"],
            "key_id": signed_b["key_id"],
            "issued_at": signed_b["issued_at"],
            "upstream_authority": signed_b["upstream_authority"],
        }
        signed_b["hmac_sha256"] = hmac.new(
            KEY.key, _canonical(unsigned_b), hashlib.sha256
        ).hexdigest()
        write_floor(floor_path, _canonical(signed_a), generation=7)
        current_clock, host_clock = self.fixed_clock()

        with current_clock, host_clock, mock.patch.object(
            host, "HOST_KEY_PATH", key_path
        ), mock.patch.object(host, "HOST_FLOOR_PATH", floor_path):
            with self.assertRaisesRegex(PortfolioError, "superseded"):
                host.compile_current(data, signed_b)

    def test_host_seal_tamper_is_rejected(self):
        tmp, _host_dir, key_path, floor_path = self.host_state()
        self.addCleanup(tmp.cleanup)
        data = portfolio_source()
        signed = signed_authority_for(data)
        write_floor(floor_path, _canonical(signed))
        current_clock, host_clock = self.fixed_clock()
        with current_clock, host_clock, mock.patch.object(
            host, "HOST_KEY_PATH", key_path
        ), mock.patch.object(host, "HOST_FLOOR_PATH", floor_path):
            value = host.compile_current(data, signed)
            seal = dict(value.host_seal)
            seal["result_sha256"] = "f" * 64
            with self.assertRaisesRegex(PortfolioError, "binding mismatch|HMAC mismatch"):
                host.verify_current(
                    value.authorized.compiled.result_bytes,
                    value.authorized.compiled.markdown_bytes,
                    value.authorized.compiled.receipt_bytes,
                    value.authorized.authority_bytes,
                    value.authorized.current_receipt_bytes,
                    _canonical(seal),
                )

    def test_host_parent_must_be_effective_uid_owned_and_nonwritable_by_others(self):
        tmp, host_dir, key_path, floor_path = self.host_state()
        self.addCleanup(tmp.cleanup)
        data = portfolio_source()
        signed = signed_authority_for(data)
        write_floor(floor_path, _canonical(signed))
        host_dir.chmod(0o770)
        current_clock, host_clock = self.fixed_clock()
        with current_clock, host_clock, mock.patch.object(
            host, "HOST_KEY_PATH", key_path
        ), mock.patch.object(host, "HOST_FLOOR_PATH", floor_path):
            with self.assertRaisesRegex(PortfolioError, "must not be group/world writable"):
                host.compile_current(data, signed)

    def test_host_key_symlink_is_rejected(self):
        tmp, host_dir, key_path, floor_path = self.host_state()
        self.addCleanup(tmp.cleanup)
        data = portfolio_source()
        signed = signed_authority_for(data)
        write_floor(floor_path, _canonical(signed))
        real_key = host_dir / "real-key.json"
        key_path.replace(real_key)
        key_path.symlink_to(real_key.name)
        current_clock, host_clock = self.fixed_clock()
        with current_clock, host_clock, mock.patch.object(
            host, "HOST_KEY_PATH", key_path
        ), mock.patch.object(host, "HOST_FLOOR_PATH", floor_path):
            with self.assertRaises((OSError, PortfolioError)):
                host.compile_current(data, signed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
