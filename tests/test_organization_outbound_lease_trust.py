from __future__ import annotations

import ast
import inspect
import json
import stat
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import revenue.organization_outbound_lease as package
import revenue.organization_outbound_lease.cli as cli
import revenue.organization_outbound_lease.core as core
import revenue.organization_outbound_lease.trust as trust
from revenue.organization_outbound_lease.core import RsaPublicKey
from revenue.organization_outbound_lease.stores import GitHubContentsLeaseStore


class TrustBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.attacker = RsaPublicKey(
            key_id="attacker-key",
            modulus=(1 << 2048) + 159,
            exponent=65537,
        )

    def test_direct_core_import_is_same_hardened_public_acquire(self):
        self.assertIs(core.acquire_lease, package.acquire_lease)
        self.assertEqual(core.acquire_lease.__name__, "acquire_lease")

    def test_production_store_rejects_caller_supplied_verifier_before_any_io(self):
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
        with self.assertRaisesRegex(ValueError, "caller-supplied pressure verifier is forbidden"):
            core.acquire_lease(
                store,
                {},
                pressure_verifier=self.attacker,
                lease_nonce_key=b"n" * 32,
            )
        self.assertEqual(calls, [])

    def test_cli_contains_no_claimant_pressure_key_selector(self):
        source = Path(cli.__file__).read_text(encoding="utf-8")
        self.assertNotIn("ORG_PRESSURE_RSA_N_HEX", source)
        self.assertNotIn("ORG_PRESSURE_RSA_E", source)
        self.assertNotIn("ORG_PRESSURE_KEY_ID", source)
        self.assertNotIn("pressure-rsa-modulus-env", source)
        self.assertNotIn("pressure-key-id-env", source)

    def test_fixed_trust_root_has_no_environment_or_cli_override(self):
        self.assertEqual(
            str(trust.TRUST_ROOT_PATH),
            "/etc/tokenjunkielabs/organization-pressure-rsa-public.json",
        )
        source = Path(trust.__file__).read_text(encoding="utf-8")
        self.assertNotIn("getenv", source)
        self.assertNotIn("environ", source)

    def test_trust_root_parser_is_exact_and_builds_public_verifier(self):
        modulus = "%x" % ((1 << 2048) + 159)
        root = {
            "schema": "commons.organization-pressure-trust-root/v1",
            "algorithm": "RS256-PKCS1-v1_5",
            "keyId": "host-pressure-2026",
            "modulusHex": modulus,
            "exponent": 65537,
        }
        parsed = trust.parse_pressure_trust_root(root)
        self.assertEqual(parsed.key_id, "host-pressure-2026")
        self.assertEqual(parsed.modulus, int(modulus, 16))
        self.assertEqual(parsed.exponent, 65537)
        bad = dict(root)
        bad["extra"] = True
        with self.assertRaises(ValueError):
            trust.parse_pressure_trust_root(bad)

    def test_loader_uses_strict_pinned_document(self):
        modulus = "%x" % ((1 << 2048) + 159)
        raw = json.dumps({
            "schema": "commons.organization-pressure-trust-root/v1",
            "algorithm": "RS256-PKCS1-v1_5",
            "keyId": "host-pressure-2026",
            "modulusHex": modulus,
            "exponent": 65537,
        }, separators=(",", ":")).encode()
        with patch.object(trust, "_read_trust_root_bytes", return_value=raw):
            parsed = trust.load_pressure_verifier()
        self.assertEqual(parsed.key_id, "host-pressure-2026")

    def test_secure_mode_rejects_non_root_or_mutable_trust_root(self):
        safe = stat.S_IFREG | 0o644
        with self.assertRaisesRegex(ValueError, "root-owned"):
            trust._secure_mode(SimpleNamespace(st_uid=1000, st_mode=safe), "root")
        with self.assertRaisesRegex(ValueError, "group/world writable"):
            trust._secure_mode(SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o666), "root")

    def test_python39_syntax_fence_includes_trust_surface(self):
        root = Path(package.__file__).parent
        for path in [root / "__init__.py", root / "cli.py", root / "trust.py"]:
            with self.subTest(path=path.name):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 9))

    def test_public_acquire_signature_keeps_test_injection_explicit(self):
        params = inspect.signature(core.acquire_lease).parameters
        self.assertIn("pressure_verifier", params)
        self.assertEqual(params["pressure_verifier"].default, None)
        self.assertIn("lease_nonce_key", params)


if __name__ == "__main__":
    unittest.main()
