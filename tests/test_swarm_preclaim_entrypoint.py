from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "host" / "swarm_preclaim_fence.sh"
EVALUATOR = ROOT / "host" / "swarm_preclaim_fence.py"


def test_entrypoint_is_executable_and_valid_shell() -> None:
    mode = ENTRYPOINT.stat().st_mode
    assert mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(ENTRYPOINT)], check=True)


def test_entrypoint_forwards_arguments_and_exit_code(tmp_path: Path) -> None:
    fake_python = tmp_path / "fake-python"
    argv_log = tmp_path / "argv.log"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf \'%s\\n\' "$@" > "$FAKE_PYTHON_ARGV_LOG"\n'
        'exit "${FAKE_PYTHON_EXIT:-23}"\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PYTHON": str(fake_python),
            "FAKE_PYTHON_ARGV_LOG": str(argv_log),
            "FAKE_PYTHON_EXIT": "22",
        }
    )
    forwarded = [
        "--owner-fork",
        "owner/repo",
        "--target",
        "upstream/repo#842",
        "--stable-id",
        "operation-key",
    ]
    result = subprocess.run(
        [str(ENTRYPOINT), *forwarded],
        cwd=tmp_path,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 22
    assert argv_log.read_text(encoding="utf-8").splitlines() == [
        str(EVALUATOR),
        *forwarded,
    ]
