from __future__ import annotations

import unittest

import revenue.organization_outbound_lease.core as core
from revenue.organization_outbound_lease.core import RsaPublicKey
from revenue.organization_outbound_lease.stores import FileLeaseStore
from tests.test_organization_outbound_lease_trust import (
    ATTACKER_E,
    ATTACKER_N_HEX,
    _attacker_sign,
    _utc,
)


class BridgedFileLeaseStore(FileLeaseStore):
    """A FileLeaseStore subclass that launders every protocol call elsewhere."""

    def __init__(self):
        # Intentionally do not initialize FileLeaseStore local paths. A subclass may
        # replace the protocol methods entirely while still satisfying isinstance().
        self.calls = []

    def _touch(self, name):
        self.calls.append(name)
        raise AssertionError("delegated production-like backend was touched: %s" % name)

    def get_active(self, org_fingerprint: str):
        return self._touch("get_active")

    def get_outcome(self, org_fingerprint: str, lease_id: str):
        return self._touch("get_outcome")

    def create_active(self, org_fingerprint: str, content: bytes) -> str:
        return self._touch("create_active")

    def create_outcome(self, org_fingerprint: str, lease_id: str, content: bytes) -> str:
        return self._touch("create_outcome")

    def delete_active(self, org_fingerprint: str, expected_generation: str) -> None:
        self._touch("delete_active")


class StoreBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.attacker = RsaPublicKey.from_hex(
            key_id="attacker-key",
            modulus_hex=ATTACKER_N_HEX,
            exponent=ATTACKER_E,
        )

    def _valid_attacker_request(self):
        org = "1" * 64
        body = core.pressure_attestation_body({
            "schema": core.ATTESTATION_SCHEMA,
            "organizationFingerprint": org,
            "pressureReceiptSha256": "2" * 64,
            "authorityCommitment": "3" * 64,
            "ledgerCommitment": "4" * 64,
            "verifiedState": core.READY_STATE,
            "verifiedAt": _utc(-2),
        })
        attestation = {
            "body": body,
            "algorithm": "RS256-PKCS1-v1_5",
            "keyId": self.attacker.key_id,
            "signatureHex": _attacker_sign(
                core.PRESSURE_DOMAIN + core.canonical_json(body)
            ),
        }
        # The hostile is not a malformed-signature test. Prove the attacker owns a
        # valid keypair and produced a READY signature that core accepts under it.
        verified = core.verify_pressure_attestation(
            attestation,
            self.attacker,
            organization_fingerprint=org,
        )
        self.assertEqual(verified["verifiedState"], core.READY_STATE)
        return {
            "schema": core.ACQUIRE_SCHEMA,
            "claimId": "bridged-attacker-claim",
            "organizationFingerprint": org,
            "prospectFingerprint": "5" * 64,
            "routeCommitment": "6" * 64,
            "opportunityCommitment": "7" * 64,
            "holderCapabilityCommitment": core.holder_capability_commitment(b"c" * 32),
            "requestedAt": _utc(-1),
            "pressureAttestation": attestation,
        }

    def test_file_store_subclass_cannot_launder_attacker_verifier(self):
        store = BridgedFileLeaseStore()
        request = self._valid_attacker_request()
        with self.assertRaisesRegex(
            ValueError,
            "caller-supplied pressure verifier is forbidden",
        ):
            core.acquire_lease(
                store,
                request,
                pressure_verifier=self.attacker,
                lease_nonce_key=b"n" * 32,
            )
        self.assertEqual(store.calls, [])


if __name__ == "__main__":
    unittest.main()
