#!/usr/bin/env python3
"""Keep isolated scanner copies bound to the exact core their parent loaded."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent


class OpenDoorCorePointerTests(unittest.TestCase):
    def test_loaded_sibling_replaces_stale_inherited_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            stale = Path(temp) / "stale_core.py"
            stale.write_text(
                "raise RuntimeError('stale core must not be imported')\n",
                encoding="utf-8",
            )
            program = "\n".join(
                [
                    "import os",
                    "from pathlib import Path",
                    "import open_door_guard",
                    "loaded = Path(open_door_guard._core.__file__).resolve()",
                    "exported = Path(os.environ['OPEN_DOOR_GUARD_CORE']).resolve()",
                    "assert exported == loaded, (exported, loaded)",
                ]
            )
            environment = dict(os.environ)
            environment["OPEN_DOOR_GUARD_CORE"] = str(stale)
            completed = subprocess.run(
                [sys.executable, "-B", "-c", program],
                cwd=ROOT,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                completed.returncode,
                0,
                completed.stdout + completed.stderr,
            )


if __name__ == "__main__":
    unittest.main()
