from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
import unittest
from pathlib import Path

from revenue.pursuit_portfolio.core import PortfolioError, normalize_upstream_authority
from revenue.pursuit_portfolio.current import (
    AuthorityKey,
    CURRENT_RECEIPT_SCHEMA,
    KEY_SCHEMA,
    SIGNED_AUTHORITY_SCHEMA,
    _canonical,
    _compile_authorized_at,
    _verify_authorized_at,
    load_authority_key,
    read_regular_bytes,
)
from test_pursuit_portfolio import NOW, authority_rows, opp, source

KEY = AuthorityKey("owner-root-1", b"k" * 32)


def portfolio_source(*, max_age: int = 86400 * 5):
    return source([opp("A", 7, {"proposal": 1})], max_age=max_age)


def _resign(value: dict, key: AuthorityKey = KEY) -> dict:
    unsigned = {
        "schema": value["schema"],
        "key_id": value["key_id"],
        "issued_at": value["issued_at"],
        "upstream_authority": value["upstream_authority"],
    }
    return {
        **unsigned,
        "hmac_sha256": hmac.new(key.key, _canonical(unsigned), hashlib.sha256).hexdigest(),
    }


def signed_authority_for(
    data,
    *,
    key: AuthorityKey = KEY,
    states=None,
    captured: str = "2026-09-13T13:00:00Z",
    issued_at: str = NOW,
):
    inner = normalize_upstream_authority(
        authority_rows(data["opportunities"], states=states, captured=captured)
    )
    return _resign(
        {
            "schema": SIGNED_AUTHORITY_SCHEMA,
            "key_id": key.key_id,
            "issued_at": issued_at,
            "upstream_authority": inner,
        },
        key,
    )


class CurrentAdapterTests(unittest.TestCase):
    def test_signed_v2_authority_compiles_without_moving_readiness_into_source(self):
        data = portfolio_source()
        signed = signed_authority_for(data)
        value = _compile_authorized_at(data, signed, KEY, NOW)
        self.assertEqual(value.compiled.result["selected_opportunity_ids"], ["A"])
        self.assertNotIn("upstream_state", value.compiled.result["normalized_input"]["opportunities"][0])
        self.assertEqual(
            value.compiled.result["normalized_upstream_authority"],
            signed["upstream_authority"],
        )
        self.assertEqual(value.current_receipt["schema"], CURRENT_RECEIPT_SCHEMA)
        self.assertEqual(
            value.current_receipt["authority_sha256"],
            hashlib.sha256(value.authority_bytes).hexdigest(),
        )

    def test_signed_authority_hmac_covers_exact_inner_v2_generation(self):
        data = portfolio_source()
        signed = signed_authority_for(data)
        signed["upstream_authority"]["rows"][0]["upstream_state"] = "HOLD"
        with self.assertRaisesRegex(PortfolioError, "HMAC mismatch"):
            _compile_authorized_at(data, signed, KEY, NOW)

    def test_caller_minted_readiness_in_source_still_fails_closed(self):
        data = portfolio_source()
        data["opportunities"][0]["upstream_state"] = "READY"
        signed = signed_authority_for(portfolio_source())
        with self.assertRaisesRegex(PortfolioError, "keys mismatch"):
            _compile_authorized_at(data, signed, KEY, NOW)

    def test_signed_authority_time_fences(self):
        data = portfolio_source()
        future = signed_authority_for(data, issued_at="2026-09-13T14:00:01Z")
        with self.assertRaisesRegex(PortfolioError, "future-issued"):
            _compile_authorized_at(data, future, KEY, NOW)

        inner_future = signed_authority_for(
            data,
            captured="2026-09-13T14:00:01Z",
            issued_at=NOW,
        )
        with self.assertRaisesRegex(PortfolioError, "predates authority generation"):
            _compile_authorized_at(data, inner_future, KEY, NOW)

        impossible = signed_authority_for(
            data,
            captured="2026-09-13T13:30:00Z",
            issued_at=NOW,
        )
        impossible["upstream_authority"]["generated_at"] = "2026-09-13T13:00:00Z"
        impossible = _resign(impossible)
        with self.assertRaisesRegex(PortfolioError, "evidence postdates authority generation"):
            _compile_authorized_at(data, impossible, KEY, NOW)

    def test_roundtrip_binds_signed_wrapper_inner_authority_and_core_receipt(self):
        data = portfolio_source()
        signed = signed_authority_for(data)
        value = _compile_authorized_at(data, signed, KEY, NOW)
        verified = _verify_authorized_at(
            value.compiled.result_bytes,
            value.compiled.markdown_bytes,
            value.compiled.receipt_bytes,
            value.authority_bytes,
            value.current_receipt_bytes,
            KEY,
            NOW,
        )
        self.assertTrue(verified["verified_current"])
        self.assertEqual(verified["selected_opportunity_ids"], ["A"])
        self.assertEqual(
            verified["upstream_authority_sha256"],
            value.compiled.result["upstream_authority_sha256"],
        )

    def test_current_reassessment_rejects_stale_allocation(self):
        data = portfolio_source(max_age=3600)
        signed = signed_authority_for(data, captured="2026-09-13T13:30:00Z")
        value = _compile_authorized_at(data, signed, KEY, NOW)
        self.assertEqual(value.compiled.result["selected_opportunity_ids"], ["A"])
        with self.assertRaisesRegex(PortfolioError, "allocation decision is stale"):
            _verify_authorized_at(
                value.compiled.result_bytes,
                value.compiled.markdown_bytes,
                value.compiled.receipt_bytes,
                value.authority_bytes,
                value.current_receipt_bytes,
                KEY,
                "2026-09-13T15:00:01Z",
            )

    def test_current_receipt_tamper_is_rejected(self):
        data = portfolio_source()
        value = _compile_authorized_at(data, signed_authority_for(data), KEY, NOW)
        receipt = dict(value.current_receipt)
        receipt["input_sha256"] = "f" * 64
        tampered = _canonical(receipt)
        with self.assertRaisesRegex(PortfolioError, "self commitment mismatch"):
            _verify_authorized_at(
                value.compiled.result_bytes,
                value.compiled.markdown_bytes,
                value.compiled.receipt_bytes,
                value.authority_bytes,
                tampered,
                KEY,
                NOW,
            )

    @unittest.skipUnless(os.name == "posix", "descriptor custody requires POSIX")
    def test_private_key_requires_owner_only_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "authority-key.json"
            key_value = {
                "schema": KEY_SCHEMA,
                "key_id": KEY.key_id,
                "key_hex": KEY.key.hex(),
            }
            path.write_bytes(_canonical(key_value))
            path.chmod(0o640)
            with self.assertRaisesRegex(PortfolioError, "owner-only permissions"):
                load_authority_key(path)

    @unittest.skipUnless(os.name == "posix", "descriptor custody requires POSIX")
    def test_symlinked_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            payload = real / "input.json"
            payload.write_bytes(b"{}")
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            with self.assertRaises((OSError, PortfolioError)):
                read_regular_bytes(alias / "input.json", 1024, "input")


if __name__ == "__main__":
    unittest.main(verbosity=2)
