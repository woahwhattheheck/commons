from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import stat
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

CONTRACT_SCHEMA = "receipt-trust-boundary/contract-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TrustError(ValueError):
    """Raised when evidence cannot satisfy the trust-boundary contract."""


def _pairs_no_duplicates(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise TrustError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _parse_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise TrustError("non-finite JSON number is forbidden")
    return value


def _reject_constant(text: str) -> None:
    raise TrustError(f"non-finite JSON constant is forbidden: {text}")


def load_json_bytes(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TrustError("input must be UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs_no_duplicates,
            parse_float=_parse_float,
            parse_constant=_reject_constant,
        )
    except TrustError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise TrustError(f"invalid JSON: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TrustError(f"value is not canonical JSON: {exc}") from exc


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def read_plain_file(path: Path) -> bytes:
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise TrustError(f"cannot stat input: {path}") from exc
    if not stat.S_ISREG(before.st_mode):
        raise TrustError(f"input must be an ordinary regular file: {path}")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise TrustError(f"cannot open input as a plain file: {path}") from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise TrustError(f"input must be a regular file: {path}")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise TrustError(f"input identity changed while opening: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
        if (
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise TrustError(f"input changed while reading: {path}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _require_object(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TrustError(f"{name} must be a JSON object")
    return value


def unsigned_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(receipt)
    out.pop("receipt_sha256", None)
    return out


def compute_self_digest(receipt: Mapping[str, Any]) -> str:
    """Return the receipt's integrity-only digest.

    This digest is useful for corruption/tamper detection only. Because it can be
    recomputed by whoever edits the receipt, it is never an authenticity root.
    """

    return sha256_value(unsigned_receipt(receipt))


def attach_integrity_digest(receipt: Mapping[str, Any]) -> dict[str, Any]:
    out = deepcopy(dict(receipt))
    out.pop("receipt_sha256", None)
    out["receipt_sha256"] = compute_self_digest(out)
    return out


def inspect_receipt(receipt: Any) -> dict[str, Any]:
    receipt_obj = _require_object(receipt, "receipt")
    claimed = receipt_obj.get("receipt_sha256")
    digest_shape_ok = _valid_sha256(claimed)
    recomputed = compute_self_digest(receipt_obj)
    self_digest_matches = bool(
        digest_shape_ok and hmac.compare_digest(str(claimed), recomputed)
    )
    return {
        "schema": "receipt-trust-boundary/inspection-v1",
        "status": "INTEGRITY_ONLY" if self_digest_matches else "INTEGRITY_UNPROVEN",
        "receipt_sha256": claimed if digest_shape_ok else None,
        "recomputed_receipt_sha256": recomputed,
        "self_digest_matches": self_digest_matches,
        "external_commitment_verified": False,
        "semantic_contract_verified": False,
        "source_authenticity_verified": False,
        "buyer_acceptance_verified": False,
        "contract_execution_verified": False,
        "payment_verified": False,
        "recognized_revenue_verified": False,
    }


def bind_external_commitment(receipt: Any, expected_receipt_sha256: str) -> dict[str, Any]:
    receipt_obj = _require_object(receipt, "receipt")
    if not _valid_sha256(expected_receipt_sha256):
        raise TrustError("external receipt commitment must be a lowercase SHA-256")
    inspected = inspect_receipt(receipt_obj)
    if not inspected["self_digest_matches"]:
        raise TrustError("receipt self-digest mismatch")
    claimed = receipt_obj["receipt_sha256"]
    if not hmac.compare_digest(claimed, expected_receipt_sha256):
        raise TrustError("external receipt commitment mismatch")
    return {
        **inspected,
        "schema": "receipt-trust-boundary/commitment-v1",
        "status": "EXTERNAL_COMMITMENT_BOUND",
        "external_commitment_verified": True,
        "external_commitment_sha256": expected_receipt_sha256,
        "trust_root_supplied_by_caller": True,
        # A commitment proves stability relative to the supplied trust root. It
        # does not identify who created the underlying facts.
        "source_authenticity_verified": False,
    }


def _typed_equal(left: Any, right: Any) -> bool:
    """JSON-semantic equality that does not alias True with 1 or 1 with 1.0."""

    return canonical_bytes(left) == canonical_bytes(right)


def _path_value(root: Mapping[str, Any], path: list[str]) -> Any:
    current: Any = root
    for index, key in enumerate(path):
        if type(current) is not dict or key not in current:
            dotted = ".".join(path[: index + 1])
            raise TrustError(f"contract path missing: {dotted}")
        current = current[key]
    return current


def _validate_path(path: Any, field: str) -> list[str]:
    if (
        type(path) is not list
        or not path
        or any(type(part) is not str or not part for part in path)
    ):
        raise TrustError(f"{field} must be a non-empty list of object keys")
    return list(path)


def validate_contract_shape(contract: Any) -> dict[str, Any]:
    obj = _require_object(contract, "contract")
    expected_keys = {
        "schema",
        "contract_id",
        "required_top_level_keys",
        "allowed_top_level_keys",
        "rules",
    }
    if set(obj) != expected_keys:
        raise TrustError("contract top-level shape is invalid")
    if obj.get("schema") != CONTRACT_SCHEMA:
        raise TrustError("unexpected contract schema")
    contract_id = obj.get("contract_id")
    if type(contract_id) is not str or not contract_id.strip():
        raise TrustError("contract_id must be a non-empty string")

    required = obj.get("required_top_level_keys")
    allowed = obj.get("allowed_top_level_keys")
    if type(required) is not list or any(type(k) is not str or not k for k in required):
        raise TrustError("required_top_level_keys must be a string list")
    if type(allowed) is not list or any(type(k) is not str or not k for k in allowed):
        raise TrustError("allowed_top_level_keys must be a string list")
    if len(required) != len(set(required)):
        raise TrustError("required_top_level_keys contains duplicates")
    if len(allowed) != len(set(allowed)):
        raise TrustError("allowed_top_level_keys contains duplicates")
    if not set(required) <= set(allowed):
        raise TrustError("required_top_level_keys must be a subset of allowed_top_level_keys")
    if "receipt_sha256" not in allowed:
        raise TrustError("allowed_top_level_keys must include receipt_sha256")

    rules = obj.get("rules")
    if type(rules) is not list or not rules:
        raise TrustError("rules must be a non-empty list")
    normalized_rules: list[dict[str, Any]] = []
    for index, rule in enumerate(rules):
        if type(rule) is not dict:
            raise TrustError(f"rules[{index}] must be an object")
        op = rule.get("op")
        path = _validate_path(rule.get("path"), f"rules[{index}].path")
        if op == "equals":
            if set(rule) != {"path", "op", "value"}:
                raise TrustError(f"rules[{index}] equals rule shape is invalid")
            normalized_rules.append({"path": path, "op": op, "value": rule["value"]})
        elif op == "in":
            if set(rule) != {"path", "op", "values"}:
                raise TrustError(f"rules[{index}] in rule shape is invalid")
            values = rule.get("values")
            if type(values) is not list or not values:
                raise TrustError(f"rules[{index}].values must be a non-empty list")
            encodings = [canonical_bytes(value) for value in values]
            if len(encodings) != len(set(encodings)):
                raise TrustError(f"rules[{index}].values contains duplicates")
            normalized_rules.append({"path": path, "op": op, "values": list(values)})
        else:
            raise TrustError(f"rules[{index}].op is unsupported")

    return {
        "schema": CONTRACT_SCHEMA,
        "contract_id": contract_id,
        "required_top_level_keys": list(required),
        "allowed_top_level_keys": list(allowed),
        "rules": normalized_rules,
    }


def verify_contract(
    receipt: Any,
    expected_receipt_sha256: str,
    contract: Any,
    expected_contract_sha256: str,
) -> dict[str, Any]:
    receipt_obj = _require_object(receipt, "receipt")
    committed = bind_external_commitment(receipt_obj, expected_receipt_sha256)

    if not _valid_sha256(expected_contract_sha256):
        raise TrustError("external contract commitment must be a lowercase SHA-256")
    normalized_contract = validate_contract_shape(contract)
    contract_sha256 = sha256_value(normalized_contract)
    if not hmac.compare_digest(contract_sha256, expected_contract_sha256):
        raise TrustError("external contract commitment mismatch")

    required = set(normalized_contract["required_top_level_keys"])
    allowed = set(normalized_contract["allowed_top_level_keys"])
    missing = sorted(required - set(receipt_obj))
    if missing:
        raise TrustError("receipt missing contract keys: " + ", ".join(missing))
    unknown = sorted(set(receipt_obj) - allowed)
    if unknown:
        raise TrustError("receipt contains contract-unknown keys: " + ", ".join(unknown))

    for index, rule in enumerate(normalized_contract["rules"]):
        actual = _path_value(receipt_obj, rule["path"])
        if rule["op"] == "equals":
            if not _typed_equal(actual, rule["value"]):
                raise TrustError(f"contract rule {index} failed")
        elif not any(_typed_equal(actual, candidate) for candidate in rule["values"]):
            raise TrustError(f"contract rule {index} failed")

    return {
        **committed,
        "schema": "receipt-trust-boundary/contract-verification-v1",
        "status": "EXTERNAL_COMMITMENT_AND_CONTRACT_BOUND",
        "semantic_contract_verified": True,
        "contract_id": normalized_contract["contract_id"],
        "contract_sha256": contract_sha256,
        "external_contract_commitment_sha256": expected_contract_sha256,
        "external_contract_commitment_verified": True,
        # Contract conformance still does not prove external facts or authorize
        # commercial/legal/monetary effects.
        "source_authenticity_verified": False,
        "buyer_acceptance_verified": False,
        "contract_execution_verified": False,
        "payment_verified": False,
        "recognized_revenue_verified": False,
    }
