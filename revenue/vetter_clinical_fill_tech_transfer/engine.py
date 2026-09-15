from __future__ import annotations

"""Current-authority facade for the Vetter tech-transfer evidence gate.

The deterministic 2026-09-13 classifier is retained as inert source text in
``_engine_v1.txt``.  It is evaluated into a private namespace at import time,
then only current, process-clock-owned capabilities are exported from this
module.  Explicit-time replay lives in ``historical.py`` and has a distinct
schema and authority mode.
"""

import argparse
import errno
import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CURRENT_REPORT_SCHEMA = "vetter-clinical-fill-tech-transfer-current/v2"
CURRENT_VERIFY_SCHEMA = "vetter-clinical-fill-tech-transfer-current-verification/v2"
CURRENT_AUTHORITY_MODE = "CURRENT_OWNER_REVIEW"
CURRENT_REPORT_KEYS = {
    "schema",
    "authority_mode",
    "evaluated_at_utc",
    "decision",
    "current_receipt_sha256",
}


def _load_private_core() -> dict[str, Any]:
    source_path = Path(__file__).with_name("_engine_v1.txt")
    source = source_path.read_text(encoding="utf-8")
    namespace: dict[str, Any] = {
        "__name__": "vetter_tech_transfer_retained_core",
        "__file__": str(source_path),
    }
    exec(compile(source, str(source_path), "exec"), namespace, namespace)
    return namespace


def _install_snapshot_chronology(core: dict[str, Any]) -> None:
    original = core["normalize_snapshot"]
    parse_utc = core["parse_utc"]
    transfer_error = core["TransferError"]

    def repaired(
        value: object,
        name: str,
        *,
        expected_role: str,
        as_of: object,
    ) -> dict[str, object]:
        if type(value) is dict:
            captured_raw = value.get("captured_at_utc")
            rows = value.get("rows")
            if captured_raw is not None and type(rows) is list:
                captured = parse_utc(captured_raw, f"{name}.captured_at_utc")
                for idx, row in enumerate(rows):
                    if type(row) is not dict or "last_updated_utc" not in row:
                        continue
                    updated = parse_utc(
                        row["last_updated_utc"],
                        f"{name}.rows[{idx}].last_updated_utc",
                    )
                    if updated > captured:
                        raise transfer_error(
                            f"{name}.rows[{idx}].last_updated_utc is later than snapshot capture"
                        )
        return original(value, name, expected_role=expected_role, as_of=as_of)

    core["normalize_snapshot"] = repaired


_core = _load_private_core()
_install_snapshot_chronology(_core)

TransferError = _core["TransferError"]
canonical_json_bytes = _core["canonical_json_bytes"]
canonical_sha256 = _core["canonical_sha256"]
format_utc = _core["format_utc"]
load_json_bytes = _core["load_json_bytes"]
write_new_bytes = _core["write_new_bytes"]
write_new_text = _core["write_new_text"]
MAX_JSON_BYTES = int(_core["MAX_JSON_BYTES"])
_COMPILE_INPUT_KEYS = frozenset(_core["COMPILE_INPUT_KEYS"])
_SNAPSHOT_KEYS = frozenset(_core["SNAPSHOT_KEYS"])


def _build_current_capabilities(
    core: dict[str, Any],
    *,
    datetime_type: type[datetime],
    timezone_value: timezone,
):
    raw_compile = core["compile_transfer"]
    raw_verify = core["verify_report"]
    raw_render = core["render_markdown"]
    canonical = core["canonical_sha256"]
    formatter = core["format_utc"]
    transfer_error = core["TransferError"]
    snapshot_keys = frozenset(core["SNAPSHOT_KEYS"])

    def clock() -> str:
        return formatter(datetime_type.now(timezone_value))

    def seal(decision: dict[str, Any]) -> dict[str, Any]:
        core_value = {
            "schema": CURRENT_REPORT_SCHEMA,
            "authority_mode": CURRENT_AUTHORITY_MODE,
            "evaluated_at_utc": decision["as_of"],
            "decision": decision,
        }
        sealed = dict(core_value)
        sealed["current_receipt_sha256"] = canonical(core_value)
        return sealed

    def validate(report: object) -> dict[str, Any]:
        if type(report) is not dict or set(report) != CURRENT_REPORT_KEYS:
            raise transfer_error("current report key set is invalid")
        if report["schema"] != CURRENT_REPORT_SCHEMA:
            raise transfer_error("current report schema mismatch")
        if report["authority_mode"] != CURRENT_AUTHORITY_MODE:
            raise transfer_error("current report authority mode mismatch")
        receipt = report["current_receipt_sha256"]
        if type(receipt) is not str or len(receipt) != 64:
            raise transfer_error("current report receipt is invalid")
        without = {
            key: report[key]
            for key in report
            if key != "current_receipt_sha256"
        }
        if canonical(without) != receipt:
            raise transfer_error("current report receipt mismatch")
        decision = report["decision"]
        raw_verify(decision)
        if report["evaluated_at_utc"] != decision["as_of"]:
            raise transfer_error("current report evaluated time does not bind decision")
        return decision

    def plain_snapshot(snapshot: object, name: str) -> dict[str, Any]:
        if type(snapshot) is not dict:
            raise transfer_error(f"current report {name} must be an object")
        expected = set(snapshot_keys) | {"snapshot_sha256"}
        if set(snapshot) != expected:
            raise transfer_error(f"current report {name} key set invalid")
        return {key: snapshot[key] for key in snapshot_keys}

    def semantic_projection(decision: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in decision.items()
            if key not in {"as_of", "receipt_sha256"}
        }

    def compile_current(
        source: object,
        receiving: object,
        policy: object,
    ) -> dict[str, Any]:
        decision = raw_compile(source, receiving, policy, as_of=clock())
        return seal(decision)

    def verify_current(report: object) -> dict[str, Any]:
        decision = validate(report)
        now = clock()
        rebuilt = raw_compile(
            plain_snapshot(decision["source"], "source"),
            plain_snapshot(decision["receiving"], "receiving"),
            decision["policy"],
            as_of=now,
        )
        if semantic_projection(rebuilt) != semantic_projection(decision):
            raise transfer_error(
                "current report is no longer current: decision semantics changed at process UTC"
            )
        return {
            "schema": CURRENT_VERIFY_SCHEMA,
            "authority_mode": CURRENT_AUTHORITY_MODE,
            "verified": True,
            "current_as_of_utc": now,
            "decision_state": rebuilt["summary"]["state"],
            "report_receipt_sha256": report["current_receipt_sha256"],
            "decision_receipt_sha256": decision["receipt_sha256"],
            "current_decision_receipt_sha256": rebuilt["receipt_sha256"],
        }

    def render_current(report: object) -> str:
        decision = validate(report)
        legacy = raw_render(decision)
        prefix = [
            "# Current Authority Envelope",
            "",
            f"- Schema: `{CURRENT_REPORT_SCHEMA}`",
            f"- Authority mode: `{CURRENT_AUTHORITY_MODE}`",
            f"- Evaluated at process UTC: `{report['evaluated_at_utc']}`",
            f"- Current envelope receipt: `{report['current_receipt_sha256']}`",
            "",
        ]
        return "\n".join(prefix) + legacy

    return compile_current, verify_current, render_current


compile_transfer, verify_report_current, render_markdown = _build_current_capabilities(
    _core,
    datetime_type=datetime,
    timezone_value=timezone.utc,
)

# The retained explicit-time compiler and the factory used to construct current
# authority are deliberately not left on the importable current module surface.
del _core
del _build_current_capabilities
del _load_private_core
del _install_snapshot_chronology


def _fd_fingerprint(st: object) -> tuple[int, int, int, int, int, int]:
    return (
        int(st.st_dev),
        int(st.st_ino),
        int(st.st_mode),
        int(st.st_size),
        int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))),
        int(getattr(st, "st_ctime_ns", int(st.st_ctime * 1_000_000_000))),
    )


def _read_bounded(path: str | os.PathLike[str]) -> bytes:
    """Read one retained regular-file generation with an in-read hard cap."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise TransferError("secure no-follow input open is unavailable")
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EMLINK}:
            raise TransferError("input final symlink is forbidden") from None
        raise TransferError(
            f"unable to open input safely: {exc.strerror or exc}"
        ) from None

    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise TransferError("input must be a regular file")
        if before.st_size > MAX_JSON_BYTES:
            raise TransferError("input exceeds byte limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            remaining = MAX_JSON_BYTES + 1 - total
            if remaining <= 0:
                raise TransferError("input exceeds byte limit during read")
            chunk = os.read(fd, min(64 * 1024, remaining))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_JSON_BYTES:
                raise TransferError("input exceeds byte limit during read")
            chunks.append(chunk)
        after = os.fstat(fd)
        if _fd_fingerprint(before) != _fd_fingerprint(after):
            raise TransferError("input generation changed during read")
        if total != after.st_size:
            raise TransferError("input size changed during read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _compile_cli(args: argparse.Namespace) -> int:
    request = load_json_bytes(_read_bounded(args.input))
    if type(request) is not dict or set(request) != set(_COMPILE_INPUT_KEYS):
        raise TransferError("compile input key set is invalid")
    report = compile_transfer(
        request["source"], request["receiving"], request["policy"]
    )
    write_new_bytes(args.report, canonical_json_bytes(report))
    write_new_text(args.markdown, render_markdown(report))
    print(
        json.dumps(
            {
                "authority_mode": report["authority_mode"],
                "state": report["decision"]["summary"]["state"],
                "current_receipt_sha256": report["current_receipt_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


def _verify_cli(args: argparse.Namespace) -> int:
    report = load_json_bytes(_read_bounded(args.report))
    result = verify_report_current(report)
    if args.markdown:
        actual = _read_bounded(args.markdown).decode("utf-8")
        if actual != render_markdown(report):
            raise TransferError("Markdown projection mismatch")
    print(json.dumps(result, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only cross-site clinical fill tech-transfer current evidence compiler"
    )
    subs = parser.add_subparsers(dest="command", required=True)
    cp = subs.add_parser("compile")
    cp.add_argument("--input", required=True)
    cp.add_argument("--report", required=True)
    cp.add_argument("--markdown", required=True)
    cp.set_defaults(func=_compile_cli)
    vp = subs.add_parser("verify")
    vp.add_argument("--report", required=True)
    vp.add_argument("--markdown")
    vp.set_defaults(func=_verify_cli)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TransferError as exc:
        parser.error(str(exc))
    return 2


__all__ = [
    "TransferError",
    "compile_transfer",
    "verify_report_current",
    "render_markdown",
    "canonical_json_bytes",
    "canonical_sha256",
    "format_utc",
    "load_json_bytes",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
