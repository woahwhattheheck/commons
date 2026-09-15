from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio import host
from revenue.pursuit_portfolio.core import PortfolioError
from revenue.pursuit_portfolio.current import AuthorityKey, KEY_SCHEMA, _canonical
from revenue.pursuit_portfolio.floor import FLOOR_SCHEMA
from test_pursuit_portfolio_current import KEY, NOW, authority_for, source


@unittest.skipUnless(os.name == "posix", "retained host dirfd tests require POSIX")
class HostRetainedDirfdTests(unittest.TestCase):
    def _key_file(self, root: Path, key: AuthorityKey = KEY) -> Path:
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
        path.chmod(0o600)
        return path

    def _floor_file(
        self,
        root: Path,
        authority: dict,
        *,
        generation: int,
        key: AuthorityKey = KEY,
    ) -> Path:
        path = root / "authority-floor.json"
        unsigned = {
            "authority_sha256": hashlib.sha256(_canonical(authority)).hexdigest(),
            "generation": generation,
            "key_id": key.key_id,
            "schema": FLOOR_SCHEMA,
            "updated_at": NOW,
        }
        value = {
            **unsigned,
            "hmac_sha256": hmac.new(
                key.key, _canonical(unsigned), hashlib.sha256
            ).hexdigest(),
        }
        path.write_bytes(_canonical(value))
        path.chmod(0o600)
        return path

    @staticmethod
    def _private_dir(path: Path) -> None:
        path.mkdir(mode=0o700)
        path.chmod(0o700)

    def test_key_read_stays_on_validated_directory_generation_after_swap(self) -> None:
        attacker_key = AuthorityKey(KEY.key_id, b"x" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live = root / "host"
            attacker = root / "attacker"
            retired = root / "retired"
            self._private_dir(live)
            self._private_dir(attacker)
            key_path = self._key_file(live, KEY)
            self._key_file(attacker, attacker_key)

            original_read = host._read_host_leaf
            swapped = False

            def racing_read(dir_fd: int, name: str, maximum: int, where: str) -> bytes:
                nonlocal swapped
                if name == key_path.name and not swapped:
                    live.rename(retired)
                    attacker.rename(live)
                    swapped = True
                return original_read(dir_fd, name, maximum, where)

            try:
                with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                    host, "_read_host_leaf", side_effect=racing_read
                ):
                    observed = host._load_host_key()
                self.assertTrue(swapped)
                self.assertEqual(observed, KEY)
                self.assertNotEqual(observed.key, attacker_key.key)
            finally:
                if retired.exists():
                    if live.exists():
                        live.rename(attacker)
                    retired.rename(live)

    def test_both_floor_reads_stay_on_each_validated_generation_after_swap(self) -> None:
        value = source(max_age=86400 * 5)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live = root / "host"
            attacker = root / "attacker"
            retired = root / "retired"
            self._private_dir(live)
            self._private_dir(attacker)
            key_path = self._key_file(live, KEY)
            floor_path = self._floor_file(live, authority, generation=1)
            self._key_file(attacker, KEY)
            self._floor_file(attacker, authority, generation=999)

            state = {"attacker_live": False, "floor_reads": 0}
            original_open = host._open_validated_host_parent
            original_read = host._read_host_leaf

            def restore_legitimate() -> None:
                if state["attacker_live"]:
                    live.rename(attacker)
                    retired.rename(live)
                    state["attacker_live"] = False

            def swap_after_validation() -> None:
                if state["attacker_live"]:
                    raise AssertionError("attacker tree already live")
                live.rename(retired)
                attacker.rename(live)
                state["attacker_live"] = True

            def racing_open(path: Path, where: str) -> int:
                if path.name == floor_path.name:
                    restore_legitimate()
                return original_open(path, where)

            def racing_read(dir_fd: int, name: str, maximum: int, where: str) -> bytes:
                if name == floor_path.name:
                    state["floor_reads"] += 1
                    swap_after_validation()
                return original_read(dir_fd, name, maximum, where)

            try:
                with mock.patch.object(host, "HOST_KEY_PATH", key_path), mock.patch.object(
                    host, "HOST_FLOOR_PATH", floor_path
                ), mock.patch.object(
                    host, "_open_validated_host_parent", side_effect=racing_open
                ), mock.patch.object(
                    host, "_read_host_leaf", side_effect=racing_read
                ):
                    compiled = host.compile_current(value, authority)
                self.assertEqual(state["floor_reads"], 2)
                self.assertEqual(compiled.host_seal["authority_floor_generation"], 1)
                self.assertNotEqual(compiled.host_seal["authority_floor_generation"], 999)
            finally:
                restore_legitimate()

    def test_private_host_key_must_have_single_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path = self._key_file(root)
            os.link(key_path, root / "authority-key-hardlink.json")
            with mock.patch.object(host, "HOST_KEY_PATH", key_path):
                with self.assertRaisesRegex(PortfolioError, "single-link retained file required"):
                    host._load_host_key()


if __name__ == "__main__":
    unittest.main(verbosity=2)
