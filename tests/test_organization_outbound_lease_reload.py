from __future__ import annotations

import importlib
import unittest

import revenue.organization_outbound_lease as package
import revenue.organization_outbound_lease.core as core
from revenue.organization_outbound_lease.stores import GitHubContentsLeaseStore
from tests.test_organization_outbound_lease_trust import TrustBoundaryTests


class CoreReloadTrustBoundaryTests(unittest.TestCase):
    """A module reload must not restore claimant-selected production verifier authority."""

    def test_reload_core_rejects_attacker_verifier_before_store_io(self):
        helper = TrustBoundaryTests(
            methodName="test_direct_core_import_is_same_hardened_public_acquire"
        )
        helper.setUp()
        request = helper._valid_attacker_ready_request()
        attacker = helper.attacker
        calls = []

        def opener(request):
            calls.append(request)
            raise AssertionError("production store must not be touched")

        store = GitHubContentsLeaseStore(
            repository="owner/repo",
            branch="outbound-lease-ledger",
            token="token",
            opener=opener,
        )

        reloaded = importlib.reload(core)
        self.assertIs(reloaded, core)
        self.assertEqual(core.acquire_lease.__name__, "acquire_lease")
        with self.assertRaisesRegex(
            ValueError,
            "caller-supplied pressure verifier is forbidden",
        ):
            core.acquire_lease(
                store,
                request,
                pressure_verifier=attacker,
                lease_nonce_key=b"n" * 32,
            )
        self.assertEqual(calls, [])

        # Keep the package-level alias coherent for any tests loaded after this one.
        package.acquire_lease = core.acquire_lease


if __name__ == "__main__":
    unittest.main()
