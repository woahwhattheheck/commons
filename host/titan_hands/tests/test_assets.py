from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class AssetTests(unittest.TestCase):
    def test_codex_registration_is_direct_and_no_prompt(self):
        script = (ROOT / "host" / "titan_hands" / "register_codex.ps1").read_text(encoding="utf-8")
        self.assertIn("host.titan_hands.mcp_server", script)
        self.assertIn('default_tools_approval_mode = \"approve\"', script)
        self.assertIn("TITAN_HANDS_ANDROID_AUTOSTART=1", script)

    def test_headless_setup_uses_verified_official_archive(self):
        script = (ROOT / "host" / "titan_hands" / "setup_android_headless.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("dl.google.com/android/repository/commandlinetools-win-", script)
        self.assertIn("90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a", script)
        self.assertIn("system-images;android-34;default;x86_64", script)


if __name__ == "__main__":
    unittest.main()
