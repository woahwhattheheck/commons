from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio.core import INPUT_SCHEMA, POLICY_SCHEMA, PortfolioError, normalize_input
from revenue.pursuit_portfolio.current import (
    AUTHORITY_SCHEMA,
    AuthorityKey,
    _canonical,
    _compile_authorized_at,
    _verify_authorized_at,
    read_published_authorized,
    read_regular_bytes,
    verify_upstream_authority,
)
from revenue.pursuit_portfolio.publisher import publish_authorized

NOW = "2026-09-13T14:00:00Z"
LATER = "2026-09-15T14:00:00Z"
KEY = AuthorityKey("owner-root-1", b"k" * 32)


def canon(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def policy(max_age=86400):
    base = {
        "schema": POLICY_SCHEMA,
        "revision": 1,
        "horizon_start": "2026-09-13T00:00:00Z",
        "horizon_end": "2026-09-20T00:00:00Z",
        "evidence_max_age_seconds": max_age,
        "pools": [{"pool_id": "proposal", "available_units": 4, "reserve_units": 0}],
    }
    return {**base, "policy_sha256": hashlib.sha256(canon(base)).hexdigest()}


def opportunity(state="READY", captured="2026-09-13T13:30:00Z", deadline="2026-09-16T14:00:00Z"):
    return {
        "opportunity_id": "alpha",
        "revision": 3,
        "source_sha256": "a" * 64,
        "upstream_receipt_sha256": "b" * 64,
        "evidence_ref": "evidence:alpha:r3",
        "evidence_captured_at": captured,
        "upstream_state": state,
        "response_deadline": deadline,
        "priority_units": 11,
        "effort": [{"pool_id": "proposal", "units": 2}],
        "min_buffer_minutes": 60,
    }


def source(*, state="READY", max_age=86400, captured="2026-09-13T13:30:00Z", deadline="2026-09-16T14:00:00Z"):
    return {
        "schema": INPUT_SCHEMA,
        "portfolio_id": "portfolio:test",
        "policy": policy(max_age=max_age),
        "opportunities": [opportunity(state=state, captured=captured, deadline=deadline)],
    }


def authority_for(value, *, key=KEY, issued_at=NOW):
    normalized = normalize_input(value)
    entries = []
    for row in normalized["opportunities"]:
        if row["upstream_state"] not in ("READY", "CURABLE"):
            continue
        entries.append(
            {
                "evidence_captured_at": row["evidence_captured_at"],
                "evidence_ref": row["evidence_ref"],
                "opportunity_id": row["opportunity_id"],
                "response_deadline": row["response_deadline"],
                "revision": row["revision"],
                "source_sha256": row["source_sha256"],
                "upstream_receipt_sha256": row["upstream_receipt_sha256"],
                "upstream_state": row["upstream_state"],
            }
        )
    unsigned = {
        "entries": sorted(entries, key=lambda row: row["opportunity_id"]),
        "issued_at": issued_at,
        "key_id": key.key_id,
        "schema": AUTHORITY_SCHEMA,
    }
    return {
        **unsigned,
        "hmac_sha256": hmac.new(key.key, _canonical(unsigned), hashlib.sha256).hexdigest(),
    }


class CurrentAuthorityTests(unittest.TestCase):
    def test_valid_authenticated_ready_allocates(self):
        value = source()
        compiled = _compile_authorized_at(value, authority_for(value), KEY, NOW)
        self.assertEqual(compiled.compiled.result["selected_opportunity_ids"], ["alpha"])
        self.assertEqual(
            compiled.compiled.result["opportunities"][0]["allocation_state"],
            "ALLOCATED_READY",
        )
        self.assertEqual(compiled.current_receipt["authority_key_id"], KEY.key_id)

    def test_caller_minted_ready_without_host_hmac_fails(self):
        value = source()
        forged = authority_for(value)
        forged["hmac_sha256"] = "0" * 64
        with self.assertRaisesRegex(PortfolioError, "HMAC mismatch"):
            _compile_authorized_at(value, forged, KEY, NOW)

    def test_authenticated_projection_must_match_exact_generation_and_state(self):
        value = source(state="READY")
        forged = authority_for(value)
        forged["entries"][0]["source_sha256"] = "c" * 64
        unsigned = {key: forged[key] for key in ("entries", "issued_at", "key_id", "schema")}
        forged["hmac_sha256"] = hmac.new(KEY.key, _canonical(unsigned), hashlib.sha256).hexdigest()
        with self.assertRaisesRegex(PortfolioError, "projection mismatch"):
            verify_upstream_authority(value, forged, KEY, trusted_now=NOW)

    def test_authority_cannot_predate_attested_evidence(self):
        value = source(captured="2026-09-13T14:00:00Z")
        forged = authority_for(value, issued_at="2026-09-13T13:59:59Z")
        with self.assertRaisesRegex(PortfolioError, "predates attested evidence"):
            _compile_authorized_at(value, forged, KEY, NOW)

    def test_fresh_current_verification_rejects_stale_historical_allocation(self):
        value = source(max_age=3600)
        compiled = _compile_authorized_at(value, authority_for(value), KEY, NOW)
        with self.assertRaisesRegex(PortfolioError, "allocation decision is stale"):
            _verify_authorized_at(
                compiled.compiled.result_bytes,
                compiled.compiled.markdown_bytes,
                compiled.compiled.receipt_bytes,
                compiled.authority_bytes,
                compiled.current_receipt_bytes,
                KEY,
                LATER,
            )

    def test_historical_and_current_verification_succeeds_while_semantics_unchanged(self):
        value = source(max_age=86400 * 5)
        compiled = _compile_authorized_at(value, authority_for(value), KEY, NOW)
        verified = _verify_authorized_at(
            compiled.compiled.result_bytes,
            compiled.compiled.markdown_bytes,
            compiled.compiled.receipt_bytes,
            compiled.authority_bytes,
            compiled.current_receipt_bytes,
            KEY,
            "2026-09-13T14:05:00Z",
        )
        self.assertTrue(verified["historical_integrity_verified"])
        self.assertTrue(verified["verified_current"])

    def test_authority_bytes_are_bound_into_current_receipt(self):
        value = source()
        compiled = _compile_authorized_at(value, authority_for(value), KEY, NOW)
        tampered = compiled.authority_bytes.replace(b'"revision":3', b'"revision":4')
        with self.assertRaises(PortfolioError):
            _verify_authorized_at(
                compiled.compiled.result_bytes,
                compiled.compiled.markdown_bytes,
                compiled.compiled.receipt_bytes,
                tampered,
                compiled.current_receipt_bytes,
                KEY,
                NOW,
            )


@unittest.skipUnless(os.name == "posix", "descriptor-generation hostiles require POSIX dir_fd semantics")
class CustodyTests(unittest.TestCase):
    def test_final_and_ancestor_symlinks_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            target = real / "input.json"
            target.write_text("{}", encoding="utf-8")
            final_link = real / "linked.json"
            final_link.symlink_to(target)
            with self.assertRaises(Exception):
                read_regular_bytes(final_link, 1024, "input")
            ancestor_link = root / "alias"
            ancestor_link.symlink_to(real, target_is_directory=True)
            with self.assertRaises(Exception):
                read_regular_bytes(ancestor_link / "input.json", 1024, "input")

    def test_published_directory_round_trip_uses_retained_generation(self):
        value = source(max_age=86400 * 5)
        compiled = _compile_authorized_at(value, authority_for(value), KEY, NOW)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir(mode=0o700)
            publish_authorized(compiled, out)
            parts = read_published_authorized(out)
            self.assertEqual(parts[0], compiled.compiled.result_bytes)
            self.assertEqual(parts[3], compiled.authority_bytes)
            self.assertEqual(parts[4], compiled.current_receipt_bytes)

    def test_late_publication_failure_preserves_prior_owned_files(self):
        value = source(max_age=86400 * 5)
        compiled = _compile_authorized_at(value, authority_for(value), KEY, NOW)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir(mode=0o700)
            import revenue.pursuit_portfolio.publisher as publisher
            original = publisher._write_relative
            calls = {"count": 0}

            def fail_second(dir_fd, name, data):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise PortfolioError("injected second-write failure")
                return original(dir_fd, name, data)

            with mock.patch.object(publisher, "_write_relative", side_effect=fail_second):
                with self.assertRaisesRegex(PortfolioError, "already-published files: portfolio.json"):
                    publisher.publish_authorized(compiled, out)
            self.assertEqual((out / "portfolio.json").read_bytes(), compiled.compiled.result_bytes)
            self.assertFalse((out / "portfolio.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
