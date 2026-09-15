from __future__ import annotations

from copy import deepcopy
import unittest

from revenue.pursuit_portfolio import current
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.current import AuthorityKey
from test_pursuit_portfolio import NOW, authority_rows, opp, source as core_source

KEY = AuthorityKey("owner-key-v1", bytes.fromhex("11" * 32))


def source(*, max_age: int = 86400 * 5, state: str = "READY") -> dict:
    del state
    return core_source(
        [opp("alpha", 11, {"proposal": 3}, deadline="2026-09-16T14:00:00Z")],
        max_age=max_age,
    )


def authority_for(
    value: dict,
    *,
    key: AuthorityKey = KEY,
    issued_at: str = "2026-09-13T13:00:00Z",
    state: str = "READY",
) -> dict:
    del key
    return authority_rows(
        value["opportunities"],
        states={"alpha": state},
        captured=issued_at,
    )


class CurrentAdapterTests(unittest.TestCase):
    def test_explicit_time_adapter_compiles_v2_authority_bound_core(self):
        value = source()
        authority = authority_for(value)
        authorized = current.compile_authorized_at(value, authority, KEY, NOW)
        self.assertEqual(
            authorized.compiled.result["selected_opportunity_ids"], ["alpha"]
        )
        self.assertEqual(
            authorized.compiled.result["normalized_upstream_authority"],
            authorized.authority,
        )
        self.assertEqual(
            authorized.current_receipt["authority_sha256"],
            current._digest(authorized.authority_bytes),
        )

    def test_explicit_time_verify_recomputes_current_decision(self):
        value = source()
        authorized = current.compile_authorized_at(
            value, authority_for(value), KEY, NOW
        )
        verified = current.verify_authorized_at(
            authorized.compiled.result_bytes,
            authorized.compiled.markdown_bytes,
            authorized.compiled.receipt_bytes,
            authorized.authority_bytes,
            authorized.current_receipt_bytes,
            KEY,
            NOW,
        )
        self.assertTrue(verified["historical_integrity_verified"])
        self.assertTrue(verified["verified_current"])
        self.assertEqual(verified["selected_opportunity_ids"], ["alpha"])

    def test_stale_replay_fails_current_decision_recomputation(self):
        value = source(max_age=3600)
        authority = authority_for(value, issued_at="2026-09-13T13:30:00Z")
        authorized = current.compile_authorized_at(value, authority, KEY, NOW)
        with self.assertRaisesRegex(PortfolioError, "allocation decision is stale"):
            current.verify_authorized_at(
                authorized.compiled.result_bytes,
                authorized.compiled.markdown_bytes,
                authorized.compiled.receipt_bytes,
                authorized.authority_bytes,
                authorized.current_receipt_bytes,
                KEY,
                "2026-09-13T15:00:00Z",
            )

    def test_authority_bytes_and_receipt_are_exactly_bound(self):
        value = source()
        authorized = current.compile_authorized_at(
            value, authority_for(value), KEY, NOW
        )
        tampered = deepcopy(authorized.authority)
        tampered["rows"][0]["upstream_state"] = "HOLD"
        with self.assertRaisesRegex(PortfolioError, "trusted SHA-256 mismatch"):
            current.verify_authorized_at(
                authorized.compiled.result_bytes,
                authorized.compiled.markdown_bytes,
                authorized.compiled.receipt_bytes,
                current._canonical(tampered),
                authorized.current_receipt_bytes,
                KEY,
                NOW,
            )

    def test_caller_key_current_names_permanently_fail_closed(self):
        for function in (
            current.compile_authorized_current,
            current.verify_authorized_current,
        ):
            with self.assertRaisesRegex(
                PortfolioError, "fixed-host fresh-process boundary"
            ):
                function({}, {}, KEY)


if __name__ == "__main__":
    unittest.main(verbosity=2)
