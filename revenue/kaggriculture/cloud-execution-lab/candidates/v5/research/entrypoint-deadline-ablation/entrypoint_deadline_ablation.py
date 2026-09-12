# SPDX-License-Identifier: Apache-2.0
"""Exact-source V3.1↔V4 whole-entrypoint deadline causal ablation.

This is an evidence materializer, never a production runtime hook.  It accepts
only the exact submitted V4 ``main.py`` and removes only the outer entrypoint
``_DeadlineTimer`` suffix from ``agent()``.  V4's producer, frozen seller,
FinalPressureAgent, town-procurement observation boundary, configuration and
TitanAgent runtime remain untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

V31_SOURCE_COMMIT = "a90d888f03987ef0b35cfd20ec3519c6144db08a"
V31_MAIN_GIT_BLOB = "b9db6c3ec9c64cb52ade0c26b23edf22710d77c9"
V4_SOURCE_COMMIT = "4af1113154e78c662780e6658cd920daac7902e3"
V4_MAIN_GIT_BLOB = "a015fef88d855d6d9c50f9d36e2551abd8829996"
PRE_GUARD_COMMIT = "784194262d1f448e5012c16503e8c2811e551c97"
PRE_GUARD_MAIN_GIT_BLOB = "06d7d7d3508403ce5e0eb53e673dede74055eae3"
INTRO_COMMIT = "4be7772ab850e50f42d0eb0fe715fecadb19ee10"
SCHEMA = "titan-v5-v31-v4-entrypoint-deadline-ablation-v1"

_GUARD_START = "    from titan_runtime import deadline\n"
_GUARD_END = "    return output\n"
_DIRECT_TAIL = (
    "    if replace:\n"
    "        instance = _new_instance(root, feature_data)\n"
    "        _INSTANCE = instance\n"
    "    return instance.act(observation, cfg, entry_started=entry_started)\n"
)


class SourceMismatch(ValueError):
    pass


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode(data: bytes, label: str) -> str:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceMismatch(f"{label}: source is not UTF-8") from exc
    if "\r\n" in text:
        raise SourceMismatch(f"{label}: CRLF source rejected")
    return text


def _require_blob(data: bytes, expected: str, label: str) -> None:
    actual = git_blob_sha1(data)
    if actual != expected:
        raise SourceMismatch(f"{label}: Git blob {actual} != {expected}")


def verify_authorities(v31: bytes, v4: bytes, pre_guard: bytes) -> dict[str, Any]:
    _require_blob(v31, V31_MAIN_GIT_BLOB, "submitted V3.1 main.py")
    _require_blob(v4, V4_MAIN_GIT_BLOB, "submitted V4 main.py")
    _require_blob(pre_guard, PRE_GUARD_MAIN_GIT_BLOB, "pre-guard main.py")

    v31_text = _decode(v31, "submitted V3.1 main.py")
    v4_text = _decode(v4, "submitted V4 main.py")
    pre_text = _decode(pre_guard, "pre-guard main.py")

    if "return _INSTANCE.act(observation, cfg, entry_started=entry_started)" not in v31_text:
        raise SourceMismatch("V3.1 direct-act boundary missing")
    if "_DeadlineTimer" in v31_text or "_entrypoint_fallback" in v31_text:
        raise SourceMismatch("V3.1 unexpectedly contains whole-entrypoint guard")

    if "class FinalPressureAgent" not in pre_text:
        raise SourceMismatch("pre-guard parent does not contain FinalPressureAgent")
    if "return _INSTANCE.act(observation, cfg, entry_started=entry_started)" not in pre_text:
        raise SourceMismatch("pre-guard parent direct-act boundary missing")
    if "_DeadlineTimer" in pre_text or "_entrypoint_fallback" in pre_text:
        raise SourceMismatch("pre-guard parent already contains whole-entrypoint guard")

    for anchor in (
        "class FinalPressureAgent",
        "def _entrypoint_fallback",
        "timer = deadline._DeadlineTimer(remaining)",
        "except deadline.DeadlineExceeded as error:",
        _GUARD_START.rstrip("\n"),
        _GUARD_END.rstrip("\n"),
    ):
        if anchor not in v4_text:
            raise SourceMismatch(f"V4 guard anchor missing: {anchor}")
    if v4_text.count(_GUARD_START) != 1 or v4_text.count(_GUARD_END) != 1:
        raise SourceMismatch("V4 guard splice anchors are not unique")
    if v4_text.index(_GUARD_START) < v4_text.index("def agent("):
        raise SourceMismatch("V4 guard start is outside agent()")

    return {
        "schema": SCHEMA,
        "v31_source_commit": V31_SOURCE_COMMIT,
        "v31_main_git_blob": V31_MAIN_GIT_BLOB,
        "v4_source_commit": V4_SOURCE_COMMIT,
        "v4_main_git_blob": V4_MAIN_GIT_BLOB,
        "pre_guard_commit": PRE_GUARD_COMMIT,
        "pre_guard_main_git_blob": PRE_GUARD_MAIN_GIT_BLOB,
        "guard_intro_commit": INTRO_COMMIT,
        "v31_main_sha256": sha256(v31),
        "v4_main_sha256": sha256(v4),
        "pre_guard_main_sha256": sha256(pre_guard),
    }


def ablate_v4_main(v4: bytes, *, expected_blob: str = V4_MAIN_GIT_BLOB) -> tuple[bytes, dict[str, Any]]:
    _require_blob(v4, expected_blob, "V4 treatment input main.py")
    text = _decode(v4, "V4 treatment input main.py")
    if text.count(_GUARD_START) != 1 or text.count(_GUARD_END) != 1:
        raise SourceMismatch("outer-guard splice anchors are not unique")
    start = text.index(_GUARD_START)
    end = text.index(_GUARD_END, start) + len(_GUARD_END)
    if start < text.index("def agent("):
        raise SourceMismatch("outer-guard splice does not belong to agent()")
    removed = text[start:end]
    for required in (
        "timer = deadline._DeadlineTimer(remaining)",
        "except deadline.DeadlineExceeded as error:",
        "return output",
    ):
        if required not in removed:
            raise SourceMismatch(f"outer-guard block missing: {required}")

    treated = (text[:start] + _DIRECT_TAIL + text[end:]).encode("utf-8")
    treated_text = _decode(treated, "treated V4 main.py")
    if "timer = deadline._DeadlineTimer(remaining)" in treated_text:
        raise SourceMismatch("outer timer survived treatment")
    if "return instance.act(observation, cfg, entry_started=entry_started)" not in treated_text:
        raise SourceMismatch("direct TitanAgent call missing from treatment")
    if treated_text[:start] != text[:start]:
        raise SourceMismatch("treatment mutated pre-guard V4 source")
    if "class FinalPressureAgent" not in treated_text or "town_procurement" not in treated_text:
        raise SourceMismatch("treatment lost V4 pressure/procurement source")

    receipt = {
        "schema": SCHEMA,
        "treatment": "remove-v4-whole-entrypoint-deadline-containment-only",
        "input_source_commit": V4_SOURCE_COMMIT,
        "input_main_git_blob": expected_blob,
        "input_main_sha256": sha256(v4),
        "output_main_git_blob": git_blob_sha1(treated),
        "output_main_sha256": sha256(treated),
        "preserved_prefix_sha256": sha256(text[:start].encode("utf-8")),
        "removed_guard_sha256": sha256(removed.encode("utf-8")),
        "replacement_tail_sha256": sha256(_DIRECT_TAIL.encode("utf-8")),
        "guard_intro_commit": INTRO_COMMIT,
        "pre_guard_commit": PRE_GUARD_COMMIT,
        "production_activation": False,
    }
    return treated, receipt


def _read(path: str) -> bytes:
    return Path(path).read_bytes()


def _write_new(path: str, data: bytes) -> None:
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"refusing to replace existing output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify")
    verify.add_argument("--v31", required=True)
    verify.add_argument("--v4", required=True)
    verify.add_argument("--pre-guard", required=True)

    materialize = sub.add_parser("materialize")
    materialize.add_argument("--v31", required=True)
    materialize.add_argument("--v4", required=True)
    materialize.add_argument("--pre-guard", required=True)
    materialize.add_argument("--out", required=True)
    materialize.add_argument("--receipt", required=True)

    args = parser.parse_args(argv)
    v31 = _read(args.v31)
    v4 = _read(args.v4)
    pre_guard = _read(args.pre_guard)
    authority = verify_authorities(v31, v4, pre_guard)

    if args.command == "verify":
        print(json.dumps(authority, sort_keys=True, separators=(",", ":")))
        return 0

    treated, receipt = ablate_v4_main(v4)
    receipt["authority"] = authority
    _write_new(args.out, treated)
    _write_new(
        args.receipt,
        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
