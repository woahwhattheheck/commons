from __future__ import annotations

import json
import os
import pwd
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from revenue.pursuit_portfolio import host
from revenue.pursuit_portfolio.current import AuthorityKey
from test_pursuit_portfolio_current import authority_for, source
from test_pursuit_portfolio_host_support import write_floor, write_key


@unittest.skipUnless(os.name == "posix", "effective-account host root requires POSIX")
class HostRootSelectionTests(unittest.TestCase):
    def test_attacker_home_cannot_select_production_trust_root(self):
        value = source()
        attacker_key = AuthorityKey("attacker-root-v1", b"x" * 32)
        authority = authority_for(value)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            attacker_home = root / "attacker-home"
            attacker_host = attacker_home / ".config" / "commons" / "pursuit-portfolio"
            attacker_host.mkdir(parents=True, mode=0o700)
            write_key(attacker_host, attacker_key)
            write_floor(
                attacker_host,
                authority,
                attacker_key,
                updated_at="2026-09-13T14:00:00Z",
            )
            env = os.environ.copy()
            env["HOME"] = str(attacker_home)
            repo_root = Path(__file__).resolve().parent
            probe = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import json; "
                        "import revenue.pursuit_portfolio.host as h; "
                        "print(json.dumps({'root': str(h.HOST_ROOT)}))"
                    ),
                ],
                cwd=repo_root,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            expected = (
                Path(pwd.getpwuid(os.geteuid()).pw_dir)
                / ".config"
                / "commons"
                / "pursuit-portfolio"
            )
            self.assertEqual(Path(json.loads(probe.stdout)["root"]), expected)
            self.assertNotEqual(expected, attacker_host)


if __name__ == "__main__":
    unittest.main(verbosity=2)
