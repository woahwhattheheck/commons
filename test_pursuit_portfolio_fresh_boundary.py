from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from revenue.pursuit_portfolio import current, fresh_boundary, fresh_exec, host
from revenue.pursuit_portfolio import fresh_worker_ops
from revenue.pursuit_portfolio.current import AuthorityKey
from test_pursuit_portfolio_current import KEY
from test_pursuit_portfolio_host_support import (
    cleanup_fixed_root,
    create_fixed_root,
    dynamic_generation,
    parse_utc,
    write_floor,
    write_key,
)


@unittest.skipUnless(os.name == "posix", "fresh current authority requires POSIX")
class FreshProcessBoundaryTests(unittest.TestCase):
    def test_parent_path_clock_and_helper_poison_cannot_cross_exec_boundary(self):
        value, authority, issued_at = dynamic_generation()
        created = create_fixed_root(self)
        root = host.HOST_ROOT
        public_compile = host.compile_current
        public_verify = host.verify_current
        poison_time = "2099-12-31T23:59:59Z"
        before = datetime.now(timezone.utc) - timedelta(seconds=3)

        try:
            write_key(root, KEY)
            write_floor(
                root,
                authority,
                KEY,
                updated_at=issued_at,
                generation=17,
            )
            with tempfile.TemporaryDirectory() as tmp:
                attacker_root = Path(tmp)
                attacker_key = AuthorityKey(KEY.key_id, b"x" * 32)
                poisoned = SimpleNamespace(poisoned=True)
                patches = [
                    mock.patch.object(host, "HOST_ROOT", attacker_root),
                    mock.patch.object(host, "HOST_KEY_PATH", attacker_root / "key"),
                    mock.patch.object(host, "HOST_FLOOR_PATH", attacker_root / "floor"),
                    mock.patch.object(host._kernel, "fixed_host_root", lambda: attacker_root),
                    mock.patch.object(host._kernel, "load_host_key", lambda: attacker_key),
                    mock.patch.object(host._kernel, "load_host_floor", lambda *_: poisoned),
                    mock.patch.object(host._kernel, "seal", lambda *_: {"forged": True}),
                    mock.patch.object(current, "compile_authorized_at", lambda *_: poisoned),
                    mock.patch.object(current, "verify_authorized_at", lambda *_: {"forged": True}),
                    mock.patch.object(current, "canonical_authority", lambda *_: ({}, b"{}\n")),
                    mock.patch.object(fresh_worker_ops, "now_utc", lambda: poison_time),
                    mock.patch.object(fresh_worker_ops, "compile_operation", lambda *_: {"ok": True}),
                    mock.patch.object(fresh_worker_ops, "verify_operation", lambda *_: {"ok": True}),
                    mock.patch.object(fresh_boundary, "os", poisoned),
                    mock.patch.object(fresh_boundary, "sys", poisoned),
                    mock.patch.object(fresh_exec, "os", poisoned),
                ]
                for patch in patches:
                    patch.start()
                try:
                    compiled = public_compile(value, authority)
                    authorized = compiled.authorized
                    verified = public_verify(
                        authorized.compiled.result_bytes,
                        authorized.compiled.markdown_bytes,
                        authorized.compiled.receipt_bytes,
                        authorized.authority_bytes,
                        authorized.current_receipt_bytes,
                        compiled.host_seal_bytes,
                    )
                finally:
                    for patch in reversed(patches):
                        patch.stop()

            after = datetime.now(timezone.utc) + timedelta(seconds=3)
            evaluated = parse_utc(compiled.authorized.compiled.result["evaluated_at"])
            verified_at = parse_utc(verified["verified_at"])
            self.assertLessEqual(before, evaluated)
            self.assertLessEqual(evaluated, after)
            self.assertLessEqual(before, verified_at)
            self.assertLessEqual(verified_at, after)
            self.assertNotEqual(
                compiled.authorized.compiled.result["evaluated_at"], poison_time
            )
            self.assertEqual(
                compiled.host_seal["authority_floor_generation"], 17
            )
            self.assertTrue(verified["host_seal_verified"])
            self.assertTrue(verified["verified_current"])
            self.assertNotIn("forged", verified)
        finally:
            cleanup_fixed_root(created)


if __name__ == "__main__":
    unittest.main(verbosity=2)
