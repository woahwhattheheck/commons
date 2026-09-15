from __future__ import annotations

"""Explicit historical/test replay namespace.

Every explicit-time result is wrapped in a non-current schema with
``HISTORICAL_INTEGRITY_ONLY`` authority.  Nothing in this module can emit the
current report or current-verification schema used by ``engine.py``.
"""

from pathlib import Path
from typing import Any

HISTORICAL_REPORT_SCHEMA = "vetter-clinical-fill-tech-transfer-historical/v1"
HISTORICAL_VERIFY_SCHEMA = "vetter-clinical-fill-tech-transfer-historical-verification/v1"
HISTORICAL_AUTHORITY_MODE = "HISTORICAL_INTEGRITY_ONLY"
HISTORICAL_REPORT_KEYS = {
    "schema",
    "authority_mode",
    "historical_as_of_utc",
    "decision",
    "historical_receipt_sha256",
}


def _load_private_core() -> dict[str, Any]:
    source_path = Path(__file__).with_name("_engine_v1.txt")
    source = source_path.read_text(encoding="utf-8")
    namespace: dict[str, Any] = {
        "__name__": "vetter_tech_transfer_historical_core",
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


def _build_historical_capabilities(core: dict[str, Any]):
    raw_compile = core["compile_transfer"]
    raw_verify = core["verify_report"]
    raw_render = core["render_markdown"]
    canonical = core["canonical_sha256"]
    transfer_error = core["TransferError"]

    def seal(decision: dict[str, Any]) -> dict[str, Any]:
        # Raw decisions are first proven internally.  Historical wrapping never
        # upgrades their authority; it only binds replay provenance.
        raw_verify(decision)
        core_value = {
            "schema": HISTORICAL_REPORT_SCHEMA,
            "authority_mode": HISTORICAL_AUTHORITY_MODE,
            "historical_as_of_utc": decision["as_of"],
            "decision": decision,
        }
        wrapped = dict(core_value)
        wrapped["historical_receipt_sha256"] = canonical(core_value)
        return wrapped

    def validate(report: object) -> dict[str, Any]:
        if type(report) is not dict or set(report) != HISTORICAL_REPORT_KEYS:
            raise transfer_error("historical report key set is invalid")
        if report["schema"] != HISTORICAL_REPORT_SCHEMA:
            raise transfer_error("historical report schema mismatch")
        if report["authority_mode"] != HISTORICAL_AUTHORITY_MODE:
            raise transfer_error("historical report authority mode mismatch")
        receipt = report["historical_receipt_sha256"]
        if type(receipt) is not str or len(receipt) != 64:
            raise transfer_error("historical report receipt is invalid")
        without = {
            key: report[key]
            for key in report
            if key != "historical_receipt_sha256"
        }
        if canonical(without) != receipt:
            raise transfer_error("historical report receipt mismatch")
        decision = report["decision"]
        raw_verify(decision)
        if report["historical_as_of_utc"] != decision["as_of"]:
            raise transfer_error("historical report time does not bind decision")
        return decision

    def compile_historical(
        source: object,
        receiving: object,
        policy: object,
        *,
        as_of: str,
    ) -> dict[str, Any]:
        return seal(raw_compile(source, receiving, policy, as_of=as_of))

    def verify_historical(report: object) -> dict[str, Any]:
        decision = validate(report)
        return {
            "schema": HISTORICAL_VERIFY_SCHEMA,
            "authority_mode": HISTORICAL_AUTHORITY_MODE,
            "verified": True,
            "historical_as_of_utc": decision["as_of"],
            "historical_decision_state": decision["summary"]["state"],
            "historical_receipt_sha256": report["historical_receipt_sha256"],
            "decision_receipt_sha256": decision["receipt_sha256"],
        }

    def seal_existing(decision: object) -> dict[str, Any]:
        if type(decision) is not dict:
            raise transfer_error("historical decision must be an object")
        return seal(decision)

    def render_historical(report: object) -> str:
        decision = validate(report)
        legacy = raw_render(decision)
        prefix = [
            "# Historical Replay Envelope",
            "",
            f"- Schema: `{HISTORICAL_REPORT_SCHEMA}`",
            f"- Authority mode: `{HISTORICAL_AUTHORITY_MODE}`",
            f"- Historical as-of: `{report['historical_as_of_utc']}`",
            f"- Historical envelope receipt: `{report['historical_receipt_sha256']}`",
            "",
        ]
        return "\n".join(prefix) + legacy

    return compile_historical, verify_historical, seal_existing, render_historical


compile_transfer, verify_report, seal_existing_decision, render_markdown = (
    _build_historical_capabilities(_core)
)

# Do not leave the retained raw explicit-time compiler, verifier, or construction
# factory on this module's import surface.
del _core
del _build_historical_capabilities
del _load_private_core
del _install_snapshot_chronology

__all__ = [
    "TransferError",
    "HISTORICAL_REPORT_SCHEMA",
    "HISTORICAL_VERIFY_SCHEMA",
    "HISTORICAL_AUTHORITY_MODE",
    "compile_transfer",
    "verify_report",
    "seal_existing_decision",
    "render_markdown",
    "canonical_json_bytes",
    "canonical_sha256",
    "format_utc",
]
