from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

SOURCE_MAX_BYTES = 32 * 1024 * 1024
POLICY_MAX_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 80
MAX_JSON_NODES = 600_000
MAX_STRING_LENGTH = 1_000_000
MAX_SELECTIONS = 256
MAX_COMPARISONS = 256
MAX_CHECKS = 256
MAX_TERMS = 64
MAX_FACTS_PER_SELECTION = 20_000
MAX_DECIMAL_ABS = Decimal("1e60")

POLICY_SCHEMA = "TJL_FILING_QUALITY_POLICY_V1"
REPORT_SCHEMA = "TJL_FILING_QUALITY_REPORT_V1"
RECEIPT_SCHEMA = "TJL_FILING_QUALITY_RECEIPT_V1"
TRUST_BOUNDARY = "RETAINED_SOURCE_BYTES_NOT_SEC_AUTHENTICATED"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_TAXONOMY_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_CONCEPT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]{0,199}$")
_UNIT_RE = re.compile(r"^[A-Za-z0-9._/:*-]{1,80}$")
_CIK_RE = re.compile(r"^[0-9]{1,10}$")

_AUTHORITY = {
    "brokerage_action": False,
    "trading_action": False,
    "regulatory_filing": False,
    "general_ledger_mutation": False,
    "payment_action": False,
    "customer_account_mutation": False,
    "materiality_judgment": False,
    "accounting_conclusion": False,
    "source_authentication": False,
}


class FilingQualityError(ValueError):
    pass


def _pairs_no_dupes(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise FilingQualityError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def _parse_int(text: str) -> int:
    if len(text.lstrip("-")) > 80:
        raise FilingQualityError("integer token too large")
    value = int(text)
    if abs(value) > 10**60:
        raise FilingQualityError("integer magnitude too large")
    return value


def _parse_float(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise FilingQualityError("invalid decimal token") from exc
    _bounded_decimal(value, "JSON decimal")
    return value


def _reject_constant(text: str) -> Any:
    raise FilingQualityError(f"non-finite JSON number forbidden: {text}")


def _walk_limits(value: Any) -> None:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise FilingQualityError("JSON node limit exceeded")
        if depth > MAX_JSON_DEPTH:
            raise FilingQualityError("JSON depth limit exceeded")
        if type(item) is str:
            if len(item) > MAX_STRING_LENGTH:
                raise FilingQualityError("JSON string too long")
            continue
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise FilingQualityError("JSON object key must be string")
                if len(key) > 500:
                    raise FilingQualityError("JSON object key too long")
                stack.append((child, depth + 1))
        elif type(item) is list:
            for child in item:
                stack.append((child, depth + 1))
        elif type(item) is bool or item is None or type(item) in {int, Decimal}:
            continue
        else:
            raise FilingQualityError(f"unsupported JSON value type: {type(item).__name__}")


def loads_strict(data: str | bytes, *, max_bytes: int) -> Any:
    if type(data) is bytes:
        raw = data
        try:
            text = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise FilingQualityError("input must be strict UTF-8") from exc
    elif type(data) is str:
        try:
            raw = data.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise FilingQualityError("input contains invalid Unicode") from exc
        text = data
    else:
        raise FilingQualityError("input must be str or bytes")
    if len(raw) > max_bytes:
        raise FilingQualityError(f"input exceeds {max_bytes} byte limit")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_no_dupes,
            parse_int=_parse_int,
            parse_float=_parse_float,
            parse_constant=_reject_constant,
        )
    except FilingQualityError:
        raise
    except (json.JSONDecodeError, RecursionError) as exc:
        raise FilingQualityError(f"invalid JSON: {exc}") from exc
    _walk_limits(value)
    return value


def load_source(data: str | bytes) -> dict[str, Any]:
    value = loads_strict(data, max_bytes=SOURCE_MAX_BYTES)
    if type(value) is not dict:
        raise FilingQualityError("source root must be an object")
    return value


def load_policy(data: str | bytes) -> dict[str, Any]:
    value = loads_strict(data, max_bytes=POLICY_MAX_BYTES)
    if type(value) is not dict:
        raise FilingQualityError("policy root must be an object")
    return value


def _jsonable(value: Any) -> Any:
    if type(value) is Decimal:
        return _decimal_text(value)
    if type(value) is dict:
        return {key: _jsonable(child) for key, child in value.items()}
    if type(value) is list:
        return [_jsonable(child) for child in value]
    if type(value) in {str, int, bool} or value is None:
        return value
    raise FilingQualityError(f"cannot canonicalize {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            _jsonable(value),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise FilingQualityError(f"cannot canonicalize: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_bytes(data: str | bytes) -> bytes:
    if type(data) is bytes:
        try:
            data.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise FilingQualityError("source must be strict UTF-8") from exc
        return data
    if type(data) is str:
        try:
            return data.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise FilingQualityError("source contains invalid Unicode") from exc
    raise FilingQualityError("source must be str or bytes")


def _exact_object(value: Any, keys: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise FilingQualityError(f"{where}: object required")
    have = set(value)
    if have != keys:
        raise FilingQualityError(
            f"{where}: exact fields required; missing={sorted(keys-have)} extra={sorted(have-keys)}"
        )
    return value


def _text(value: Any, where: str, maximum: int = 512) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise FilingQualityError(f"{where}: bounded nonempty string required")
    if any(ord(ch) < 32 for ch in value):
        raise FilingQualityError(f"{where}: control characters forbidden")
    return value


def _match(value: Any, regex: re.Pattern[str], where: str, maximum: int = 512) -> str:
    text = _text(value, where, maximum)
    if not regex.fullmatch(text):
        raise FilingQualityError(f"{where}: invalid value {text!r}")
    return text


def _iso_date(value: Any, where: str) -> str:
    text = _text(value, where, 10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise FilingQualityError(f"{where}: YYYY-MM-DD date required") from exc
    if parsed.isoformat() != text:
        raise FilingQualityError(f"{where}: canonical YYYY-MM-DD date required")
    return text


def _normalize_cik(value: Any, where: str) -> str:
    if type(value) is bool:
        raise FilingQualityError(f"{where}: CIK cannot be boolean")
    if type(value) is int:
        if value < 0:
            raise FilingQualityError(f"{where}: CIK cannot be negative")
        text = str(value)
    elif type(value) is str:
        text = value
    else:
        raise FilingQualityError(f"{where}: string or integer CIK required")
    if not _CIK_RE.fullmatch(text):
        raise FilingQualityError(f"{where}: invalid CIK")
    return text.zfill(10)


def _bounded_decimal(value: Decimal, where: str) -> Decimal:
    if not value.is_finite():
        raise FilingQualityError(f"{where}: finite decimal required")
    if abs(value) > MAX_DECIMAL_ABS:
        raise FilingQualityError(f"{where}: decimal magnitude exceeds limit")
    tup = value.as_tuple()
    if len(tup.digits) > 80 or abs(tup.exponent) > 80:
        raise FilingQualityError(f"{where}: decimal precision/exponent exceeds limit")
    return value


def _decimal(value: Any, where: str) -> Decimal:
    if type(value) is bool:
        raise FilingQualityError(f"{where}: boolean is not numeric")
    if type(value) is int:
        return _bounded_decimal(Decimal(value), where)
    if type(value) is Decimal:
        return _bounded_decimal(value, where)
    if type(value) is str:
        try:
            dec = Decimal(value)
        except InvalidOperation as exc:
            raise FilingQualityError(f"{where}: decimal string required") from exc
        return _bounded_decimal(dec, where)
    raise FilingQualityError(f"{where}: exact decimal value required")


def _decimal_text(value: Decimal) -> str:
    value = _bounded_decimal(value, "decimal output")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "-0":
        return "0"
    return text


def _period(raw: Any, where: str) -> dict[str, str]:
    if type(raw) is not dict:
        raise FilingQualityError(f"{where}: period object required")
    kind = raw.get("kind")
    if kind == "instant":
        obj = _exact_object(raw, {"kind", "end"}, where)
        return {"kind": "instant", "end": _iso_date(obj["end"], f"{where}.end")}
    if kind == "duration":
        obj = _exact_object(raw, {"kind", "start", "end"}, where)
        start = _iso_date(obj["start"], f"{where}.start")
        end = _iso_date(obj["end"], f"{where}.end")
        if start > end:
            raise FilingQualityError(f"{where}: start after end")
        return {"kind": "duration", "start": start, "end": end}
    raise FilingQualityError(f"{where}: kind must be instant or duration")


def _period_key(period: dict[str, str]) -> tuple[str, str | None, str]:
    return (period["kind"], period.get("start"), period["end"])


def _selection_policy(raw: Any, index: int) -> dict[str, Any]:
    where = f"policy.selections[{index}]"
    row = _exact_object(raw, {"id", "taxonomy", "concept", "unit", "period"}, where)
    return {
        "id": _match(row["id"], _ID_RE, f"{where}.id", 120),
        "taxonomy": _match(row["taxonomy"], _TAXONOMY_RE, f"{where}.taxonomy", 80),
        "concept": _match(row["concept"], _CONCEPT_RE, f"{where}.concept", 200),
        "unit": _match(row["unit"], _UNIT_RE, f"{where}.unit", 80),
        "period": _period(row["period"], f"{where}.period"),
    }


def _comparison_policy(raw: Any, index: int) -> dict[str, str]:
    where = f"policy.comparisons[{index}]"
    row = _exact_object(raw, {"id", "left", "right"}, where)
    return {
        "id": _match(row["id"], _ID_RE, f"{where}.id", 120),
        "left": _match(row["left"], _ID_RE, f"{where}.left", 120),
        "right": _match(row["right"], _ID_RE, f"{where}.right", 120),
    }


def _term_policy(raw: Any, where: str) -> dict[str, str]:
    row = _exact_object(raw, {"selection", "coefficient"}, where)
    coefficient = _decimal(row["coefficient"], f"{where}.coefficient")
    return {
        "selection": _match(row["selection"], _ID_RE, f"{where}.selection", 120),
        "coefficient": _decimal_text(coefficient),
    }


def _check_policy(raw: Any, index: int) -> dict[str, Any]:
    where = f"policy.checks[{index}]"
    row = _exact_object(raw, {"id", "terms", "target", "tolerance"}, where)
    terms = row["terms"]
    if type(terms) is not list or not terms or len(terms) > MAX_TERMS:
        raise FilingQualityError(f"{where}.terms: 1..{MAX_TERMS} items required")
    tolerance = _decimal(row["tolerance"], f"{where}.tolerance")
    if tolerance < 0:
        raise FilingQualityError(f"{where}.tolerance: nonnegative required")
    return {
        "id": _match(row["id"], _ID_RE, f"{where}.id", 120),
        "terms": [_term_policy(item, f"{where}.terms[{i}]") for i, item in enumerate(terms)],
        "target": _match(row["target"], _ID_RE, f"{where}.target", 120),
        "tolerance": _decimal_text(tolerance),
    }


def normalize_policy(policy: dict[str, Any]) -> dict[str, Any]:
    row = _exact_object(
        policy,
        {"schema", "cik", "filing_cutoff", "selections", "comparisons", "checks"},
        "policy",
    )
    if row["schema"] != POLICY_SCHEMA:
        raise FilingQualityError(f"policy.schema must be {POLICY_SCHEMA}")
    selections_raw = row["selections"]
    comparisons_raw = row["comparisons"]
    checks_raw = row["checks"]
    if type(selections_raw) is not list or not selections_raw or len(selections_raw) > MAX_SELECTIONS:
        raise FilingQualityError(f"policy.selections: 1..{MAX_SELECTIONS} items required")
    if type(comparisons_raw) is not list or len(comparisons_raw) > MAX_COMPARISONS:
        raise FilingQualityError(f"policy.comparisons: 0..{MAX_COMPARISONS} items required")
    if type(checks_raw) is not list or len(checks_raw) > MAX_CHECKS:
        raise FilingQualityError(f"policy.checks: 0..{MAX_CHECKS} items required")
    selections = [_selection_policy(item, i) for i, item in enumerate(selections_raw)]
    comparisons = [_comparison_policy(item, i) for i, item in enumerate(comparisons_raw)]
    checks = [_check_policy(item, i) for i, item in enumerate(checks_raw)]
    ids = [row["id"] for row in selections]
    if len(ids) != len(set(ids)):
        raise FilingQualityError("policy.selections: duplicate id")
    all_control_ids = [row["id"] for row in comparisons] + [row["id"] for row in checks]
    if len(all_control_ids) != len(set(all_control_ids)):
        raise FilingQualityError("policy comparisons/checks: duplicate control id")
    known = set(ids)
    for cmp in comparisons:
        if cmp["left"] not in known or cmp["right"] not in known:
            raise FilingQualityError(f"comparison {cmp['id']}: unknown selection")
        if cmp["left"] == cmp["right"]:
            raise FilingQualityError(f"comparison {cmp['id']}: left and right must differ")
    for check in checks:
        refs = [term["selection"] for term in check["terms"]] + [check["target"]]
        if any(ref not in known for ref in refs):
            raise FilingQualityError(f"check {check['id']}: unknown selection")
    return {
        "schema": POLICY_SCHEMA,
        "cik": _normalize_cik(row["cik"], "policy.cik"),
        "filing_cutoff": _iso_date(row["filing_cutoff"], "policy.filing_cutoff"),
        "selections": sorted(selections, key=lambda item: item["id"]),
        "comparisons": sorted(comparisons, key=lambda item: item["id"]),
        "checks": sorted(checks, key=lambda item: item["id"]),
    }


def _source_identity(source: dict[str, Any], expected_cik: str) -> dict[str, str]:
    if "cik" not in source or "entityName" not in source or "facts" not in source:
        raise FilingQualityError("source must contain cik, entityName, and facts")
    cik = _normalize_cik(source["cik"], "source.cik")
    if cik != expected_cik:
        raise FilingQualityError(f"source.cik {cik} does not match policy.cik {expected_cik}")
    entity_name = _text(source["entityName"], "source.entityName", 500)
    if type(source["facts"]) is not dict:
        raise FilingQualityError("source.facts must be an object")
    return {"cik": cik, "entity_name": entity_name}


def _candidate_value(raw: Any, where: str) -> Decimal:
    return _decimal(raw, where)


def _observation_from_fact(
    raw: Any,
    *,
    selection: dict[str, Any],
    index: int,
    cutoff: str,
) -> dict[str, Any] | None:
    where = f"{selection['id']}.fact[{index}]"
    if type(raw) is not dict:
        raise FilingQualityError(f"{where}: fact must be object")
    required = {"end", "val", "accn", "form", "filed"}
    if selection["period"]["kind"] == "duration":
        required.add("start")
    missing = required - set(raw)
    if missing:
        raise FilingQualityError(f"{where}: missing required fields {sorted(missing)}")
    end = _iso_date(raw["end"], f"{where}.end")
    start = None
    if selection["period"]["kind"] == "duration":
        start = _iso_date(raw["start"], f"{where}.start")
    elif "start" in raw:
        return None
    period = selection["period"]
    if end != period["end"]:
        return None
    if period["kind"] == "duration" and start != period["start"]:
        return None
    filed = _iso_date(raw["filed"], f"{where}.filed")
    if filed > cutoff:
        return None
    value = _candidate_value(raw["val"], f"{where}.val")
    accn = _text(raw["accn"], f"{where}.accn", 80)
    form = _text(raw["form"], f"{where}.form", 40)
    out = {
        "value": _decimal_text(value),
        "filed": filed,
        "accession": accn,
        "form": form,
    }
    for key in ("fy", "fp", "frame"):
        if key in raw and raw[key] is not None:
            val = raw[key]
            if type(val) is bool:
                raise FilingQualityError(f"{where}.{key}: boolean forbidden")
            if type(val) in {int, Decimal}:
                val = str(val)
            out[key] = _text(val, f"{where}.{key}", 80)
    return out


def _find_unit_facts(source: dict[str, Any], selection: dict[str, Any]) -> list[Any]:
    facts = source["facts"]
    taxonomy = facts.get(selection["taxonomy"])
    if taxonomy is None:
        return []
    if type(taxonomy) is not dict:
        raise FilingQualityError(f"source.facts.{selection['taxonomy']}: object required")
    concept = taxonomy.get(selection["concept"])
    if concept is None:
        return []
    if type(concept) is not dict:
        raise FilingQualityError(f"concept {selection['concept']}: object required")
    units = concept.get("units")
    if units is None:
        return []
    if type(units) is not dict:
        raise FilingQualityError(f"concept {selection['concept']}.units: object required")
    facts_for_unit = units.get(selection["unit"])
    if facts_for_unit is None:
        return []
    if type(facts_for_unit) is not list:
        raise FilingQualityError(f"unit {selection['unit']}: fact list required")
    if len(facts_for_unit) > MAX_FACTS_PER_SELECTION:
        raise FilingQualityError(f"selection {selection['id']}: fact count exceeds limit")
    return facts_for_unit


def _select(source: dict[str, Any], spec: dict[str, Any], cutoff: str) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    for index, raw in enumerate(_find_unit_facts(source, spec)):
        obs = _observation_from_fact(raw, selection=spec, index=index, cutoff=cutoff)
        if obs is not None:
            observations.append(obs)
    observations.sort(key=lambda row: (row["filed"], row["accession"], row["value"], row["form"]))
    base = {
        "id": spec["id"],
        "taxonomy": spec["taxonomy"],
        "concept": spec["concept"],
        "unit": spec["unit"],
        "period": spec["period"],
        "observations": observations,
        "selected_value": None,
        "selected_filed": None,
        "selected_accessions": [],
        "findings": [],
    }
    if not observations:
        base["status"] = "NO_MATCHING_FACT"
        base["findings"].append("NO_MATCHING_FACT_AT_OR_BEFORE_CUTOFF")
        return base
    latest_filed = max(obs["filed"] for obs in observations)
    latest = [obs for obs in observations if obs["filed"] == latest_filed]
    latest_values = {obs["value"] for obs in latest}
    if len(latest_values) > 1:
        base["status"] = "AMBIGUOUS_LATEST_FILING_DATE"
        base["selected_filed"] = latest_filed
        base["selected_accessions"] = sorted({obs["accession"] for obs in latest})
        base["findings"].append("SAME_FILED_DATE_DIFFERING_VALUES")
        return base
    value = next(iter(latest_values))
    base["status"] = "SELECTED"
    base["selected_value"] = value
    base["selected_filed"] = latest_filed
    base["selected_accessions"] = sorted({obs["accession"] for obs in latest})
    if len(base["selected_accessions"]) > 1:
        base["findings"].append("SAME_VALUE_MULTIPLE_ACCESSIONS_ON_LATEST_DATE")
    historical_values = {obs["value"] for obs in observations}
    if len(historical_values) > 1:
        base["findings"].append("REPORTED_VALUE_CHANGED_ACROSS_FILINGS")
    return base


def _selection_value(row: dict[str, Any]) -> Decimal | None:
    if row["status"] != "SELECTED" or row["selected_value"] is None:
        return None
    return _decimal(row["selected_value"], f"selection {row['id']} selected_value")


def _comparison(spec: dict[str, str], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    left = by_id[spec["left"]]
    right = by_id[spec["right"]]
    out = {
        "id": spec["id"],
        "left": spec["left"],
        "right": spec["right"],
        "status": "",
        "left_value": left["selected_value"],
        "right_value": right["selected_value"],
        "delta": None,
        "unit": None,
        "note": None,
    }
    if left["unit"] != right["unit"]:
        out["status"] = "HOLD_INCOMPATIBLE_UNIT"
        out["note"] = "comparison requires identical units"
        return out
    lv = _selection_value(left)
    rv = _selection_value(right)
    if lv is None or rv is None:
        out["status"] = "HOLD_UNSELECTED_INPUT"
        out["note"] = "one or both selections are not uniquely selected"
        out["unit"] = left["unit"]
        return out
    out["status"] = "OK"
    out["unit"] = left["unit"]
    out["delta"] = _decimal_text(rv - lv)
    if rv != lv:
        out["note"] = "reported value differs; this is not labeled a restatement"
    else:
        out["note"] = "reported values equal"
    return out


def _check(spec: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    refs = [term["selection"] for term in spec["terms"]] + [spec["target"]]
    rows = [by_id[ref] for ref in refs]
    out = {
        "id": spec["id"],
        "target": spec["target"],
        "terms": spec["terms"],
        "tolerance": spec["tolerance"],
        "status": "",
        "unit": None,
        "period": None,
        "computed": None,
        "target_value": by_id[spec["target"]]["selected_value"],
        "difference": None,
        "note": None,
    }
    units = {row["unit"] for row in rows}
    if len(units) != 1:
        out["status"] = "HOLD_INCOMPATIBLE_UNIT"
        out["note"] = "arithmetic check requires identical units"
        return out
    period_keys = {_period_key(row["period"]) for row in rows}
    if len(period_keys) != 1:
        out["status"] = "HOLD_INCOMPATIBLE_PERIOD"
        out["unit"] = next(iter(units))
        out["note"] = "arithmetic check requires identical fact periods"
        return out
    values = {row["id"]: _selection_value(row) for row in rows}
    if any(value is None for value in values.values()):
        out["status"] = "HOLD_UNSELECTED_INPUT"
        out["unit"] = next(iter(units))
        out["period"] = rows[0]["period"]
        out["note"] = "one or more arithmetic inputs are not uniquely selected"
        return out
    computed = Decimal(0)
    for term in spec["terms"]:
        coefficient = _decimal(term["coefficient"], f"check {spec['id']} coefficient")
        value = values[term["selection"]]
        if value is None:
            raise FilingQualityError("internal missing check value")
        computed += coefficient * value
    target = values[spec["target"]]
    if target is None:
        raise FilingQualityError("internal missing target value")
    difference = computed - target
    tolerance = _decimal(spec["tolerance"], f"check {spec['id']} tolerance")
    out["unit"] = next(iter(units))
    out["period"] = rows[0]["period"]
    out["computed"] = _decimal_text(computed)
    out["target_value"] = _decimal_text(target)
    out["difference"] = _decimal_text(difference)
    out["status"] = "PASS" if abs(difference) <= tolerance else "FAIL"
    out["note"] = "exact Decimal arithmetic; tolerance is inclusive"
    return out


def _exceptions(selections: list[dict[str, Any]], checks: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for selection in selections:
        if selection["status"] != "SELECTED":
            rows.append({
                "kind": "SELECTION",
                "id": selection["id"],
                "code": selection["status"],
                "detail": "; ".join(selection["findings"]) or selection["status"],
            })
        for finding in selection["findings"]:
            if finding == "REPORTED_VALUE_CHANGED_ACROSS_FILINGS":
                rows.append({
                    "kind": "SELECTION",
                    "id": selection["id"],
                    "code": finding,
                    "detail": "multiple retained filed-date observations carry differing reported values; analyst review required",
                })
    for check in checks:
        if check["status"] != "PASS":
            rows.append({
                "kind": "CHECK",
                "id": check["id"],
                "code": check["status"],
                "detail": check["note"] or check["status"],
            })
    rows.sort(key=lambda row: (row["kind"], row["id"], row["code"], row["detail"]))
    return rows


def compile_report(source_data: str | bytes, policy_data: str | bytes) -> dict[str, Any]:
    source_raw = _source_bytes(source_data)
    policy_raw = _source_bytes(policy_data)
    source = load_source(source_raw)
    policy = normalize_policy(load_policy(policy_raw))
    identity = _source_identity(source, policy["cik"])
    selections = [_select(source, spec, policy["filing_cutoff"]) for spec in policy["selections"]]
    by_id = {row["id"]: row for row in selections}
    comparisons = [_comparison(spec, by_id) for spec in policy["comparisons"]]
    checks = [_check(spec, by_id) for spec in policy["checks"]]
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "source": {
            "cik": identity["cik"],
            "entity_name": identity["entity_name"],
            "sha256": sha256_bytes(source_raw),
            "bytes": len(source_raw),
            "trust_boundary": TRUST_BOUNDARY,
        },
        "policy": {
            "sha256": sha256_bytes(policy_raw),
            "bytes": len(policy_raw),
            "normalized_sha256": sha256_bytes(canonical_bytes(policy)),
            "filing_cutoff": policy["filing_cutoff"],
        },
        "selection_rule": {
            "period_identity": "EXACT_START_END_OR_EXACT_INSTANT_END",
            "unit_identity": "EXACT_UNIT_KEY",
            "cutoff": "FILED_DATE_INCLUSIVE",
            "latest_rule": "LATEST_FILED_DATE_AT_OR_BEFORE_CUTOFF",
            "same_day_conflict": "DIFFERING_VALUES_REFUSE_SELECTION",
            "fy_fp_frame": "PRESERVED_AS_METADATA_NEVER_PERIOD_IDENTITY",
        },
        "selections": selections,
        "comparisons": comparisons,
        "checks": checks,
        "exceptions": _exceptions(selections, checks),
        "authority": dict(_AUTHORITY),
        "limitations": [
            "retained bytes are not authenticated as SEC-origin by this compiler",
            "a filing-date cutoff over a later snapshot is not a historical-vintage or intraday-availability backtest",
            "reported value changes are not automatically restatements",
            "custom/dimensional/missing-fact interpretation and materiality remain analyst responsibilities",
            "digests prove byte identity only, not issuer, filing, SEC, or accounting authenticity",
        ],
    }
    report["receipt_sha256"] = sha256_bytes(canonical_bytes(report))
    return report


def verify_report(report: dict[str, Any], source_data: str | bytes, policy_data: str | bytes) -> bool:
    if type(report) is not dict:
        return False
    receipt = report.get("receipt_sha256")
    if type(receipt) is not str or len(receipt) != 64:
        return False
    body = dict(report)
    body.pop("receipt_sha256", None)
    if sha256_bytes(canonical_bytes(body)) != receipt:
        return False
    try:
        expected = compile_report(source_data, policy_data)
    except FilingQualityError:
        return False
    return canonical_bytes(expected) == canonical_bytes(report)


def render_observations_csv(report: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow([
        "selection_id", "taxonomy", "concept", "unit", "period_kind", "start", "end",
        "status", "selected", "value", "filed", "accession", "form", "fy", "fp", "frame",
    ])
    for selection in report["selections"]:
        selected_accessions = set(selection["selected_accessions"])
        for obs in selection["observations"]:
            selected = (
                selection["status"] == "SELECTED"
                and obs["filed"] == selection["selected_filed"]
                and obs["accession"] in selected_accessions
                and obs["value"] == selection["selected_value"]
            )
            writer.writerow([
                selection["id"], selection["taxonomy"], selection["concept"], selection["unit"],
                selection["period"]["kind"], selection["period"].get("start", ""), selection["period"]["end"],
                selection["status"], "true" if selected else "false", obs["value"], obs["filed"],
                obs["accession"], obs["form"], obs.get("fy", ""), obs.get("fp", ""), obs.get("frame", ""),
            ])
    return output.getvalue()


def render_exceptions_csv(report: dict[str, Any]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["kind", "id", "code", "detail"])
    for row in report["exceptions"]:
        writer.writerow([row["kind"], row["id"], row["code"], row["detail"]])
    return output.getvalue()


def render_html(report: dict[str, Any]) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    selection_rows = []
    for row in report["selections"]:
        selection_rows.append(
            "<tr>"
            f"<td>{esc(row['id'])}</td><td>{esc(row['taxonomy'])}:{esc(row['concept'])}</td>"
            f"<td>{esc(row['unit'])}</td><td><code>{esc(canonical_bytes(row['period']).decode('utf-8'))}</code></td><td>{esc(row['status'])}</td>"
            f"<td>{esc(row['selected_value'] if row['selected_value'] is not None else '')}</td>"
            f"<td>{esc(row['selected_filed'] if row['selected_filed'] is not None else '')}</td>"
            f"<td>{esc(', '.join(row['findings']))}</td>"
            "</tr>"
        )
    check_rows = []
    for row in report["checks"]:
        check_rows.append(
            "<tr>"
            f"<td>{esc(row['id'])}</td><td>{esc(row['status'])}</td><td>{esc(row['computed'] or '')}</td>"
            f"<td>{esc(row['target_value'] or '')}</td><td>{esc(row['difference'] or '')}</td>"
            f"<td>{esc(row['tolerance'])}</td><td>{esc(row['note'] or '')}</td>"
            "</tr>"
        )
    exceptions = "".join(
        f"<li><code>{esc(row['id'])}</code> — {esc(row['code'])}: {esc(row['detail'])}</li>"
        for row in report["exceptions"]
    ) or "<li>None</li>"
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Filing Quality Desk</title>
<style>body{font-family:system-ui,sans-serif;max-width:1200px;margin:2rem auto;padding:0 1rem}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{border:1px solid #bbb;padding:.4rem;vertical-align:top}th{background:#eee}code{font-family:ui-monospace,monospace}.warn{border-left:4px solid #777;padding:.5rem 1rem;background:#f5f5f5}</style></head><body>""" + (
        f"<h1>Filing Quality Desk — {esc(report['source']['entity_name'])}</h1>"
        f"<p><strong>CIK:</strong> {esc(report['source']['cik'])} &nbsp; <strong>Filed cutoff:</strong> {esc(report['policy']['filing_cutoff'])}</p>"
        f"<p><strong>Source SHA-256:</strong> <code>{esc(report['source']['sha256'])}</code></p>"
        f"<p><strong>Report receipt:</strong> <code>{esc(report['receipt_sha256'])}</code></p>"
        "<div class=\"warn\"><strong>Boundary:</strong> retained bytes are untrusted supplied data. "
        "This report does not authenticate SEC custody, make filing/accounting conclusions, or treat changed reported values as restatements.</div>"
        "<h2>Selections</h2><table><thead><tr><th>ID</th><th>Fact</th><th>Unit</th><th>Period</th><th>Status</th><th>Selected value</th><th>Filed</th><th>Findings</th></tr></thead><tbody>"
        + "".join(selection_rows) + "</tbody></table>"
        "<h2>Arithmetic checks</h2><table><thead><tr><th>ID</th><th>Status</th><th>Computed</th><th>Target</th><th>Difference</th><th>Tolerance</th><th>Note</th></tr></thead><tbody>"
        + "".join(check_rows) + "</tbody></table>"
        "<h2>Exceptions / review queue</h2><ul>" + exceptions + "</ul>"
        "<h2>Limitations</h2><ul>" + "".join(f"<li>{esc(x)}</li>" for x in report["limitations"]) + "</ul>"
        "</body></html>\n"
    )


def bundle_files(report: dict[str, Any]) -> dict[str, bytes]:
    report_bytes = canonical_bytes(report) + b"\n"
    observations = render_observations_csv(report).encode("utf-8")
    exceptions = render_exceptions_csv(report).encode("utf-8")
    analyst_html = render_html(report).encode("utf-8")
    manifest = {
        "schema": RECEIPT_SCHEMA,
        "report_receipt_sha256": report["receipt_sha256"],
        "files": {
            "report.json": {"sha256": sha256_bytes(report_bytes), "bytes": len(report_bytes)},
            "observations.csv": {"sha256": sha256_bytes(observations), "bytes": len(observations)},
            "exceptions.csv": {"sha256": sha256_bytes(exceptions), "bytes": len(exceptions)},
            "analyst.html": {"sha256": sha256_bytes(analyst_html), "bytes": len(analyst_html)},
        },
    }
    receipt = canonical_bytes(manifest) + b"\n"
    return {
        "report.json": report_bytes,
        "observations.csv": observations,
        "exceptions.csv": exceptions,
        "analyst.html": analyst_html,
        "receipt.json": receipt,
    }


def write_bundle(output_dir: str | Path, report: dict[str, Any]) -> dict[str, str]:
    target = Path(output_dir)
    if target.exists():
        if not target.is_dir():
            raise FilingQualityError("output path exists and is not a directory")
        if any(target.iterdir()):
            raise FilingQualityError("output directory must be empty; no overwrite allowed")
    else:
        target.mkdir(parents=True, exist_ok=False)
    written: dict[str, str] = {}
    for name, data in bundle_files(report).items():
        path = target / name
        try:
            with path.open("xb") as handle:
                handle.write(data)
        except FileExistsError as exc:
            raise FilingQualityError(f"refusing to overwrite {path}") from exc
        written[name] = sha256_bytes(data)
    return written


def verify_bundle(output_dir: str | Path, source_data: str | bytes, policy_data: str | bytes) -> bool:
    target = Path(output_dir)
    try:
        report_raw = (target / "report.json").read_bytes()
        report = loads_strict(report_raw, max_bytes=8 * 1024 * 1024)
        if type(report) is not dict or not verify_report(report, source_data, policy_data):
            return False
        expected = bundle_files(report)
        for name, data in expected.items():
            if (target / name).read_bytes() != data:
                return False
        return True
    except (OSError, FilingQualityError):
        return False
