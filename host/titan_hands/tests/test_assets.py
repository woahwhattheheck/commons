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
        self.assertIn("TITAN_HANDS_ANDROID_BACKEND=auto", script)

    def test_headless_setup_uses_verified_official_archive(self):
        script = (ROOT / "host" / "titan_hands" / "setup_android_headless.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("dl.google.com/android/repository/commandlinetools-win-", script)
        self.assertIn("90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a", script)
        self.assertIn("system-images;android-34;default;x86_64", script)

    def test_windows_launch_omits_argument_list_when_empty(self):
        script = (ROOT / "host" / "titan_hands_windows" / "backend.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("if ($arguments.Count -gt 0)", script)
        self.assertIn("$startParameters.ArgumentList = $arguments", script)
        self.assertIn("Start-Process @startParameters", script)

    def test_lda_installer_builds_the_owner_kotlin_and_probes_receiver(self):
        script = (ROOT / "host" / "titan_hands" / "install_lda_emulator.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn(":app:assembleDebug", script)
        self.assertIn("com.local.deviceagent/.TitanHandsReceiver", script)
        self.assertIn("ActionAccessibilityService", script)

    def test_receiver_exposes_marked_capture_op(self):
        receiver = (ROOT / "lda" / "app" / "src" / "main" / "java" / "com" / "local" / "deviceagent" / "TitanHandsReceiver.kt").read_text(
            encoding="utf-8"
        )
        overlay = (ROOT / "lda" / "app" / "src" / "main" / "java" / "com" / "local" / "deviceagent" / "TitanHandsMarks.kt").read_text(
            encoding="utf-8"
        )
        brain = (ROOT / "lda" / "app" / "src" / "main" / "java" / "com" / "local" / "deviceagent" / "AgentBrain.kt").read_text(
            encoding="utf-8"
        )
        self.assertIn('"capture"', receiver)
        self.assertIn("goAsync()", receiver)
        self.assertIn("captureScreenshot", receiver)
        self.assertIn("currentMarks()", receiver)
        self.assertIn("set-of-marks", receiver)
        self.assertIn("TitanHandsMarks.jpeg", receiver)
        self.assertIn("0xF01E88E5", overlay)
        self.assertIn("0x99FFC107", overlay)
        self.assertIn("marks.ids.getOrNull", overlay)
        self.assertIn("0xF01E88E5", brain)
        self.assertIn("0x99FFC107", brain)
        self.assertIn("Set-of-Marks", (ROOT / "host" / "titan_hands" / "mcp_server.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
