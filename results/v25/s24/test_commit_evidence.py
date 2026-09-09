#!/usr/bin/env python3
"""Regression: unique S24 evidence must land on the live tip without force-push.

Reproduces run 34383948697: two serialized holdouts parented at the same
detached SHA; the first push advances the branch, the second sibling push
is non-fast-forward. The helper must fetch the live tip, add the unique
run-id path, and non-force push.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commit_evidence import GitError, commit_evidence, run_git  # type: ignore


def sh(cwd: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=check)


def init_user(repo: Path) -> None:
    sh(repo, ["git", "config", "user.name", "s24-test"])
    sh(repo, ["git", "config", "user.email", "s24-test@example.com"])
    sh(repo, ["git", "config", "commit.gpgsign", "false"])


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_harness() -> dict[str, Path]:
    root = Path(tempfile.mkdtemp(prefix="s24-nff-"))
    origin = root / "origin.git"
    sh(root, ["git", "init", "--bare", str(origin)])
    work = root / "work"
    sh(root, ["git", "clone", str(origin), str(work)])
    init_user(work)
    write_file(work / "README", "main\n")
    sh(work, ["git", "add", "README"])
    sh(work, ["git", "commit", "-m", "seed main"])
    sh(work, ["git", "branch", "-M", "main"])
    sh(work, ["git", "push", "-u", "origin", "main"])
    sh(work, ["git", "checkout", "-b", "sol/s24"])
    write_file(work / "workflow.yml", "holdout\n")
    sh(work, ["git", "add", "workflow.yml"])
    sh(work, ["git", "commit", "-m", "triggering head"])
    sh(work, ["git", "push", "-u", "origin", "sol/s24"])
    triggering = sh(work, ["git", "rev-parse", "HEAD"]).stdout.strip()
    return {
        "root": root,
        "origin": origin,
        "work": work,
        "triggering": Path(triggering),  # misuse Path as str holder
    }


def write_evidence(repo: Path, run_id: str, body: str) -> Path:
    dest = repo / "results" / "v25" / "s24" / "official-h" / f"run-{run_id}-1"
    write_file(dest / "SUMMARY.json", body)
    write_file(dest / "EXIT_CODE.txt", "0\n")
    return dest


def test_legacy_detached_push_is_non_fast_forward():
    h = make_harness()
    work = h["work"]
    triggering = str(h["triggering"])
    # First serialized run: commit evidence on detached triggering SHA (legacy).
    sh(work, ["git", "switch", "--detach", triggering])
    first = write_evidence(work, "111", '{"completed":384}\n')
    sh(work, ["git", "add", "--", str(first.relative_to(work))])
    sh(work, ["git", "commit", "-m", "evidence 111"])
    sh(work, ["git", "push", "origin", "HEAD:sol/s24"])
    # Second serialized run: same parent, unique path — legacy push rejected.
    sh(work, ["git", "switch", "--detach", triggering])
    second = write_evidence(work, "222", '{"completed":384,"run":222}\n')
    sh(work, ["git", "add", "--", str(second.relative_to(work))])
    sh(work, ["git", "commit", "-m", "evidence 222"])
    rejected = sh(work, ["git", "push", "origin", "HEAD:sol/s24"], check=False)
    assert rejected.returncode != 0, rejected.stdout + rejected.stderr
    assert "non-fast-forward" in (rejected.stderr + rejected.stdout)
    shutil.rmtree(h["root"])


def test_helper_lands_second_run_on_live_tip():
    h = make_harness()
    work = h["work"]
    triggering = str(h["triggering"])
    sh(work, ["git", "switch", "--detach", triggering])
    first = write_evidence(work, "111", '{"completed":384}\n')
    r1 = commit_evidence(work, first, "sol/s24", "111")
    assert r1["status"] == "pushed"
    sh(work, ["git", "switch", "--detach", triggering])
    second = write_evidence(work, "222", '{"completed":384,"run":222}\n')
    r2 = commit_evidence(work, second, "sol/s24", "222")
    assert r2["status"] == "pushed"
    assert r2["base"] == r1["sha"]
    # Live branch contains both unique trees and is a descendant of triggering.
    sh(work, ["git", "fetch", "origin", "sol/s24"])
    tip = sh(work, ["git", "rev-parse", "FETCH_HEAD"]).stdout.strip()
    sh(work, ["git", "switch", "--detach", tip])
    assert (work / "results/v25/s24/official-h/run-111-1/SUMMARY.json").read_text() == '{"completed":384}\n'
    assert (work / "results/v25/s24/official-h/run-222-1/SUMMARY.json").read_text() == '{"completed":384,"run":222}\n'
    merge_base = sh(work, ["git", "merge-base", triggering, tip]).stdout.strip()
    assert merge_base == triggering
    # No force was required; first parent of tip is the first evidence commit.
    parent = sh(work, ["git", "rev-parse", f"{tip}^"]).stdout.strip()
    assert parent == r1["sha"]
    shutil.rmtree(h["root"])


def test_helper_creates_branch_from_main_when_target_gone():
    h = make_harness()
    work = h["work"]
    sh(work, ["git", "push", "origin", "--delete", "sol/s24"])
    triggering = str(h["triggering"])
    sh(work, ["git", "switch", "--detach", triggering])
    ev = write_evidence(work, "333", '{"completed":384}\n')
    result = commit_evidence(work, ev, "sol/s24", "333")
    assert result["status"] == "pushed"
    sh(work, ["git", "fetch", "origin", "sol/s24"])
    tip = sh(work, ["git", "rev-parse", "FETCH_HEAD"]).stdout.strip()
    sh(work, ["git", "fetch", "origin", "main"])
    parent = sh(work, ["git", "rev-parse", f"{tip}^"]).stdout.strip()
    main = sh(work, ["git", "rev-parse", "origin/main"]).stdout.strip()
    assert parent == main
    sh(work, ["git", "switch", "--detach", tip])
    assert (work / "results/v25/s24/official-h/run-333-1/EXIT_CODE.txt").read_text() == "0\n"
    shutil.rmtree(h["root"])


def test_helper_refuses_overwrite_of_different_bytes():
    h = make_harness()
    work = h["work"]
    triggering = str(h["triggering"])
    ev = write_evidence(work, "444", '{"completed":384}\n')
    commit_evidence(work, ev, "sol/s24", "444")
    sh(work, ["git", "switch", "--detach", triggering])
    dest = write_evidence(work, "444", '{"tampered":true}\n')
    try:
        commit_evidence(work, dest, "sol/s24", "444")
        raise AssertionError("expected overwrite refusal")
    except GitError as exc:
        assert "different bytes" in str(exc)
    shutil.rmtree(h["root"])


def test_helper_idempotent_when_bytes_already_present():
    h = make_harness()
    work = h["work"]
    ev = write_evidence(work, "555", '{"completed":384}\n')
    first = commit_evidence(work, ev, "sol/s24", "555")
    sh(work, ["git", "fetch", "origin", "sol/s24"])
    sh(work, ["git", "switch", "--detach", "FETCH_HEAD"])
    again = commit_evidence(work, ev, "sol/s24", "555")
    assert again["status"] in {"already-present", "no-op"}
    assert first["sha"]
    shutil.rmtree(h["root"])


def test_run_git_refuses_force_flags():
    h = make_harness()
    work = h["work"]
    for args in (
        ["push", "--force", "origin", "HEAD:sol/s24"],
        ["push", "--force-with-lease", "origin", "HEAD:sol/s24"],
        ["push", "-f", "origin", "HEAD:sol/s24"],
        ["push", "-uf", "origin", "HEAD:sol/s24"],
    ):
        try:
            run_git(work, args)
            raise AssertionError(f"force args should fail: {args}")
        except GitError as exc:
            assert "force" in str(exc).lower() or "refusing" in str(exc).lower()
    shutil.rmtree(h["root"])


def test_workflow_delegates_to_helper():
    wf = Path(__file__).resolve().parents[3] / ".github/workflows/titan-s24-champion-freeze.yml"
    text = wf.read_text(encoding="utf-8")
    assert "results/v25/s24/commit_evidence.py" in text
    assert 'git push origin "HEAD:${GITHUB_HEAD_REF}"' not in text
    assert "commit_evidence.py" in text
    assert "Non-force push fails if the branch advanced past that source." not in text


if __name__ == "__main__":
    test_legacy_detached_push_is_non_fast_forward()
    test_helper_lands_second_run_on_live_tip()
    test_helper_creates_branch_from_main_when_target_gone()
    test_helper_refuses_overwrite_of_different_bytes()
    test_helper_idempotent_when_bytes_already_present()
    test_run_git_refuses_force_flags()
    test_workflow_delegates_to_helper()
    print("ok")
