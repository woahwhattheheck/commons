from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

from . import AuthorityError, compile_current, verify_current_authority
from . import authority as a
from . import engine
from . import strict_json
from .cli import main as cli_main
from .current_runtime import assert_current_runtime
from .test_authority import packet


class FrozenCurrentRuntimeTests(unittest.TestCase):
    def _both_fail_closed(self) -> None:
        with self.assertRaises(AuthorityError):
            compile_current(packet())
        with self.assertRaises(AuthorityError):
            verify_current_authority(packet(), {})

    def test_guard_is_intact_immediately_after_import(self):
        self.assertIsNone(assert_current_runtime())

    def test_public_surfaces_have_no_trust_or_time_injection_parameters(self):
        self.assertEqual(tuple(inspect.signature(compile_current).parameters), ("packet",))
        self.assertEqual(tuple(inspect.signature(verify_current_authority).parameters), ("packet", "report"))
        self.assertEqual(tuple(inspect.signature(cli_main).parameters), ("argv",))
        with self.assertRaises(TypeError):
            compile_current(packet(), _clock=lambda: None)
        with self.assertRaises(TypeError):
            verify_current_authority(packet(), {}, _guard=lambda: True)

    def test_post_import_rebinding_of_authority_roots_fails_closed(self):
        mutations = (
            (a, "now_utc", lambda: None),
            (a, "_key", lambda: b"x" * 32),
            (a, "_load_current", lambda _key: ({}, "0" * 64)),
            (a, "_authority_status", lambda *_args, **_kwargs: {"authenticated": True}),
            (a, "canonical_json", lambda _value: "{}"),
            (a, "digest", lambda _value: "0" * 64),
            (a, "_compile_current_at", lambda *_args: {"state": a.READY}),
            (a, "_verify_current_at", lambda *_args: {"state": "CURRENT_VERIFIED"}),
        )
        for owner, name, replacement in mutations:
            with self.subTest(name=name), patch.object(owner, name, replacement):
                self._both_fail_closed()

    def test_post_import_rebinding_of_clock_and_json_graph_fails_closed(self):
        class FakeDateTime:
            @classmethod
            def now(cls, _tz=None):
                raise AssertionError("fake clock must never be authoritative")

        mutations = (
            (engine, "datetime", FakeDateTime),
            (strict_json.json, "dumps", lambda *_a, **_k: "{}"),
            (strict_json.json, "loads", lambda *_a, **_k: {}),
            (strict_json.hashlib, "sha256", lambda *_a, **_k: None),
        )
        for owner, name, replacement in mutations:
            with self.subTest(name=f"{getattr(owner, '__name__', type(owner).__name__)}.{name}"), patch.object(owner, name, replacement):
                self._both_fail_closed()

    def test_in_place_json_class_and_cached_encoder_mutation_fails_closed(self):
        mutations = (
            (strict_json.json.JSONEncoder, "encode", lambda self, _obj: "{}"),
            (strict_json.json.JSONDecoder, "decode", lambda self, _text, **_kw: {}),
            (strict_json.json._default_encoder, "encode", lambda _obj: "{}"),
            (strict_json.json._default_decoder, "decode", lambda _text, **_kw: {}),
        )
        for owner, name, replacement in mutations:
            with self.subTest(owner=type(owner).__name__, name=name), patch.object(owner, name, replacement):
                self._both_fail_closed()

    def test_post_import_rebinding_and_in_place_mac_graph_mutation_fails_closed(self):
        mutations = (
            (a.hmac, "new", lambda *_a, **_k: None),
            (a.hmac, "compare_digest", lambda *_a, **_k: True),
            (a.hashlib, "sha256", lambda *_a, **_k: None),
            (a.hmac.HMAC, "__init__", lambda self, *_a, **_k: None),
            (a.hmac.HMAC, "digest", lambda self: b"x" * 32),
        )
        for owner, name, replacement in mutations:
            with self.subTest(name=name), patch.object(owner, name, replacement):
                self._both_fail_closed()

    def test_runtime_recovers_after_temporary_rebinding_is_restored(self):
        original = a.now_utc
        with patch.object(a, "now_utc", lambda: None):
            self._both_fail_closed()
        self.assertIs(a.now_utc, original)
        assert_current_runtime()
        try:
            compile_current(packet())
        except AuthorityError as exc:
            self.assertNotIn("dependency graph changed", str(exc))


if __name__ == "__main__":
    unittest.main()
