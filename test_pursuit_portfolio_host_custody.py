from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from revenue.pursuit_portfolio import host
from revenue.pursuit_portfolio.current import AuthorityKey
from test_pursuit_portfolio_current import KEY, NOW, authority_for, source
from test_pursuit_portfolio_host_support import write_floor, write_key


@unittest.skipUnless(os.name == "posix", "descriptor custody requires POSIX")
class HostDescriptorCustodyTests(unittest.TestCase):
    def test_key_parent_swap_reads_retained_generation(self):
        attacker_key = AuthorityKey("attacker-root-v1", b"x" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live, attacker, parked = root / "host", root / "attacker", root / "parked"
            live.mkdir(mode=0o700)
            attacker.mkdir(mode=0o700)
            key_path = write_key(live, KEY)
            write_key(attacker, attacker_key)
            original = host._read_validated_host_leaf
            fired = False

            def swap_then_read(path, dir_fd, maximum, where):
                nonlocal fired
                if not fired:
                    fired = True
                    live.rename(parked)
                    attacker.rename(live)
                    try:
                        return original(path, dir_fd, maximum, where)
                    finally:
                        live.rename(attacker)
                        parked.rename(live)
                return original(path, dir_fd, maximum, where)

            with mock.patch.object(
                host._kernel,
                "_read_validated_host_leaf",
                side_effect=swap_then_read,
            ):
                loaded = host._load_host_key_from(key_path)
            self.assertTrue(fired)
            self.assertEqual(loaded, KEY)

    def test_floor_parent_swap_cannot_consume_attacker_generation(self):
        value = source()
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live, attacker, parked = root / "host", root / "attacker", root / "parked"
            live.mkdir(mode=0o700)
            attacker.mkdir(mode=0o700)
            floor_path = write_floor(live, authority, generation=1, updated_at=NOW)
            write_floor(attacker, authority, generation=99, updated_at=NOW)
            original = host._read_validated_host_leaf
            fired = False

            def swap_then_read(path, dir_fd, maximum, where):
                nonlocal fired
                if not fired:
                    fired = True
                    live.rename(parked)
                    attacker.rename(live)
                    try:
                        return original(path, dir_fd, maximum, where)
                    finally:
                        live.rename(attacker)
                        parked.rename(live)
                return original(path, dir_fd, maximum, where)

            with mock.patch.object(
                host._kernel,
                "_read_validated_host_leaf",
                side_effect=swap_then_read,
            ):
                loaded = host._load_host_floor_from(floor_path, KEY, NOW)
            self.assertTrue(fired)
            self.assertEqual(loaded.generation, 1)

    def test_key_and_floor_share_one_retained_root_generation(self):
        value = source()
        authority = authority_for(value)
        attacker_key = AuthorityKey("attacker-root-v1", b"x" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live, attacker, parked = root / "host", root / "attacker", root / "parked"
            live.mkdir(mode=0o700)
            attacker.mkdir(mode=0o700)
            write_key(live, KEY)
            write_floor(live, authority, KEY, generation=1, updated_at=NOW)
            write_key(attacker, attacker_key)
            write_floor(
                attacker,
                authority,
                attacker_key,
                generation=99,
                updated_at=NOW,
            )
            original = host._read_validated_host_leaf
            calls = 0
            swapped = False

            def swap_between_leaves(path, dir_fd, maximum, where):
                nonlocal calls, swapped
                raw = original(path, dir_fd, maximum, where)
                calls += 1
                if calls == 1:
                    live.rename(parked)
                    attacker.rename(live)
                    swapped = True
                elif calls == 2 and swapped:
                    live.rename(attacker)
                    parked.rename(live)
                    swapped = False
                return raw

            try:
                with mock.patch.object(
                    host._kernel,
                    "_read_validated_host_leaf",
                    side_effect=swap_between_leaves,
                ):
                    snapshot = host._load_host_authority_from(live, NOW)
            finally:
                if swapped:
                    live.rename(attacker)
                    parked.rename(live)
            self.assertEqual(calls, 2)
            self.assertEqual(snapshot.key, KEY)
            self.assertEqual(snapshot.floor.generation, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
