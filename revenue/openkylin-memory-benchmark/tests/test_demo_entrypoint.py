import stat
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DemoEntrypointTests(unittest.TestCase):
    def test_documented_demo_runner_is_executable(self):
        mode = (ROOT / "run_demo.sh").stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
