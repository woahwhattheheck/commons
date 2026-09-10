# SPDX-License-Identifier: Apache-2.0
"""Require exact opponent closure custody before consuming the Capillary verdict."""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any, Mapping

import bind_opponents as binding_core

HERE = Path(__file__).resolve().parent
PARENT_CASE = HERE.parent / "titan-v3-capillary-panel-sol-cambium"
PARENT_COMPARE_PATH = PARENT_CASE / "compare.py"
PARENT_COMPARE_GIT_BLOB = "add5584f4c3c29979c324b420a97b72ca80e1c2f"
PARENT_HEAD = binding_core.PARENT_HEAD
OPERATION = "titan-v3-capillary-opponent-closure-strict-compare-20260910-sol-pro-01"
EXPECTED_SOURCE_ENTRIES = {
    "arlene": {
        "entry": "arlene.py",
        "bytes": 46342,
        "sha256": "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4",
        "path_suffix": (
            "revenue/kaggriculture/cloud-execution-lab/runtime/variants/v1/"
            "reference/next-panel/vendor/arlene.py"
        ),
    },
    "v1": {
        "entry": "candidate.py",
        "bytes": 66,
        "sha256": "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2",
        "path_suffix": (
            "revenue/kaggriculture/cloud-execution-lab/runtime/variants/v1/candidate.py"
        ),
    },
}
EXPECTED_ORIGINS = {
    "arlene": {"entry": "arlene.py"},
    "v1": {
        "entry": "candidate.py",
        "mechanics": "mechanics.py",
        "scheduler": "scheduler.py",
        "scheduler.parent": "reference/next-panel/vendor/arlene.py",
        "scheduler.receipt_math": "reference/decision/decision.py",
    },
}


class ClosureCompareError(ValueError):
    """The panel verdict is not bound to exact opponent execution closures."""


def _regular_bytes(path: Path, label: str) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ClosureCompareError(f"cannot stat {label} {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ClosureCompareError(f"{label} is not one regular file: {path}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ClosureCompareError(f"cannot read {label} {path}: {exc}") from exc


def _identity(path: Path, label: str) -> dict[str, Any]:
    data = _regular_bytes(path, label)
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest(),
    }


def _load_parent_compare():
    data = _regular_bytes(PARENT_COMPARE_PATH, "parent comparator")
    actual = hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()
    if actual != PARENT_COMPARE_GIT_BLOB:
        raise ClosureCompareError(
            "parent comparator blob drift: "
            f"expected {PARENT_COMPARE_GIT_BLOB}, got {actual}"
        )
    name = "_sol_pro_exact_parent_capillary_compare"
    spec = importlib.util.spec_from_file_location(name, PARENT_COMPARE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load exact parent comparator: {PARENT_COMPARE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PARENT = _load_parent_compare()


def _lower_hex(value: Any, length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ClosureCompareError(f"{label} is not lowercase {length}-hex")
    return value


def _int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ClosureCompareError(f"{label} is not a nonnegative integer")
    return value


def _exact(value: Any, expected: Any, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ClosureCompareError(
            f"{label}: expected {expected!r}, got {value!r}"
        )


def _canonical_digest(value: Any) -> str:
    return binding_core.object_sha256(value)


def _input_digest(value: Any) -> str:
    try:
        return _canonical_digest(value)
    except (TypeError, ValueError) as exc:
        raise ClosureCompareError(f"input is not canonical JSON: {exc}") from exc


def _validate_identity(row: Any, label: str) -> dict[str, Any]:
    if not isinstance(row, Mapping):
        raise ClosureCompareError(f"{label} identity is missing")
    result = {
        "bytes": _int(row.get("bytes"), f"{label} bytes"),
        "sha256": _lower_hex(row.get("sha256"), 64, f"{label} sha256"),
        "git_blob_sha1": _lower_hex(
            row.get("git_blob_sha1"), 40, f"{label} git blob"
        ),
    }
    path = row.get("path")
    if path is not None:
        if not isinstance(path, str) or not path:
            raise ClosureCompareError(f"{label} path is invalid")
        result["path"] = path
    return result


def _validate_payload_files(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ClosureCompareError(f"{label} payload file inventory is empty")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise ClosureCompareError(f"{label} payload row {index} is invalid")
        path = binding_core.safe_relative(raw.get("path"), f"{label} payload path")
        if path in seen:
            raise ClosureCompareError(f"{label} payload path duplicated: {path}")
        seen.add(path)
        row = {
            "path": path,
            "bytes": _int(raw.get("bytes"), f"{label} payload bytes {path}"),
            "sha256": _lower_hex(
                raw.get("sha256"), 64, f"{label} payload sha256 {path}"
            ),
            "git_blob_sha1": _lower_hex(
                raw.get("git_blob_sha1"), 40, f"{label} payload git blob {path}"
            ),
        }
        rows.append(row)
    return rows


def validate_binding(
    binding: Mapping[str, Any],
    verification: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return wrapper identities after validating source/build/post-game custody."""
    _exact(binding.get("schema_version"), 1, "binding schema")
    _exact(binding.get("operation"), binding_core.OPERATION, "binding operation")
    _exact(binding.get("source_parent_head"), PARENT_HEAD, "binding parent head")
    head = _lower_hex(binding.get("git_head"), 40, "binding git head")
    _exact(audit.get("git_head"), head, "audit/binding git head")

    _exact(verification.get("schema_version"), 1, "verification schema")
    _exact(
        verification.get("operation"),
        binding_core.VERIFY_OPERATION,
        "verification operation",
    )
    _exact(verification.get("git_head"), head, "verification git head")
    _exact(
        verification.get("source_parent_head"),
        PARENT_HEAD,
        "verification parent head",
    )
    _exact(verification.get("verified"), True, "verification completion")
    _exact(
        verification.get("binding_object_sha256"),
        _canonical_digest(binding),
        "verification binding digest",
    )

    binder = _validate_identity(binding.get("binder"), "binding binder")
    verify_binder = _validate_identity(
        verification.get("binder"), "verification binder"
    )
    _exact(verify_binder, binder, "binder build/post-game identity")
    actual_binder = _identity(HERE / "bind_opponents.py", "local opponent binder")
    _exact(binder, actual_binder, "binding/local binder identity")

    freeze = binding.get("freeze")
    if not isinstance(freeze, Mapping):
        raise ClosureCompareError("binding freeze receipt is missing")
    _exact(
        freeze.get("sha256"),
        binding_core.EXPECTED_FREEZE_SHA256,
        "freeze sha256",
    )
    _exact(
        freeze.get("bytes"),
        binding_core.EXPECTED_FREEZE_BYTES,
        "freeze bytes",
    )
    _exact(
        freeze.get("runtime_files"),
        len(binding_core.EXPECTED_FILES),
        "freeze runtime file count",
    )
    full_source_closure = _lower_hex(
        freeze.get("source_closure_sha256"), 64, "freeze source closure"
    )

    audit_opponents = audit.get("opponents")
    build_opponents = binding.get("opponents")
    verify_opponents = verification.get("opponents")
    expected_names = set(EXPECTED_SOURCE_ENTRIES)
    if not isinstance(audit_opponents, Mapping) or set(audit_opponents) != expected_names:
        raise ClosureCompareError("audit opponent bank drift")
    if not isinstance(build_opponents, Mapping) or set(build_opponents) != expected_names:
        raise ClosureCompareError("binding opponent bank drift")
    if not isinstance(verify_opponents, Mapping) or set(verify_opponents) != expected_names:
        raise ClosureCompareError("verification opponent bank drift")

    wrappers: dict[str, dict[str, Any]] = {}
    wrapper_hashes: set[str] = set()
    for label in ("arlene", "v1"):
        expected = EXPECTED_SOURCE_ENTRIES[label]
        build = build_opponents[label]
        after = verify_opponents[label]
        if not isinstance(build, Mapping) or not isinstance(after, Mapping):
            raise ClosureCompareError(f"{label} opponent receipt is invalid")
        _exact(build.get("entry_name"), expected["entry"], f"{label} entry name")

        source_entry = _validate_identity(
            build.get("source_entry"), f"{label} source entry"
        )
        audit_entry = _validate_identity(
            audit_opponents[label], f"{label} audited source entry"
        )
        for key in ("bytes", "sha256", "git_blob_sha1"):
            _exact(
                source_entry[key], audit_entry[key], f"{label} audit/source {key}"
            )
        _exact(source_entry["bytes"], expected["bytes"], f"{label} source bytes")
        _exact(source_entry["sha256"], expected["sha256"], f"{label} source sha256")
        source_path = source_entry.get("path")
        if not isinstance(source_path, str) or not source_path.endswith(
            expected["path_suffix"]
        ):
            raise ClosureCompareError(f"{label} source path drift: {source_path!r}")

        source_closure = _lower_hex(
            build.get("source_closure_sha256"),
            64,
            f"{label} source closure",
        )
        payload = build.get("payload")
        if not isinstance(payload, Mapping):
            raise ClosureCompareError(f"{label} payload receipt is missing")
        _exact(payload.get("root"), f"{label}/payload", f"{label} payload root")
        payload_closure = _lower_hex(
            payload.get("closure_sha256"),
            64,
            f"{label} payload closure",
        )
        _exact(payload_closure, source_closure, f"{label} source/payload closure")
        payload_files = _validate_payload_files(
            payload.get("files"), label
        )
        _exact(
            binding_core.closure_sha256(payload_files),
            payload_closure,
            f"{label} payload inventory closure",
        )
        if label == "v1":
            _exact(
                payload_closure,
                full_source_closure,
                "frozen V1 full source/payload closure",
            )
            _exact(
                len(payload_files),
                len(binding_core.EXPECTED_FILES),
                "frozen V1 payload file count",
            )
            indexed_payload = {row["path"]: row for row in payload_files}
            _exact(
                set(indexed_payload),
                set(binding_core.EXPECTED_FILES),
                "frozen V1 payload path set",
            )
            for path, metadata in binding_core.EXPECTED_FILES.items():
                _exact(
                    indexed_payload[path]["bytes"],
                    metadata["bytes"],
                    f"frozen V1 payload bytes {path}",
                )
                _exact(
                    indexed_payload[path]["sha256"],
                    metadata["sha256"],
                    f"frozen V1 payload sha256 {path}",
                )
        else:
            _exact(len(payload_files), 1, "Arlene payload file count")
            _exact(payload_files[0]["path"], "arlene.py", "Arlene payload path")
            _exact(
                payload_files[0]["bytes"],
                EXPECTED_SOURCE_ENTRIES["arlene"]["bytes"],
                "Arlene payload bytes",
            )
            _exact(
                payload_files[0]["sha256"],
                EXPECTED_SOURCE_ENTRIES["arlene"]["sha256"],
                "Arlene payload sha256",
            )

        wrapper = _validate_identity(build.get("wrapper"), f"{label} wrapper")
        _exact(
            wrapper.get("path"),
            f"{label}/{expected['entry']}",
            f"{label} wrapper path",
        )
        if wrapper["sha256"] == source_entry["sha256"]:
            raise ClosureCompareError(f"{label} wrapper aliases entry-only identity")
        if wrapper["sha256"] in wrapper_hashes:
            raise ClosureCompareError("opponent wrapper hashes alias")
        wrapper_hashes.add(wrapper["sha256"])

        sidecar = _validate_identity(build.get("sidecar"), f"{label} sidecar")
        _exact(
            sidecar.get("path"),
            f"{label}/BINDING.json",
            f"{label} sidecar path",
        )
        probe = build.get("probe")
        if not isinstance(probe, Mapping):
            raise ClosureCompareError(f"{label} wrapper probe is missing")
        probe_binding = probe.get("binding")
        if not isinstance(probe_binding, Mapping):
            raise ClosureCompareError(f"{label} wrapper probe binding is missing")
        _exact(probe_binding.get("label"), label, f"{label} probe label")
        _exact(probe_binding.get("git_head"), head, f"{label} probe head")
        _exact(
            probe_binding.get("closure_sha256"),
            source_closure,
            f"{label} probe closure",
        )
        _exact(
            probe_binding.get("entry"), expected["entry"], f"{label} probe entry"
        )
        _exact(
            probe_binding.get("verified_origins"),
            EXPECTED_ORIGINS[label],
            f"{label} probe module origins",
        )

        _exact(
            _validate_identity(after.get("source_entry"), f"{label} verified source"),
            source_entry,
            f"{label} post-game source entry",
        )
        _exact(
            after.get("source_closure_sha256"),
            source_closure,
            f"{label} post-game source closure",
        )
        _exact(
            after.get("payload_closure_sha256"),
            payload_closure,
            f"{label} post-game payload closure",
        )
        _exact(
            _validate_identity(after.get("wrapper"), f"{label} verified wrapper"),
            wrapper,
            f"{label} post-game wrapper",
        )
        _exact(
            _validate_identity(after.get("sidecar"), f"{label} verified sidecar"),
            sidecar,
            f"{label} post-game sidecar",
        )
        _exact(after.get("probe"), probe, f"{label} post-game wrapper probe")
        wrappers[label] = wrapper
    return wrappers


def classify(
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    audit: Mapping[str, Any],
    evaluator_receipt: Mapping[str, Any],
    binding: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> dict[str, Any]:
    inputs = (control, candidate, audit, evaluator_receipt, binding, verification)
    before = tuple(_input_digest(value) for value in inputs)
    wrappers = validate_binding(binding, verification, audit)

    bound_audit = copy.deepcopy(audit)
    for label, wrapper in wrappers.items():
        bound_audit["opponents"][label] = dict(wrapper)

    report = PARENT.classify(
        control, candidate, bound_audit, evaluator_receipt
    )
    after = tuple(_input_digest(value) for value in inputs)
    if after != before:
        raise ClosureCompareError("strict classification mutated an input object")

    report = copy.deepcopy(report)
    report["parent_operation"] = report.get("operation")
    report["operation"] = OPERATION
    report["criteria"]["opponent_transitive_closure_bound"] = True
    report["advance"] = all(report["criteria"].values())
    report["verdict"] = "advance" if report["advance"] else "reject"
    report["causal_binding"]["opponent_execution_custody"] = (
        "each report fingerprint names a generated wrapper whose pre-import "
        "payload closure, post-import module origins, and post-panel bytes are "
        "bound to frozen V1 FREEZE.json"
    )
    report["opponent_binding"] = {
        label: {
            "source_entry_sha256": binding["opponents"][label]["source_entry"]["sha256"],
            "source_closure_sha256": binding["opponents"][label]["source_closure_sha256"],
            "wrapper_sha256": wrappers[label]["sha256"],
            "verified_origins": binding["opponents"][label]["probe"]["binding"]["verified_origins"],
        }
        for label in ("arlene", "v1")
    }
    report["identity"].update(
        {
            "source_parent_head": PARENT_HEAD,
            "parent_compare_git_blob_sha1": PARENT_COMPARE_GIT_BLOB,
            "opponent_binding_object_sha256": _canonical_digest(binding),
            "opponent_verification_object_sha256": _canonical_digest(verification),
            "strict_compare_sha256": _identity(
                Path(__file__).resolve(), "strict comparator"
            )["sha256"],
            "arlene_source_closure_sha256": binding["opponents"]["arlene"]["source_closure_sha256"],
            "arlene_wrapper_sha256": wrappers["arlene"]["sha256"],
            "v1_source_closure_sha256": binding["opponents"]["v1"]["source_closure_sha256"],
            "v1_wrapper_sha256": wrappers["v1"]["sha256"],
        }
    )
    return report


def markdown(report: Mapping[str, Any]) -> str:
    base = PARENT.markdown(report).rstrip()
    lines = [
        base,
        "",
        "## Opponent transitive-closure custody",
        "",
        "| Opponent | Source entry SHA-256 | Executable closure SHA-256 | Wrapper SHA-256 |",
        "|---|---|---|---|",
    ]
    for label in ("arlene", "v1"):
        row = report["opponent_binding"][label]
        lines.append(
            f"| {label} | `{row['source_entry_sha256']}` | "
            f"`{row['source_closure_sha256']}` | `{row['wrapper_sha256']}` |"
        )
    lines += [
        "",
        "The wrapper verifies its complete private payload before import, rejects "
        "ambient local-module collisions, attests loaded module origins, and is "
        "reprobed with all payload and wrapper bytes rehashed after both arms.",
        "",
    ]
    return "\n".join(lines)


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--evaluator-receipt", type=Path, required=True)
    parser.add_argument("--opponent-binding", type=Path, required=True)
    parser.add_argument("--opponent-verification", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    report = classify(
        binding_core.strict_object(args.control, "control report"),
        binding_core.strict_object(args.candidate, "candidate report"),
        binding_core.strict_object(args.audit, "source audit"),
        binding_core.strict_object(args.evaluator_receipt, "evaluator receipt"),
        binding_core.strict_object(args.opponent_binding, "opponent binding"),
        binding_core.strict_object(
            args.opponent_verification, "opponent verification"
        ),
    )
    atomic_text(
        args.output,
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )
    atomic_text(args.markdown, markdown(report))
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "criteria": report["criteria"],
                "metrics": report["metrics"],
                "opponent_binding": report["opponent_binding"],
            },
            sort_keys=True,
        )
    )
    return 0 if report["advance"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
