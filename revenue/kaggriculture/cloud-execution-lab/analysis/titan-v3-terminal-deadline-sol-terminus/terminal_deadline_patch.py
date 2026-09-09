#!/usr/bin/env python3
"""Derive the one-factor TITAN terminal-deadline candidate from pinned sources.

This script never edits a repository checkout unless both canonical source blobs
match the exact reviewed preimages. It is intended for a clean detached worktree
whose exact HEAD descends from the reviewed source-preimage commit; the canonical
archive, pointers, configuration, and provider state are outside its scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Final

OPERATION: Final = "titan-v3-terminal-deadline-liquidation-preservation-20260909-01"
BASE_COMMIT: Final = "15d39ea7a9048c880b5185ed9797cd4af717b27f"
EXPECTED_BLOBS: Final = {
    "main.py": "4a8cf7bcda1f0fea231a144692cb84a779a9e73e",
    "titan_runtime.py": "b952c9c228ecbde592bf3d2df01638677abb0d24",
}

_MAIN_OLD: Final = '''def _entrypoint_fallback(instance, observation, configuration, deadline):
    """Return a completed current action, otherwise the visible-state fallback."""
    from copy import deepcopy
    selected = None if instance is None else getattr(instance, 'selected', None)
    if selected is not None:
        return deepcopy(selected)
    cfg = dict(configuration or {})
    obs = dict(observation)
    step = obs.get('step')
    if step is None:
        step = int(obs['day'])*int(cfg.get('turnsPerDay', 24))+int(obs['hour'])
    obs['step'] = int(step)
    last = int(cfg.get('episodeSteps', 720))-2
    return (deadline.terminal_liquidation_fallback(obs, cfg)
            if obs['step'] == last else deadline.legal_pass(obs))
'''

_MAIN_NEW: Final = '''def _entrypoint_fallback(instance, observation, configuration, deadline):
    """Keep terminal liquidation authoritative; otherwise reuse a selection."""
    from copy import deepcopy
    cfg = dict(configuration or {})
    obs = dict(observation)
    step = obs.get('step')
    if step is None:
        step = int(obs['day'])*int(cfg.get('turnsPerDay', 24))+int(obs['hour'])
    obs['step'] = int(step)
    last = int(cfg.get('episodeSteps', 720))-2
    if obs['step'] == last:
        return deadline.terminal_liquidation_fallback(obs, cfg)
    selected = None if instance is None else getattr(instance, 'selected', None)
    return deepcopy(selected) if selected is not None else deadline.legal_pass(obs)
'''

_RUNTIME_OLD: Final = '''                selected = self.production.act(obs)
                self.selected = deepcopy(selected)
                selected_checkpoint = (self.selected, self.controller.cur)
                fallback = selected_checkpoint[0]
                if self.quadrant is not None:
'''

_RUNTIME_NEW: Final = '''                selected = self.production.act(obs)
                self.selected = deepcopy(selected)
                selected_checkpoint = (self.selected, self.controller.cur)
                # At the final executable step, raw producer selection is not a
                # liquidation receipt. Preserve the visible-state fallback if
                # any downstream transform or finalizer exhausts the deadline.
                if obs['step'] != last:
                    fallback = selected_checkpoint[0]
                if self.quadrant is not None:
'''


class CandidateError(RuntimeError):
    """The candidate could not be derived exactly from the pinned source."""


def git_blob_sha(data: bytes) -> str:
    """Return the Git SHA-1 object id for exact blob bytes."""
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _replace_exact(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise CandidateError(f"{label}: expected one replacement site, found {count}")
    return text.replace(old, new, 1)


def patch_main(text: str) -> str:
    return _replace_exact(text, _MAIN_OLD, _MAIN_NEW, "main.py")


def patch_runtime(text: str) -> str:
    return _replace_exact(text, _RUNTIME_OLD, _RUNTIME_NEW, "titan_runtime.py")


def _git(lab: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(lab), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise CandidateError(f"cannot execute git for {lab}: {exc}") from exc


def _full_commit(value: str, label: str) -> str:
    commit = value.strip().lower()
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise CandidateError(f"{label} must be a full 40-character hexadecimal commit")
    return commit


def checkout_provenance(lab: Path, expected_head: str) -> dict[str, object]:
    """Bind a clean detached derivation checkout to an exact descendant HEAD."""
    lab = lab.resolve(strict=True)
    if not lab.is_dir() or lab.is_symlink():
        raise CandidateError(f"refusing non-directory lab root: {lab}")
    expected = _full_commit(expected_head, "expected derivation head")

    root_result = _git(lab, "rev-parse", "--show-toplevel")
    if root_result.returncode != 0:
        raise CandidateError(
            f"lab is not in a Git worktree: {root_result.stderr.strip() or lab}"
        )
    try:
        root = Path(root_result.stdout.strip()).resolve(strict=True)
        lab.relative_to(root)
    except (OSError, ValueError) as exc:
        raise CandidateError("lab root escaped its reported Git worktree") from exc

    head_result = _git(lab, "rev-parse", "--verify", "HEAD^{commit}")
    if head_result.returncode != 0:
        raise CandidateError(
            f"cannot resolve derivation HEAD: {head_result.stderr.strip()}"
        )
    actual = _full_commit(head_result.stdout, "actual derivation head")
    if actual != expected:
        raise CandidateError(
            f"derivation HEAD mismatch: expected {expected}, got {actual}"
        )

    ancestor = _git(lab, "merge-base", "--is-ancestor", BASE_COMMIT, actual)
    if ancestor.returncode == 1:
        raise CandidateError(
            f"reviewed source-preimage commit {BASE_COMMIT} is not an ancestor of {actual}"
        )
    if ancestor.returncode != 0:
        raise CandidateError(
            "cannot prove source-preimage ancestry: "
            f"{ancestor.stderr.strip() or ancestor.returncode}"
        )

    symbolic = _git(lab, "symbolic-ref", "-q", "HEAD")
    if symbolic.returncode == 0:
        raise CandidateError(
            f"derivation checkout must be detached, found {symbolic.stdout.strip()}"
        )
    if symbolic.returncode != 1:
        raise CandidateError(
            f"cannot verify detached HEAD: {symbolic.stderr.strip() or symbolic.returncode}"
        )

    status = _git(lab, "status", "--porcelain", "--untracked-files=no")
    if status.returncode != 0:
        raise CandidateError(f"cannot inspect derivation checkout: {status.stderr.strip()}")
    if status.stdout:
        raise CandidateError("derivation checkout is not clean before candidate generation")

    return {
        "source_preimage_commit": BASE_COMMIT,
        "source_preimage_commit_is_ancestor": True,
        "derivation_head": actual,
        "derivation_head_expected": expected,
        "derivation_detached_head": True,
        "derivation_checkout_clean_before_patch": True,
    }


def _read_exact(path: Path, expected_blob: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CandidateError(f"refusing non-regular source: {path}")
    data = path.read_bytes()
    actual = git_blob_sha(data)
    if actual != expected_blob:
        raise CandidateError(
            f"preimage mismatch for {path.name}: expected {expected_blob}, got {actual}"
        )
    return data


def _decode(data: bytes, name: str) -> str:
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CandidateError(f"{name}: source is not strict UTF-8") from exc


def _atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.terminus.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def apply_candidate(lab: Path) -> dict[str, object]:
    """Patch both pinned source preimages and return the semantic receipt."""
    lab = lab.resolve(strict=True)
    if not lab.is_dir() or lab.is_symlink():
        raise CandidateError(f"refusing non-directory lab root: {lab}")

    before: dict[str, bytes] = {}
    for name, expected in EXPECTED_BLOBS.items():
        before[name] = _read_exact(lab / name, expected)

    # Render and encode the full two-file candidate before mutating either file.
    rendered = {
        "main.py": patch_main(_decode(before["main.py"], "main.py")).encode("utf-8"),
        "titan_runtime.py": patch_runtime(
            _decode(before["titan_runtime.py"], "titan_runtime.py")
        ).encode("utf-8"),
    }
    if any(rendered[name] == before[name] for name in rendered):
        raise CandidateError("candidate must change both claimed sources")

    for name in ("main.py", "titan_runtime.py"):
        _atomic_write(lab / name, rendered[name])

    receipt: dict[str, object] = {
        "operation": OPERATION,
        "source_preimage_commit": BASE_COMMIT,
        "source_preimage_commit_role": "reviewed origin of exact source blobs",
        "changed_paths": ["main.py", "titan_runtime.py"],
        "before_git_blobs": {
            name: git_blob_sha(before[name]) for name in sorted(before)
        },
        "after_git_blobs": {
            name: git_blob_sha(rendered[name]) for name in sorted(rendered)
        },
        "semantic_delta": {
            "terminal_step": "visible-state liquidation remains fallback after selection",
            "nonterminal_steps": "completed producer selection remains fallback",
        },
        "canonical_runtime_mutated": False,
        "archive_or_pointer_mutated": False,
        "provider_or_submission_action": False,
        "score_or_promotion_claim": False,
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expect-head", required=True)
    args = parser.parse_args()

    provenance = checkout_provenance(args.lab, args.expect_head)
    receipt = apply_candidate(args.lab)
    receipt.update(provenance)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
