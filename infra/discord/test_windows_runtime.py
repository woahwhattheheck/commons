import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class WindowsRuntimeTest(unittest.TestCase):
    def text(self, name: str) -> str:
        return (ROOT / name).read_text(encoding="utf-8")

    def test_installer_runs_real_bridge_and_fast_forward_watcher(self):
        script = self.text("install_windows_runtime.ps1")
        self.assertIn("Commons Discord Live Bridge v1", script)
        self.assertIn("Commons Discord Main Watcher v1", script)
        self.assertIn("commons_discord_bridge.py", script)
        self.assertIn("pull --ff-only --quiet origin main", script)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", script)
        self.assertIn("RepetitionInterval", script)
        self.assertIn("RestartCount 99", script)
        self.assertIn("Start-ScheduledTask", script)

    def test_installer_preserves_checkout_and_open_door(self):
        script = self.text("install_windows_runtime.ps1")
        for destructive in ("reset", "clean -", "Remove-Item", "Unregister-ScheduledTask"):
            self.assertNotIn(destructive, script)


if __name__ == "__main__":
    unittest.main()
