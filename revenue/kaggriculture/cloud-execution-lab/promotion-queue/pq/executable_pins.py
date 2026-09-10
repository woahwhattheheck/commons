# SPDX-License-Identifier: Apache-2.0
"""Submission-time executable closure for the promotion queue.

The ordinary queue pin is the identity of a submission.  Engine and runner
identity manifests therefore have to enter that pin before enqueueing; adding
them later in ``Attempt.prepare`` lets one queue id be evaluated by different
executables.

This module keeps the closure additive:

* ``submission_inputs`` expands the submission pin to include predecessor
  config, engine identity, and runner identity bytes.
* ``require_config_pin`` binds the operator-supplied run config to the exact
  config submitted.
* ``bind_submission_config`` rejects incomplete/tampered/drifted executable
  identities and rewrites only the identity-file paths to immutable blobs.
* ``ExecutablePinnedAttempt`` applies that boundary before the existing gate
  orchestration.  Gate logic is not reimplemented.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Mapping

from .pinning import PinStore, canonical_json, sha256_file
from .runner import Attempt, RunError, load_predecessor_config

REQUIRED_SUBMISSION_INPUTS = (
    "candidate_artifact",
    "candidate_games",
    "policy",
    "predecessor_config",
    "engine_identity",
    "runner_identity",
)
ROLE_INPUT_NAMES = {
    "engine": "engine_identity",
    "runner": "runner_identity",
}


class ExecutablePinError(RunError):
    """Executable closure is absent, malformed, tampered, or drifted."""


def _mapping(value, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ExecutablePinError(f"{label}: expected object")
    return value


def _record(inputs: Mapping, name: str) -> Mapping:
    record = _mapping(inputs.get(name), f"submission input {name}")
    digest = record.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ExecutablePinError(
            f"submission input {name}: expected 64-character sha256"
        )
    try:
        int(digest, 16)
    except ValueError as exc:
        raise ExecutablePinError(
            f"submission input {name}: sha256 is not hexadecimal"
        ) from exc
    return record


def _identity_path(config: Mapping, role: str) -> Path:
    role_config = _mapping(config.get(role), f"predecessor config {role}")
    value = role_config.get("identity_file")
    if not isinstance(value, str) or not value:
        raise ExecutablePinError(
            f"predecessor config {role}.identity_file must be a nonempty string"
        )
    path = Path(value)
    if not path.is_file():
        raise ExecutablePinError(
            f"predecessor config {role}.identity_file missing: {path}"
        )
    return path


def submission_inputs(
    *,
    candidate_artifact: Path,
    candidate_games: Path,
    policy: Path,
    predecessor_config: Path,
) -> dict[str, Path]:
    """Return the complete named input set that defines one queue submission."""
    config_path = Path(predecessor_config)
    config = load_predecessor_config(config_path)
    return {
        "candidate_artifact": Path(candidate_artifact),
        "candidate_games": Path(candidate_games),
        "policy": Path(policy),
        "predecessor_config": config_path,
        "engine_identity": _identity_path(config, "engine"),
        "runner_identity": _identity_path(config, "runner"),
    }


def require_config_pin(
    pin_manifest: Mapping,
    supplied_config_sha256: str | None,
) -> str:
    """Require run-time config bytes to equal the submission-time config."""
    inputs = _mapping(pin_manifest.get("inputs"), "pin manifest inputs")
    expected = _record(inputs, "predecessor_config")["sha256"]
    if supplied_config_sha256 != expected:
        got = supplied_config_sha256 or "<missing>"
        raise ExecutablePinError(
            "predecessor config drift: "
            f"submission pinned {expected}, run supplied {got}"
        )
    return expected


def bind_submission_config(
    pins: PinStore,
    pin_manifest: Mapping,
    config: Mapping,
) -> dict:
    """Validate executable closure and bind engine/runner to pinned blobs.

    ``config`` is compared semantically with the pinned predecessor config.
    The live identity-file paths are then re-hashed to detect a post-submit
    replacement.  Only after both checks pass are those paths replaced with
    content-addressed blob paths for the existing ``Attempt`` implementation.
    """
    inputs = _mapping(pin_manifest.get("inputs"), "pin manifest inputs")
    missing = sorted(name for name in REQUIRED_SUBMISSION_INPUTS if name not in inputs)
    if missing:
        raise ExecutablePinError(
            "submission pin lacks executable closure "
            f"({', '.join(missing)}); resubmit under the executable-pin contract"
        )

    pin_id = pin_manifest.get("pin_id")
    if not isinstance(pin_id, str) or not pin_id:
        raise ExecutablePinError("pin manifest missing pin_id")
    try:
        stored_manifest = pins.get_pin(pin_id)
    except KeyError as exc:
        raise ExecutablePinError(f"submission pin is not stored: {pin_id}") from exc
    if canonical_json(stored_manifest) != canonical_json(pin_manifest):
        raise ExecutablePinError("presented pin manifest differs from stored manifest")
    ok, problems = pins.verify_pin(pin_id)
    if not ok:
        raise ExecutablePinError(
            "submission pin verification failed: " + "; ".join(problems)
        )

    config_record = _record(inputs, "predecessor_config")
    pinned_config_path = pins.blob_path(config_record["sha256"])
    pinned_config = load_predecessor_config(pinned_config_path)
    if canonical_json(pinned_config) != canonical_json(config):
        raise ExecutablePinError(
            "predecessor config semantics differ from the submitted config"
        )

    bound = copy.deepcopy(pinned_config)
    for role, input_name in ROLE_INPUT_NAMES.items():
        record = _record(inputs, input_name)
        expected = record["sha256"]
        live_path = _identity_path(pinned_config, role)
        observed = sha256_file(live_path)
        if observed != expected:
            raise ExecutablePinError(
                f"{role} identity drift: submission pinned {expected}, "
                f"live path {live_path} has {observed}"
            )
        if not pins.verify_blob(expected):
            raise ExecutablePinError(
                f"{role} identity blob missing or modified: {expected}"
            )
        bound[role]["identity_file"] = str(pins.blob_path(expected))

    return bound


class ExecutablePinnedAttempt(Attempt):
    """Existing attempt runner with submission-time executable binding."""

    def prepare(
        self,
        *,
        submission_id: str,
        candidate_name: str,
        pin_manifest: Mapping,
        config: Mapping,
        policy: Mapping,
        strategy: str = "auto",
    ) -> dict:
        bound_config = bind_submission_config(self.pins, pin_manifest, config)
        return super().prepare(
            submission_id=submission_id,
            candidate_name=candidate_name,
            pin_manifest=pin_manifest,
            config=bound_config,
            policy=policy,
            strategy=strategy,
        )
