"""SYNTHETIC FIXTURE. Expected: UNDETERMINED — the screen cannot see inside."""
import subprocess


def run_lane_tests(lane_dir):
    return subprocess.run(
        ["python3", "-m", "unittest", "discover"],
        cwd=lane_dir, capture_output=True, text=True,
    )
