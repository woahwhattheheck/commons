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
        self.assertIn("Commons Discord Health Watcher v1", script)
        self.assertIn("run_bridge_windows.ps1", script)
        self.assertIn("run_main_watcher_windows.ps1", script)
        self.assertIn("health_watch_windows_runtime.ps1", script)
        self.assertIn("New-ScheduledTaskTrigger -AtLogOn", script)
        self.assertIn("RepetitionInterval", script)
        self.assertIn("RestartCount 99", script)
        self.assertIn("Start-ScheduledTask", script)

    def test_installer_preserves_checkout_and_open_door(self):
        script = self.text("install_windows_runtime.ps1")
        for destructive in ("reset", "clean -", "Remove-Item", "Unregister-ScheduledTask"):
            self.assertNotIn(destructive, script)

    def test_health_watcher_restarts_only_the_exact_unhealthy_bridge_task(self):
        script = self.text("health_watch_windows_runtime.ps1")
        self.assertIn("http://127.0.0.1:18787/health", script)
        self.assertIn("curl.exe", script)
        self.assertIn("--max-time $TimeoutSec", script)
        self.assertIn("RetryCount = 6", script)
        self.assertIn("bounded startup grace period", script)
        self.assertIn('$body.node -eq "discord"', script)
        self.assertIn("schtasks.exe", script)
        self.assertIn("/End /TN $bridgeTask", script)
        self.assertIn("/Run /TN $bridgeTask", script)
        for destructive in ("reset", "clean -", "Remove-Item", "Unregister-ScheduledTask"):
            self.assertNotIn(destructive, script)

    def test_native_runners_drain_output_and_preserve_dirty_checkout(self):
        bridge = self.text("run_bridge_windows.ps1")
        watcher = self.text("run_main_watcher_windows.ps1")
        self.assertIn("commons_discord_bridge.py", bridge)
        self.assertIn("*> $null", bridge)
        self.assertIn("--untracked-files=no", watcher)
        self.assertIn("pull --ff-only --quiet origin main", watcher)
        self.assertIn("*> $null", watcher)
        for destructive in ("reset", "clean -", "Remove-Item", "Unregister-ScheduledTask"):
            self.assertNotIn(destructive, bridge + watcher)


if __name__ == "__main__":
    unittest.main()
