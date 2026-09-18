from __future__ import annotations

import os
import traceback
import unittest
import urllib.error
from unittest.mock import patch

from host import jev


class JevCredentialHygieneTests(unittest.TestCase):
    def _vault(self, mapping):
        return patch.object(jev, "_cred_read", side_effect=lambda target: mapping.get(target, ""))

    def test_env_only_compatibility_fallback(self) -> None:
        with patch.dict(os.environ, {jev.ENV_KEY: "env-generation"}, clear=True), self._vault({}):
            self.assertEqual(jev.load_key(), "env-generation")
            self.assertEqual(jev.key_state(), "KEY_PRESENT_ENV")

    def test_vault_is_authoritative_when_matching_env_exists(self) -> None:
        vaulted = "same-generation"
        target = jev.CREDVAULT_TARGETS[0]
        with patch.dict(os.environ, {jev.ENV_KEY: vaulted}, clear=True), self._vault({target: vaulted}):
            self.assertEqual(jev.load_key(), vaulted)
            state = jev.key_state()
            self.assertEqual(state, f"KEY_PRESENT_CREDVAULT:{target}+ENV_MATCH")
            self.assertNotIn(vaulted, state)

    def test_env_vault_disagreement_fails_closed_without_secret(self) -> None:
        env_key = "old-env-generation"
        vault_key = "rotated-vault-generation"
        target = jev.CREDVAULT_TARGETS[0]
        with patch.dict(os.environ, {jev.ENV_KEY: env_key}, clear=True), self._vault({target: vault_key}):
            with self.assertRaisesRegex(jev.JevError, "^KEY_SOURCE_CONFLICT$") as caught:
                jev.load_key()
            self.assertEqual(jev.key_state(), "KEY_SOURCE_CONFLICT")
            rendered = str(caught.exception) + jev.key_state()
            self.assertNotIn(env_key, rendered)
            self.assertNotIn(vault_key, rendered)

    def test_two_vault_generations_disagree_fail_closed(self) -> None:
        first, second = jev.CREDVAULT_TARGETS
        values = {first: "vault-generation-a", second: "vault-generation-b"}
        with patch.dict(os.environ, {}, clear=True), self._vault(values):
            with self.assertRaisesRegex(jev.JevError, "^KEY_SOURCE_CONFLICT$"):
                jev.load_key()
            self.assertEqual(jev.key_state(), "KEY_SOURCE_CONFLICT")

    def test_two_vault_targets_may_alias_same_generation(self) -> None:
        first, second = jev.CREDVAULT_TARGETS
        values = {first: "same-vault-generation", second: "same-vault-generation"}
        with patch.dict(os.environ, {}, clear=True), self._vault(values):
            self.assertEqual(jev.load_key(), "same-vault-generation")
            self.assertEqual(jev.key_state(), f"KEY_PRESENT_CREDVAULT:{first}")

    def test_transport_exception_chain_does_not_reemit_key(self) -> None:
        key = "synthetic-key-must-not-escape"
        questions = {
            "route": {
                "type": "choice",
                "instructions": "choose",
                "criteria": {"a": "first", "b": "second"},
            }
        }
        leak = urllib.error.URLError("lower-layer detail " + key)
        with patch.object(jev.urllib.request, "urlopen", side_effect=leak):
            with self.assertRaisesRegex(jev.JevError, "^TRANSPORT$") as caught:
                jev.systemone("state", questions, key=key)
        rendered = "".join(
            traceback.TracebackException.from_exception(caught.exception).format(chain=True)
        )
        self.assertNotIn(key, rendered)
        self.assertTrue(caught.exception.__suppress_context__)

    def test_http_exception_chain_does_not_reemit_request_context(self) -> None:
        key = "synthetic-http-key-must-not-escape"
        questions = {
            "route": {
                "type": "choice",
                "instructions": "choose",
                "criteria": {"a": "first", "b": "second"},
            }
        }
        err = urllib.error.HTTPError(
            url="https://api.typesafe.ai/v1/systemone",
            code=401,
            msg="authorization failed " + key,
            hdrs=None,
            fp=None,
        )
        with patch.object(jev.urllib.request, "urlopen", side_effect=err):
            with self.assertRaisesRegex(jev.JevError, "^HTTP_401$") as caught:
                jev.systemone("state", questions, key=key)
        rendered = "".join(
            traceback.TracebackException.from_exception(caught.exception).format(chain=True)
        )
        self.assertNotIn(key, rendered)
        self.assertTrue(caught.exception.__suppress_context__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
