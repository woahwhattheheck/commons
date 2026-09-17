#!/usr/bin/env python3
"""Post-authenticated WHEAT carry census for TITAN V5 D2.

Research/evidence only. This module does not import or mutate gameplay policy.
It binds the retained D2 authentication receipt and independently compares the
exact source-derived `protect_feed_stock` withholding equation with the minimum
withholding required to preserve its certified WHEAT obligation.

If the two differ, the retained source contract is contradicted and the gate
fails closed. If they agree, there is no discretionary buffer at this seam and
no lean-feed candidate is authorized.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "titan-v5-d2-wheat-carry-census-v1"
STATUS_SCHEMA = "titan-v5-d2-recovery-status-v1"

D2_ARCHIVE_SHA256 = "3d250d7bd32bf51f26ec1f69c2c10bc3c914e7d0cf64a078ae5bac5832465bd8"
D2_ARCHIVE_BYTES = 424145
D2_MEMBER_COUNT = 94
AUTH_RECEIPT_SHA256 = "df11fce3b91bcf36ad280942ed38e1faed743ce3b23fbb6f8b8e8a5ada65fb46"
SAFE_MANIFEST_SHA256 = "d0c150d5be46a6f5e5b3275197c0f3279f4f7345b61e0ff917196db5a1eca84c"
RUNTIME_MEMBER = "titan_runtime.py"
RUNTIME_GIT_BLOB = "e0cdcf5a5dbe350d442d3b492795d37507449853"
OPERATING_STOCK_GIT_BLOB = "80b372bfd34d04a2c9e2376fa02917f21f659c41"
OFFICIAL_ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
HARNESS_SHA256 = "853850d8673cff0b21fdfe783e2dfcd539b8b2707bfe2d36c2e60d8ec2e43ea4"

STATE_AUTHENTICATED = "D2_SOURCE_AUTHENTICATED"
NEGATIVE = "NO_DISCRETIONARY_EXCESS_AT_CERTIFIED_WHEAT_SEAM"
UNCERTIFIED = "CURRENT_POLICY_UNCERTIFIED"
CONTRADICTION = "SOURCE_CONTRADICTION"
MAX_SHED_CAPACITY = 100
MAX_HELPER_WITHHOLD = 2


class WheatCensusError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise WheatCensusError(message)


def _whole(value: Any, label: str, *, maximum: int | None = None) -> int:
    _require(type(value) is int and value >= 0, f"{label} must be a non-negative exact int")
    if maximum is not None:
        _require(value <= maximum, f"{label} exceeds {maximum}")
    return value


def _strict_json_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    _require(len(raw) <= 64 * 1024, "status file too large")

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            _require(type(key) is str, "status key must be string")
            _require(key not in out, f"duplicate JSON key: {key}")
            out[key] = value
        return out

    def parse_int(token: str) -> int:
        _require(len(token.lstrip("-")) <= 128, "integer token too long")
        try:
            return int(token)
        except ValueError as exc:
            raise WheatCensusError("invalid integer token") from exc

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs_hook,
            parse_int=parse_int,
            parse_constant=lambda token: (_ for _ in ()).throw(
                WheatCensusError(f"non-finite JSON constant: {token}")
            ),
        )
    except UnicodeDecodeError as exc:
        raise WheatCensusError("status is not UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise WheatCensusError("status is not valid JSON") from exc
    _require(type(value) is dict, "status root must be object")
    return value


def default_status_path() -> Path:
    return Path(__file__).with_name("D2_RECOVERY_STATUS.json")


def validate_authenticated_status(path: Path | None = None) -> dict[str, Any]:
    """Validate the checked-in post-#15592 D2 source-authentication state."""
    status = _strict_json_object(default_status_path() if path is None else Path(path))
    _require(status.get("schema") == STATUS_SCHEMA, "wrong status schema")
    _require(status.get("state") == STATE_AUTHENTICATED, "D2 source is not authenticated")
    _require(status.get("source_authority_verified") is True, "root source authority must be true")
    _require(status.get("execution_inputs_ready") is True, "execution inputs are not ready")
    _require(status.get("candidate_build_authorized") is False, "status cannot authorize candidate")
    _require(status.get("promotion_authorized") is False, "status cannot authorize promotion")

    archive = status.get("archive")
    _require(type(archive) is dict, "archive status missing")
    _require(archive.get("sha256") == D2_ARCHIVE_SHA256, "wrong archive sha256")
    _require(archive.get("bytes") == D2_ARCHIVE_BYTES, "wrong archive byte count")
    _require(archive.get("member_count") == D2_MEMBER_COUNT, "wrong archive member count")

    auth = status.get("operator_host_archive_authentication")
    _require(type(auth) is dict, "operator archive authentication missing")
    _require(auth.get("source_authority_verified") is True, "nested source authority must be true")
    _require(auth.get("execution_inputs_ready") is True, "nested execution inputs not ready")
    _require(auth.get("receipt_sha256") == AUTH_RECEIPT_SHA256, "wrong auth receipt")
    _require(auth.get("safe_member_manifest_sha256") == SAFE_MANIFEST_SHA256, "wrong safe manifest")

    bindings = status.get("retained_source_bindings")
    _require(type(bindings) is dict, "retained bindings missing")
    expected = {
        "runtime_member": RUNTIME_MEMBER,
        "runtime_git_blob": RUNTIME_GIT_BLOB,
        "operating_stock_git_blob": OPERATING_STOCK_GIT_BLOB,
        "official_engine_sha256": OFFICIAL_ENGINE_SHA256,
        "harness_sha256": HARNESS_SHA256,
    }
    for key, expected_value in expected.items():
        _require(bindings.get(key) == expected_value, f"wrong retained binding: {key}")

    return {
        "state": STATE_AUTHENTICATED,
        "archive_sha256": D2_ARCHIVE_SHA256,
        "authentication_receipt_sha256": AUTH_RECEIPT_SHA256,
        "safe_member_manifest_sha256": SAFE_MANIFEST_SHA256,
        "runtime_member": RUNTIME_MEMBER,
        "runtime_git_blob": RUNTIME_GIT_BLOB,
        "operating_stock_git_blob": OPERATING_STOCK_GIT_BLOB,
        "official_engine_sha256": OFFICIAL_ENGINE_SHA256,
        "harness_sha256": HARNESS_SHA256,
    }


def minimum_required_withheld(
    observed_shed_wheat: int,
    eod_wheat_credit: int,
    required_wheat: int,
    offered_wheat: int,
) -> int:
    """Minimum current SELL-WHEAT units that must be withheld.

    This is derived independently as a balance equation: after the originally
    offered executable sale, how many units must be restored so retained stock
    plus certified EOD return still covers the source-proven obligation?
    """
    stock = _whole(observed_shed_wheat, "observed_shed_wheat", maximum=MAX_SHED_CAPACITY)
    returned = _whole(eod_wheat_credit, "eod_wheat_credit", maximum=MAX_SHED_CAPACITY)
    required = _whole(required_wheat, "required_wheat", maximum=MAX_SHED_CAPACITY * 2)
    offered = _whole(offered_wheat, "offered_wheat", maximum=MAX_SHED_CAPACITY)
    _require(required <= stock + returned, "observed wheat cannot cover source-proven obligation")
    executable_offer = min(stock, offered)
    remaining_if_unchanged = stock - executable_offer + returned
    return min(executable_offer, max(0, required - remaining_if_unchanged))


def source_current_policy_withheld(
    observed_shed_wheat: int,
    eod_wheat_credit: int,
    required_wheat: int,
    offered_wheat: int,
) -> int:
    """Exact arithmetic from D2 `operating_stock.protect_feed_stock`.

    This reproduces only the final certified WHEAT sale reservation equation,
    not the helper's earlier route/window/room proof. A caller must separately
    supply a certified runtime report before this can describe an observed cell.
    """
    stock = _whole(observed_shed_wheat, "observed_shed_wheat", maximum=MAX_SHED_CAPACITY)
    returned = _whole(eod_wheat_credit, "eod_wheat_credit", maximum=MAX_SHED_CAPACITY)
    required = _whole(required_wheat, "required_wheat", maximum=MAX_SHED_CAPACITY * 2)
    offered = _whole(offered_wheat, "offered_wheat", maximum=MAX_SHED_CAPACITY)
    _require(required <= stock + returned, "observed wheat cannot cover source-proven obligation")
    permitted = min(stock, max(0, stock + returned - required))
    withheld = max(0, min(stock, offered) - permitted)
    _require(withheld <= MAX_HELPER_WITHHOLD, "feed reservation exceeds source helper ceiling")
    return withheld


def analyze_certified_window(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one retained `protect_feed_stock` report and classify the seam."""
    _require(isinstance(packet, Mapping), "packet must be object")
    expected = {
        "observed_shed_wheat",
        "eod_wheat_credit",
        "required_wheat",
        "offered_wheat",
        "helper_report",
    }
    _require(set(packet) == expected, "packet key set mismatch")

    stock = _whole(packet["observed_shed_wheat"], "observed_shed_wheat", maximum=MAX_SHED_CAPACITY)
    returned = _whole(packet["eod_wheat_credit"], "eod_wheat_credit", maximum=MAX_SHED_CAPACITY)
    required = _whole(packet["required_wheat"], "required_wheat", maximum=MAX_SHED_CAPACITY * 2)
    offered = _whole(packet["offered_wheat"], "offered_wheat", maximum=MAX_SHED_CAPACITY)

    report = packet["helper_report"]
    _require(type(report) is dict, "helper_report must be object")
    if report.get("certified") is not True:
        return {
            "schema": SCHEMA,
            "state": UNCERTIFIED,
            "candidate_build_authorized": False,
            "promotion_authorized": False,
            "reason": str(report.get("reason", "uncertified current-policy window")),
        }

    current = source_current_policy_withheld(stock, returned, required, offered)
    minimum = minimum_required_withheld(stock, returned, required, offered)

    _require(report.get("required_wheat") == required, "helper required_wheat mismatch")
    _require(report.get("observed_shed_wheat") == stock, "helper observed_shed_wheat mismatch")
    _require(report.get("eod_wheat_credit") == returned, "helper eod_wheat_credit mismatch")
    _require(report.get("withheld_units") == current, "helper withheld_units mismatch")
    _require(report.get("changed") is (current > 0), "helper changed flag mismatch")

    if current != minimum:
        return {
            "schema": SCHEMA,
            "state": CONTRADICTION,
            "candidate_build_authorized": False,
            "promotion_authorized": False,
            "current_policy_withheld": current,
            "min_provable_withheld": minimum,
            "reason": "retained current-policy equation diverges from independent minimum balance",
        }

    saleable = min(stock, offered)
    plus_one = min(saleable, minimum + 1)
    return {
        "schema": SCHEMA,
        "state": NEGATIVE,
        "feed_item": "WHEAT",
        "mechanism": "selected_sell_wheat_reservation",
        "current_policy_withheld": current,
        "min_provable_withheld": minimum,
        "plus_one_withheld": plus_one,
        "discretionary_excess_units": 0,
        "cash_liberated_by_min_provable": 0,
        "cash_liberation_measurement": "ZERO_BY_EQUAL_WITHHOLDING_NO_PRICE_ASSUMPTION",
        "candidate_build_authorized": False,
        "promotion_authorized": False,
        "falsifier": "current certified helper reservation equals MIN_PROVABLE",
    }


def source_theorem_receipt(status_path: Path | None = None) -> dict[str, Any]:
    """Return the code/source-only negative result and its remaining evidence gap."""
    authority = validate_authenticated_status(status_path)
    return {
        "schema": SCHEMA,
        "state": NEGATIVE,
        "authority": authority,
        "scope": "certified operating_stock.protect_feed_stock WHEAT SELL reservation only",
        "theorem": (
            "For every supported certified window, the source current-policy "
            "withholding equation equals the independent minimum balance needed "
            "to preserve required_wheat after the offered executable sale."
        ),
        "candidate_build_authorized": False,
        "promotion_authorized": False,
        "empirical_result": None,
        "empirical_gate": (
            "No official-engine dev/holdout is authorized by this source theorem. "
            "Run retained observation census only to detect source/runtime drift; "
            "a candidate exists only if authenticated runtime behavior contradicts "
            "the retained source theorem, which must first be reviewed as drift."
        ),
    }
