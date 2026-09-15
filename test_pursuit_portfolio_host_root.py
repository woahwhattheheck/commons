from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio import host
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.current import AuthorityKey, KEY_SCHEMA, _canonical, _now
from revenue.pursuit_portfolio.floor import FLOOR_SCHEMA
from test_pursuit_portfolio_current import KEY, portfolio_source, signed_authority_for


def _write_key(root: Path, key: AuthorityKey) -> Path:
    path = root / "authority-key.json"
    path.write_bytes(
        _canonical(
            {
                "schema": KEY_SCHEMA,
                "key_id": key.key_id,
                "key_hex": key.key.hex(),
            }
        )
    )
    if os.name == "posix":
        path.chmod(0o600)
    return path


def _write_floor(
    root: Path,
    authority: dict,
    key: AuthorityKey,
    *,
    generation: int = 1,
    updated_at: str,
) -> Path:
    authority_raw = _canonical(authority)
    unsigned = {
        "authority_sha256": hashlib.sha256(authority_raw).hexdigest(),
        "generation": generation,
        "key_id": key.key_id,
        "schema": FLOOR_SCHEMA,
        "updated_at": updated_at,
    }
    value = {
        **unsigned,
        "hmac_sha256": hmac.new(
            key.key,
            _canonical(unsigned),
            hashlib.sha256,
        ).hexdigest(),
    }
    path = root / "authority-floor.json"
    path.write_bytes(_canonical(value))
    if os.name == "posix":
        path.chmod(0o600)
    return path


@unittest.skipUnless(os.name == "posix", "effective-account host root requires POSIX")
class HostRootSelectionTests(unittest.TestCase):
    def test_attacker_home_with_self_consistent_host_tree_cannot_select_trust_root(self):
        import pwd

        now = _now()
        value = portfolio_source()
        attacker_key = AuthorityKey("attacker-root-1", b"x" * 32)
        authority = signed_authority_for(
            value,
            key=attacker_key,
            captured=now,
            issued_at=now,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            attacker_home = root / "attacker-home"
            attacker_host = attacker_home / ".config" / "commons" / "pursuit-portfolio"
            attacker_host.mkdir(parents=True, mode=0o700)
            _write_key(attacker_host, attacker_key)
            _write_floor(attacker_host, authority, attacker_key, updated_at=now)

            source_path = root / "input.json"
            source_path.write_bytes(_canonical(value))
            authority_path = root / "authority.json"
            authority_path.write_bytes(_canonical(authority))
            output_dir = root / "out"
            output_dir.mkdir(mode=0o700)

            env = os.environ.copy()
            env["HOME"] = str(attacker_home)
            repo_root = Path(__file__).resolve().parent
            expected_root = (
                Path(pwd.getpwuid(os.geteuid()).pw_dir)
                / ".config"
                / "commons"
                / "pursuit-portfolio"
            )

            probe = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import json, os, pwd; from pathlib import Path; "
                        "import revenue.pursuit_portfolio.host as host; "
                        "expected = Path(pwd.getpwuid(os.geteuid()).pw_dir) / '.config' / 'commons' / 'pursuit-portfolio'; "
                        "print(json.dumps({'root': str(host.HOST_ROOT), 'expected': str(expected)}))"
                    ),
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            observed = json.loads(probe.stdout)
            self.assertEqual(Path(observed["root"]), expected_root)
            self.assertEqual(Path(observed["expected"]), expected_root)
            self.assertNotEqual(Path(observed["root"]), attacker_host)

            compiled = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "revenue.pursuit_portfolio.cli",
                    "compile",
                    str(source_path),
                    str(authority_path),
                    str(output_dir),
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse((output_dir / "host-seal.json").exists())

    def test_key_parent_swap_after_validation_reads_retained_generation(self):
        attacker_key = AuthorityKey("attacker-root-1", b"x" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live = root / "host"
            attacker = root / "attacker"
            parked = root / "parked"
            live.mkdir(mode=0o700)
            attacker.mkdir(mode=0o700)
            attacker.chmod(0o777)
            key_path = _write_key(live, KEY)
            _write_key(attacker, attacker_key)

            original = host._read_validated_host_leaf
            fired = False

            def swap_then_read(path: Path, dir_fd: int, maximum: int, where: str) -> bytes:
                nonlocal fired
                if not fired and path.name == "authority-key.json":
                    fired = True
                    live.rename(parked)
                    attacker.rename(live)
                    try:
                        return original(path, dir_fd, maximum, where)
                    finally:
                        live.rename(attacker)
                        parked.rename(live)
                return original(path, dir_fd, maximum, where)

            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "_read_validated_host_leaf", side_effect=swap_then_read
            ):
                loaded = host._load_host_key()

            self.assertTrue(fired)
            self.assertEqual(loaded.key_id, KEY.key_id)
            self.assertEqual(loaded.key, KEY.key)
            self.assertNotEqual(loaded.key, attacker_key.key)

    def test_repeated_floor_reads_survive_parent_swap_without_consuming_attacker_tree(self):
        now = _now()
        value = portfolio_source()
        authority = signed_authority_for(value, captured=now, issued_at=now)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live = root / "host"
            attacker = root / "attacker"
            parked = root / "parked"
            live.mkdir(mode=0o700)
            attacker.mkdir(mode=0o700)
            attacker.chmod(0o777)
            key_path = _write_key(live, KEY)
            floor_path = _write_floor(live, authority, KEY, generation=1, updated_at=now)
            _write_floor(attacker, authority, KEY, generation=99, updated_at=now)

            original = host._read_validated_host_leaf
            swaps = 0

            def swap_then_read(path: Path, dir_fd: int, maximum: int, where: str) -> bytes:
                nonlocal swaps
                if path.name == "authority-floor.json":
                    live.rename(parked)
                    attacker.rename(live)
                    try:
                        raw = original(path, dir_fd, maximum, where)
                    finally:
                        live.rename(attacker)
                        parked.rename(live)
                    swaps += 1
                    return raw
                return original(path, dir_fd, maximum, where)

            with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                host, "HOST_FLOOR_PATH", floor_path
            ), mock.patch.object(
                host, "_read_validated_host_leaf", side_effect=swap_then_read
            ):
                compiled = host.compile_current(value, authority)

            self.assertEqual(swaps, 2)
            self.assertEqual(compiled.host_seal["authority_floor_generation"], 1)

    def test_host_key_hardlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path = _write_key(root, KEY)
            os.link(key_path, root / "authority-key-alias.json")
            with mock.patch.object(host, "HOST_KEY_PATH", key_path):
                with self.assertRaisesRegex(PortfolioError, "single-link retained file required"):
                    host._load_host_key()


if __name__ == "__main__":
    unittest.main(verbosity=2)
