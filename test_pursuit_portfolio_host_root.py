from __future__ import annotations

import hashlib
import hmac
import json
import os
import pwd
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.pursuit_portfolio.current import AuthorityKey, KEY_SCHEMA, _canonical
from revenue.pursuit_portfolio.floor import FLOOR_SCHEMA
from test_pursuit_portfolio_current import NOW, authority_for, source


@unittest.skipUnless(os.name == "posix", "effective-account host root requires POSIX")
class HostRootSelectionTests(unittest.TestCase):
    def test_attacker_home_with_self_consistent_host_tree_cannot_select_trust_root(self):
        value = source(max_age=86400 * 5)
        attacker_key = AuthorityKey("attacker-root-1", b"x" * 32)
        authority = authority_for(value, key=attacker_key)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            attacker_home = root / "attacker-home"
            attacker_host = attacker_home / ".config" / "commons" / "pursuit-portfolio"
            attacker_host.mkdir(parents=True, mode=0o700)

            key_value = {
                "schema": KEY_SCHEMA,
                "key_id": attacker_key.key_id,
                "key_hex": attacker_key.key.hex(),
            }
            key_path = attacker_host / "authority-key.json"
            key_path.write_bytes(_canonical(key_value))
            key_path.chmod(0o600)

            authority_raw = _canonical(authority)
            unsigned_floor = {
                "authority_sha256": hashlib.sha256(authority_raw).hexdigest(),
                "generation": 1,
                "key_id": attacker_key.key_id,
                "schema": FLOOR_SCHEMA,
                "updated_at": NOW,
            }
            floor = {
                **unsigned_floor,
                "hmac_sha256": hmac.new(
                    attacker_key.key,
                    _canonical(unsigned_floor),
                    hashlib.sha256,
                ).hexdigest(),
            }
            floor_path = attacker_host / "authority-floor.json"
            floor_path.write_bytes(_canonical(floor))
            floor_path.chmod(0o600)

            source_path = root / "input.json"
            source_path.write_bytes(_canonical(value))
            authority_path = root / "authority.json"
            authority_path.write_bytes(authority_raw)
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
