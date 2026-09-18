from __future__ import annotations

import json
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
        "--owner-fork", "owner/repo",
        "--target", "upstream/repo#842",
        "--stable-id", "operation-key",
        "--json",
    ]
    result = subprocess.run(
        [str(ENTRYPOINT), *forwarded], cwd=tmp_path, env=env,
        check=False, text=True, capture_output=True,
    )

    assert result.returncode == 22
    assert argv_log.read_text(encoding="utf-8").splitlines() == [
        str(EVALUATOR), *forwarded,
    ]


def test_entrypoint_real_help_tracks_current_parser() -> None:
    result = subprocess.run(
        [str(ENTRYPOINT), "--help"], cwd=ROOT,
        check=False, text=True, capture_output=True,
    )
    assert result.returncode == 0
    assert "--offline-report OFFLINE_REPORT" in result.stdout
    assert "--json" in result.stdout
    assert "--show-evidence" not in result.stdout
    assert "--self-test" not in result.stdout


def _base_report() -> dict:
    return {
        "input": {
            "owner_fork": "owner/repo",
            "upstream_pr_or_issue": "upstream/repo#842",
            "stable_id": "operation-key",
            "candidate_paths": [],
            "semantic_tokens": [],
        },
        "slack": {
            "stable_id_hits": [],
            "exact_target_hits": [],
            "path_semantic_hits": [],
        },
        "owner": {},
        "upstream": {"kind": "issue", "repo": "upstream/repo", "number": 842},
        "owner_pr_census": {"complete": True, "open_pr_count": 0, "hits": []},
        "blob_comparisons": [],
        "errors": [],
    }


def test_entrypoint_five_offline_decision_cases(tmp_path: Path) -> None:
    cases = []

    safe = _base_report()
    cases.append(("safe", safe, 0, "SAFE_TO_BIND_BRANCH"))

    owned = _base_report()
    owned["slack"]["stable_id_hits"] = [
        {"channel": "build-demand", "ts": "1", "text": "TAKE operation-key"}
    ]
    cases.append(("owned", owned, 20, "OWNED"))

    absorbed = _base_report()
    absorbed["upstream"]["kind"] = "pull"
    absorbed["blob_comparisons"] = [
        {"path": "src/fence.py", "comparable": True, "match": True}
    ]
    cases.append(("absorbed", absorbed, 21, "ALREADY_ABSORBED"))

    manual = _base_report()
    manual["errors"] = ["slack: incomplete evidence"]
    cases.append(("manual", manual, 22, "NEEDS_MANUAL_DIFF"))

    exact_pr = _base_report()
    exact_pr["owner_pr_census"]["hits"] = [
        {"number": 9, "strength": "exact", "reasons": ["stable_id"]}
    ]
    cases.append(("owner-pr", exact_pr, 20, "OWNED"))

    for name, report, expected_code, expected_decision in cases:
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        result = subprocess.run(
            [str(ENTRYPOINT), "--offline-report", str(path), "--json"],
            cwd=ROOT, check=False, text=True, capture_output=True,
        )
        assert result.returncode == expected_code, result.stderr
        payload = json.loads(result.stdout)
        assert payload["decision"] == expected_decision
        assert payload["branch_write_allowed"] is (expected_code == 0)
