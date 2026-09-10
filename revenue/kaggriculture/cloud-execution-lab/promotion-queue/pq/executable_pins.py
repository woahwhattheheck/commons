# SPDX-License-Identifier: Apache-2.0
"""Submission-time input identity closure for the promotion queue.

The queue pin is the identity of one submission. Candidate inputs, declared
engine/runner identity files, and every configured predecessor panel/artifact
must therefore enter that pin before enqueueing. Reading any of those files
for the first time in ``Attempt.prepare`` lets one queue id be evaluated under
different bytes.

This module deliberately closes *input co-identity*, not panel provenance or a
full executable/import closure:

* ``pin_submission`` discovers, pins, and revalidates the complete declared
  queue-input set before a queue entry is admitted.
* ``require_config_pin`` binds the operator-supplied run config to the exact
  config submitted.
* ``bind_submission_config`` rejects incomplete/tampered/drifted inputs and
  rewrites engine, runner, predecessor-panel, and predecessor-artifact paths to
  immutable content-addressed blobs.
* ``ExecutablePinnedAttempt`` applies that boundary before the existing gate
  orchestration. Gate logic is not reimplemented.
"""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
from typing import Mapping

from .pinning import PinStore, canonical_json, sha256_file
from .runner import Attempt, RunError

BASE_SUBMISSION_INPUTS = (
    "candidate_artifact",
    "candidate_games",
    "policy",
    "predecessor_config",
    "engine_identity",
    "runner_identity",
)
# Backward-compatible public name for callers that need the invariant base.
# A complete submission also has two deterministic records per predecessor
# slot; use expected_submission_input_names(config) for the exact set.
REQUIRED_SUBMISSION_INPUTS = BASE_SUBMISSION_INPUTS
ROLE_INPUT_NAMES = {
    "engine": "engine_identity",
    "runner": "runner_identity",
}
SLOT_FIELDS = {
    "games": "games",
    "artifact_file": "artifact",
}


class ExecutablePinError(RunError):
    """Submission input closure is absent, malformed, tampered, or drifted."""


def _mapping(value, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ExecutablePinError(f"{label}: expected object")
    return value


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ExecutablePinError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise ExecutablePinError(f"non-finite JSON value: {value}")


def _validate_config(config, label: str) -> dict:
    config = _mapping(config, label)
    if config.get("schema_version") != 1:
        raise ExecutablePinError(f"{label}: schema_version must be 1")

    for role in ROLE_INPUT_NAMES:
        role_config = _mapping(config.get(role), f"{label} {role}")
        commit = role_config.get("commit")
        if not isinstance(commit, str) or len(commit) not in (40, 64):
            raise ExecutablePinError(
                f"{label} {role}.commit must be 40 or 64 hexadecimal characters"
            )
        try:
            int(commit, 16)
        except ValueError as exc:
            raise ExecutablePinError(
                f"{label} {role}.commit is not hexadecimal"
            ) from exc
        identity = role_config.get("identity_file")
        if not isinstance(identity, str) or not identity:
            raise ExecutablePinError(
                f"{label} {role}.identity_file must be a nonempty string"
            )

    slots = _mapping(config.get("slots"), f"{label} slots")
    if not slots:
        raise ExecutablePinError(f"{label}: needs at least one slot")
    names = []
    for slot_key, value in slots.items():
        if not isinstance(slot_key, str) or not slot_key:
            raise ExecutablePinError(
                f"{label}: predecessor slot keys must be nonempty strings"
            )
        slot = _mapping(value, f"{label} slot {slot_key!r}")
        name = slot.get("name")
        if not isinstance(name, str) or not name:
            raise ExecutablePinError(
                f"{label} slot {slot_key!r}.name must be a nonempty string"
            )
        names.append(name)
        for field in SLOT_FIELDS:
            value = slot.get(field)
            if not isinstance(value, str) or not value:
                raise ExecutablePinError(
                    f"{label} slot {slot_key!r}.{field} "
                    "must be a nonempty string"
                )
    if len(set(names)) != len(names):
        raise ExecutablePinError(f"{label}: predecessor slot names must be distinct")

    try:
        # Prove the parsed value is canonicalizable now, rather than letting a
        # custom Mapping or unsupported nested type escape later as a traceback.
        canonical_json(config)
    except (TypeError, ValueError) as exc:
        raise ExecutablePinError(f"{label}: not canonical JSON: {exc}") from exc
    return dict(config)


def load_submission_config(path: Path, *, label: str = "predecessor config") -> dict:
    """Load one config with duplicate-key and non-finite rejection."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ExecutablePinError(f"{label}: cannot read {path}: {exc}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except ExecutablePinError:
        raise
    except json.JSONDecodeError as exc:
        raise ExecutablePinError(
            f"{label}: invalid JSON at line {exc.lineno} column {exc.colno}"
        ) from exc
    return _validate_config(value, label)


def _slot_token(slot_key: str) -> str:
    """Return a reversible, manifest-key-safe token for one exact slot key."""
    if not isinstance(slot_key, str) or not slot_key:
        raise ExecutablePinError("predecessor slot key must be a nonempty string")
    return base64.urlsafe_b64encode(slot_key.encode("utf-8")).decode("ascii").rstrip("=")


def slot_input_name(slot_key: str, field: str) -> str:
    """Name the immutable submission record for one slot file.

    The config itself is pinned, so the encoded slot key plus field is a stable
    and collision-free semantic edge from config to manifest record.
    """
    if field not in SLOT_FIELDS:
        raise ExecutablePinError(f"unsupported predecessor slot field: {field}")
    return f"predecessor_slot.{_slot_token(slot_key)}.{SLOT_FIELDS[field]}"


def expected_submission_input_names(config: Mapping) -> tuple[str, ...]:
    """Return the exact input-name cardinality implied by a validated config."""
    config = _validate_config(config, "predecessor config")
    names = list(BASE_SUBMISSION_INPUTS)
    for slot_key in sorted(config["slots"]):
        for field in SLOT_FIELDS:
            names.append(slot_input_name(slot_key, field))
    if len(set(names)) != len(names):
        raise ExecutablePinError("predecessor slot input names are not unique")
    return tuple(names)


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
    size = record.get("bytes")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ExecutablePinError(
            f"submission input {name}: bytes must be a nonnegative integer"
        )
    return record


def _configured_path(section: Mapping, field: str, label: str) -> Path:
    value = section.get(field)
    if not isinstance(value, str) or not value:
        raise ExecutablePinError(f"{label}.{field} must be a nonempty string")
    path = Path(value)
    if not path.is_file():
        raise ExecutablePinError(f"{label}.{field} missing: {path}")
    return path


def _identity_path(config: Mapping, role: str) -> Path:
    role_config = _mapping(config.get(role), f"predecessor config {role}")
    return _configured_path(role_config, "identity_file", f"predecessor config {role}")


def _slot_path(config: Mapping, slot_key: str, field: str) -> Path:
    slots = _mapping(config.get("slots"), "predecessor config slots")
    slot = _mapping(slots.get(slot_key), f"predecessor config slot {slot_key!r}")
    return _configured_path(slot, field, f"predecessor config slot {slot_key!r}")


def _hash_path(path: Path, label: str) -> str:
    try:
        return sha256_file(path)
    except OSError as exc:
        raise ExecutablePinError(f"{label} cannot be hashed: {path}: {exc}") from exc


def submission_inputs(
    *,
    candidate_artifact: Path,
    candidate_games: Path,
    policy: Path,
    predecessor_config: Path,
) -> dict[str, Path]:
    """Discover the exact named input set that defines one submission."""
    config_path = Path(predecessor_config)
    config = load_submission_config(config_path)
    result = {
        "candidate_artifact": Path(candidate_artifact),
        "candidate_games": Path(candidate_games),
        "policy": Path(policy),
        "predecessor_config": config_path,
        "engine_identity": _identity_path(config, "engine"),
        "runner_identity": _identity_path(config, "runner"),
    }
    for slot_key in sorted(config["slots"]):
        for field in SLOT_FIELDS:
            result[slot_input_name(slot_key, field)] = _slot_path(
                config,
                slot_key,
                field,
            )
    expected = set(expected_submission_input_names(config))
    if set(result) != expected:
        raise ExecutablePinError("discovered submission-input cardinality mismatch")
    return result


def pin_submission(
    pins: PinStore,
    *,
    candidate_artifact: Path,
    candidate_games: Path,
    policy: Path,
    predecessor_config: Path,
    note: str = "",
) -> dict:
    """Pin and revalidate all declared inputs before queue admission.

    Pinning reads multiple files sequentially. A source can therefore change
    after discovery or between hashing and copying. Re-read the stored
    manifest, verify every blob, reload the live config, and bind every named
    engine/runner/slot file before returning. Any crossed snapshot remains
    unqueued.
    """
    config_path = Path(predecessor_config)
    tentative = pins.pin(
        submission_inputs(
            candidate_artifact=Path(candidate_artifact),
            candidate_games=Path(candidate_games),
            policy=Path(policy),
            predecessor_config=config_path,
        ),
        note=note,
    )
    try:
        stored = pins.get_pin(tentative["pin_id"])
    except (KeyError, OSError, json.JSONDecodeError) as exc:
        raise ExecutablePinError(
            f"stored submission pin cannot be read: {tentative.get('pin_id')}"
        ) from exc
    live_config = load_submission_config(config_path)
    bind_submission_config(pins, stored, live_config)
    return stored


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


def _bind_live_file(
    pins: PinStore,
    inputs: Mapping,
    *,
    input_name: str,
    live_path: Path,
    label: str,
) -> Path:
    """Require live bytes to match one stored record and return its blob path."""
    record = _record(inputs, input_name)
    expected = record["sha256"]
    observed = _hash_path(live_path, label)
    if observed != expected:
        raise ExecutablePinError(
            f"{label} drift: submission pinned {expected}, "
            f"live path {live_path} has {observed}"
        )
    try:
        blob_verified = pins.verify_blob(expected)
    except OSError as exc:
        raise ExecutablePinError(
            f"{label} blob cannot be verified: {expected}: {exc}"
        ) from exc
    if not blob_verified:
        raise ExecutablePinError(
            f"{label} blob missing or modified: {expected}"
        )
    try:
        return pins.blob_path(expected)
    except KeyError as exc:
        raise ExecutablePinError(
            f"{label} blob disappeared after verification: {expected}"
        ) from exc


def bind_submission_config(
    pins: PinStore,
    pin_manifest: Mapping,
    config: Mapping,
) -> dict:
    """Validate submission identity and bind all config-named files to blobs.

    ``config`` is compared semantically with the pinned predecessor config.
    Live engine, runner, predecessor-panel, and predecessor-artifact paths are
    then re-hashed. Only after every check passes are those paths replaced with
    submitted content-addressed blob paths for the existing ``Attempt``.
    """
    pin_manifest = _mapping(pin_manifest, "pin manifest")
    inputs = _mapping(pin_manifest.get("inputs"), "pin manifest inputs")
    base_missing = sorted(name for name in BASE_SUBMISSION_INPUTS if name not in inputs)
    if base_missing:
        raise ExecutablePinError(
            "submission pin lacks base input closure "
            f"({', '.join(base_missing)}); resubmit under the input-pin contract"
        )

    pin_id = pin_manifest.get("pin_id")
    if not isinstance(pin_id, str) or not pin_id:
        raise ExecutablePinError("pin manifest missing pin_id")
    try:
        stored_manifest = pins.get_pin(pin_id)
        if canonical_json(stored_manifest) != canonical_json(pin_manifest):
            raise ExecutablePinError(
                "presented pin manifest differs from stored manifest"
            )
        ok, problems = pins.verify_pin(pin_id)
    except ExecutablePinError:
        raise
    except (KeyError, OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ExecutablePinError(
            f"submission pin is malformed or unavailable: {pin_id}"
        ) from exc
    if not ok:
        raise ExecutablePinError(
            "submission pin verification failed: " + "; ".join(problems)
        )

    config = _validate_config(config, "supplied predecessor config")
    config_record = _record(inputs, "predecessor_config")
    try:
        pinned_config_path = pins.blob_path(config_record["sha256"])
    except KeyError as exc:
        raise ExecutablePinError(
            "pinned predecessor config blob is missing"
        ) from exc
    pinned_config = load_submission_config(
        pinned_config_path,
        label="pinned predecessor config",
    )
    if canonical_json(pinned_config) != canonical_json(config):
        raise ExecutablePinError(
            "predecessor config semantics differ from the submitted config"
        )

    expected_names = set(expected_submission_input_names(pinned_config))
    observed_names = set(inputs)
    missing = sorted(expected_names - observed_names)
    extra = sorted(observed_names - expected_names)
    if missing or extra:
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("extra=" + ",".join(extra))
        raise ExecutablePinError(
            "submission pin input cardinality differs from pinned config: "
            + "; ".join(details)
        )

    bound = copy.deepcopy(pinned_config)
    for role, input_name in ROLE_INPUT_NAMES.items():
        bound_path = _bind_live_file(
            pins,
            inputs,
            input_name=input_name,
            live_path=_identity_path(pinned_config, role),
            label=f"{role} identity",
        )
        bound[role]["identity_file"] = str(bound_path)

    for slot_key in sorted(pinned_config["slots"]):
        for field in SLOT_FIELDS:
            bound_path = _bind_live_file(
                pins,
                inputs,
                input_name=slot_input_name(slot_key, field),
                live_path=_slot_path(pinned_config, slot_key, field),
                label=f"predecessor slot {slot_key!r} {field}",
            )
            bound["slots"][slot_key][field] = str(bound_path)

    return bound


class ExecutablePinnedAttempt(Attempt):
    """Existing attempt runner with submission-time input binding."""

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
        try:
            return super().prepare(
                submission_id=submission_id,
                candidate_name=candidate_name,
                pin_manifest=pin_manifest,
                config=bound_config,
                policy=policy,
                strategy=strategy,
            )
        except RunError:
            raise
        except (KeyError, OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ExecutablePinError(
                f"pinned attempt preparation failed: {exc}"
            ) from exc
