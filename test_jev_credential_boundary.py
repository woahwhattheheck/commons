"""Offline regression coverage; every credential and Windows API is synthetic."""
from __future__ import annotations

import ctypes
import io
import os
import traceback
import unittest
from unittest.mock import Mock, patch

from host import jev

QUESTIONS = {"route": {"type": "choice", "instructions": "choose",
                       "criteria": {"a": "first", "b": "second"}}}


class FakeVault:
    """Exercise the real ctypes read path without loading a DLL or real vault."""
    def __init__(self, blobs=None, error=1168):
        self.blobs = blobs or {}
        self.error = error
        self.retained = []
        self.CredReadW = Mock(side_effect=self.read)
        self.CredFree = Mock()

    def read(self, target, kind, flags, destination):
        if target not in self.blobs:
            return False
        blob = self.blobs[target]
        buffer = ctypes.create_string_buffer(blob)
        record = jev.CREDENTIALW()
        record.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))
        record.CredentialBlobSize = len(blob)
        self.retained.extend((buffer, record))
        ctypes.cast(destination, ctypes.POINTER(ctypes.POINTER(jev.CREDENTIALW)))[0] = ctypes.pointer(record)
        return True

    def patches(self):
        from contextlib import ExitStack
        stack = ExitStack()
        stack.enter_context(patch.object(jev.os, "name", "nt"))
        stack.enter_context(patch.object(jev.ctypes, "WinDLL", return_value=self, create=True))
        stack.enter_context(patch.object(jev.ctypes, "get_last_error", return_value=self.error, create=True))
        return stack


class JevCredentialBoundaryTests(unittest.TestCase):
    def test_utf8_even_and_odd_lengths_are_not_misdecoded_as_utf16(self):
        for text in ("abc123", "abc1234", "x"):
            with self.subTest(length=len(text)):
                vault = FakeVault({"target": text.encode("utf-8")})
                with vault.patches():
                    self.assertEqual(jev._cred_read("target"), text)
                vault.CredFree.assert_called_once()

    def test_utf16le_and_optional_nul_terminators_roundtrip(self):
        for text in ("abc123", "abc1234", "x"):
            for terminal in ("", "\0"):
                with self.subTest(length=len(text), terminal=bool(terminal)):
                    vault = FakeVault({"target": (text + terminal).encode("utf-16-le")})
                    with vault.patches():
                        self.assertEqual(jev._cred_read("target"), text)
                    vault.CredFree.assert_called_once()

    def test_utf8_nul_terminator_roundtrip(self):
        vault = FakeVault({"target": b"synthetic-key\0"})
        with vault.patches():
            self.assertEqual(jev._cred_read("target"), "synthetic-key")
        vault.CredFree.assert_called_once()

    def test_real_read_path_reconciles_equal_utf8_vault_and_env(self):
        target = jev.CREDVAULT_TARGETS[0]
        vault = FakeVault({target: b"abc123"})
        with patch.dict(os.environ, {jev.ENV_KEY: "abc123"}, clear=True), vault.patches():
            self.assertEqual(jev.load_key(), "abc123")
            self.assertEqual(jev.key_state(), f"KEY_PRESENT_CREDVAULT:{target}+ENV_MATCH")
        self.assertEqual(vault.CredFree.call_count, 2)

    def test_corrupt_or_empty_present_blob_never_enables_env_fallback(self):
        for blob in (b"", b"\0\0", b"\xff", b" \0 \0", b"a\0b", b"a\nb", b"\xff\xff"):
            with self.subTest(blob_size=len(blob)):
                vault = FakeVault({jev.CREDVAULT_TARGETS[0]: blob})
                with patch.dict(os.environ, {jev.ENV_KEY: "stale-key"}, clear=True), vault.patches():
                    with self.assertRaisesRegex(jev.JevError, "^KEY_SOURCE_UNAVAILABLE$"):
                        jev.load_key()
                    self.assertEqual(jev.key_state(), "KEY_SOURCE_UNAVAILABLE")
                self.assertEqual(vault.CredFree.call_count, 2)

    def test_absent_vault_is_distinct_from_unreadable_vault(self):
        for error in (5, 87, 1168):
            with self.subTest(error=error):
                vault = FakeVault(error=error)
                with patch.dict(os.environ, {jev.ENV_KEY: "env-key"}, clear=True), vault.patches():
                    if error == 1168:
                        self.assertEqual(jev.load_key(), "env-key")
                    else:
                        with self.assertRaisesRegex(jev.JevError, "^KEY_SOURCE_UNAVAILABLE$"):
                            jev.load_key()
                vault.CredFree.assert_not_called()

    def test_buffer_release_is_guaranteed_when_copy_fails(self):
        vault = FakeVault({"target": b"synthetic-key"})
        with vault.patches(), patch.object(jev.ctypes, "string_at", side_effect=OSError("copy failed")):
            with self.assertRaises(OSError):
                jev._cred_read("target")
        vault.CredFree.assert_called_once()

    def test_second_alias_failure_cannot_be_hidden_by_valid_first_alias(self):
        first, second = jev.CREDVAULT_TARGETS
        vault = FakeVault({first: b"valid-key", second: b""})
        with patch.dict(os.environ, {}, clear=True), vault.patches():
            with self.assertRaisesRegex(jev.JevError, "^KEY_SOURCE_UNAVAILABLE$"):
                jev.load_key()
        self.assertEqual(vault.CredFree.call_count, 2)

    def test_absent_sources_remain_no_key(self):
        vault = FakeVault()
        with patch.dict(os.environ, {}, clear=True), vault.patches():
            self.assertEqual(jev.load_key(), "")
            self.assertEqual(jev.key_state(), "NO_KEY")

    def test_invalid_env_key_is_typed_without_transport_or_value_disclosure(self):
        for key in ("synthetic\u2603key", "synthetic\0key", "synthetic\r\nkey", "synthetic key", "synthetic\x7fkey"):
            with self.subTest(kind=repr(key[-3:])):
                with patch.object(jev.os, "environ", {jev.ENV_KEY: key}), patch.object(jev, "_cred_read", return_value=""):
                    with self.assertRaisesRegex(jev.JevError, "^KEY_SOURCE_UNAVAILABLE$") as caught:
                        jev.load_key()
                    self.assertEqual(jev.key_state(), "KEY_SOURCE_UNAVAILABLE")
                    self.assertNotIn(key, str(caught.exception))

    def test_explicit_invalid_key_never_calls_transport(self):
        for key in ("synthetic\r\nkey", "synthetic\u2603key", "synthetic key", b"bytes-key", 123):
            with self.subTest(type=type(key).__name__):
                with patch.object(jev.urllib.request, "urlopen") as transport:
                    with self.assertRaisesRegex(jev.JevError, "^BAD_KEY$"):
                        jev.systemone("state", QUESTIONS, key=key)
                    transport.assert_not_called()

    def test_explicit_empty_key_remains_no_key(self):
        with patch.object(jev.urllib.request, "urlopen") as transport:
            with self.assertRaisesRegex(jev.JevError, "^NO_KEY$"):
                jev.systemone("state", QUESTIONS, key="")
            transport.assert_not_called()

    def test_oserror_and_timeout_are_typed_and_secret_free(self):
        key = "synthetic-boundary-secret"
        for error in (TimeoutError, ConnectionResetError, OSError):
            with self.subTest(error=error.__name__):
                with patch.object(jev.urllib.request, "urlopen", side_effect=error("transport " + key)):
                    with self.assertRaisesRegex(jev.JevError, "^TRANSPORT$") as caught:
                        jev.systemone("state", QUESTIONS, key=key)
                rendered = "".join(traceback.TracebackException.from_exception(caught.exception).format(chain=True))
                self.assertNotIn(key, rendered)
                self.assertTrue(caught.exception.__suppress_context__)

    def test_response_read_timeout_is_typed_and_response_is_closed(self):
        key = "synthetic-read-secret"
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.side_effect = TimeoutError(key)
        with patch.object(jev.urllib.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(jev.JevError, "^TRANSPORT$") as caught:
                jev.systemone("state", QUESTIONS, key=key)
        response.__exit__.assert_called_once()
        self.assertNotIn(key, "".join(traceback.TracebackException.from_exception(caught.exception).format(chain=True)))

    def test_mocked_success_keeps_request_contract_and_explicit_override(self):
        with patch.object(jev, "load_key", side_effect=AssertionError("explicit override must not read vault")), patch.object(
            jev.urllib.request, "urlopen", return_value=io.BytesIO(b'{"answers": {"route": {"value": "a"}}}')
        ) as transport:
            result = jev.systemone("state", QUESTIONS, key="explicit-key", timeout=7)
        self.assertIn("answers", result)
        request = transport.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer explicit-key")
        self.assertEqual(transport.call_args.kwargs, {"timeout": 7})


if __name__ == "__main__":
    unittest.main(verbosity=2)
