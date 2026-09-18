"""Fail-closed partner-first qualification for HCPF RFP UHAA 2026000258.

Production source/evidence roots are intentionally empty. Research packets cannot mint
contact, provider, submission, payment, revenue, or public-Common-backlink authority.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Callable, Mapping

PURSUIT_ID = "CO-HCPF-HCBS-QUALITY-258"
PACKET_SCHEMA = "co-hcpf-hcbs-quality-qualification/v1"
RECEIPT_SCHEMA = "co-hcpf-hcbs-quality-qualification-receipt/v1"
MAX_JSON_BYTES = 1_000_000
MAX_JSON_DEPTH = 48
MAX_JSON_NODES = 50_000
MAX_SAFE_INTEGER = (1 << 53) - 1
MAX_INT_DIGITS = 16

PRIME_GATES = (
    "three_year_healthcare_survey_experience",
    "virtual_remote_survey_experience",
    "protected_data_collection",
    "diverse_community_projects",
    "disability_population_experience",
    "nci_or_analogous_statewide_survey_delivery",
)
WORKSHARE_GATES = (
    "sample_validation_automation",
    "survey_programming_testing",
    "secure_reporting_analytics",
    "accessibility_verification",
    "odesa_file_qa",
)
SOURCE_KEYS = frozenset({
    "id", "authority", "sha256", "effective_at", "solicitation_id",
    "inquiry_deadline", "proposal_deadline", "submission_route",
    "initial_cap_usd", "extension_cap_usd", "pricing_generation",
})
PRIME_KEYS = frozenset({"id", "org_id", "gate", "sha256"})
WORKSHARE_KEYS = frozenset({"id", "gate", "sha256"})
SHA_RE = re.compile(r"^[0-9a-f]{64}$")

_PRODUCTION_SOURCE_ROOTS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})
_PRODUCTION_PRIME_ROOTS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})
_PRODUCTION_WORKSHARE_ROOTS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})


class QualificationError(ValueError):
    pass


def _build_codec():
    loads = json.loads
    dumps = json.dumps
    decode_error = json.JSONDecodeError
    error = QualificationError
    max_bytes = MAX_JSON_BYTES
    max_depth = MAX_JSON_DEPTH
    max_nodes = MAX_JSON_NODES
    max_safe = MAX_SAFE_INTEGER
    max_digits = MAX_INT_DIGITS
    builtin_len = len
    builtin_type = type
    builtin_abs = abs
    builtin_int = int
    builtin_id = id
    builtin_set = set
    bytes_type = bytes
    str_type = str
    bool_type = bool
    int_type = int
    float_type = float
    list_type = list
    dict_type = dict
    unicode_encode_error = UnicodeEncodeError
    unicode_decode_error = UnicodeDecodeError
    runtime_error = RuntimeError
    value_error = ValueError
    overflow_error = OverflowError
    recursion_error = RecursionError
    unicode_error = UnicodeError

    def pairs(pairs_in):
        out = {}
        for key, value in pairs_in:
            if key in out:
                raise error(f"duplicate JSON key: {key}")
            out[key] = value
        return out

    def parse_int(text: str) -> int:
        digits = text[1:] if text.startswith("-") else text
        if not digits or not digits.isdigit() or builtin_len(digits) > max_digits:
            raise error("unsafe JSON integer")
        number = builtin_int(text)
        if builtin_abs(number) > max_safe:
            raise error("unsafe JSON integer")
        return number

    def reject_number(text: str):
        raise error(f"floating/non-finite JSON number forbidden: {text}")

    def snapshot(root: Any) -> Any:
        seen: set[int] = builtin_set()
        nodes = 0
        string_bytes = 0

        def detach(value: Any, depth: int) -> Any:
            nonlocal nodes, string_bytes
            nodes += 1
            if nodes > max_nodes:
                raise error("JSON value exceeds node limit")
            if depth > max_depth:
                raise error("JSON value exceeds depth limit")
            t = builtin_type(value)
            if value is None or t is bool_type:
                return value
            if t is int_type:
                if builtin_abs(value) > max_safe:
                    raise error("unsafe JSON integer")
                return value
            if t is float_type:
                raise error("floating-point value forbidden")
            if t is str_type:
                if builtin_len(value) > max_bytes - string_bytes:
                    raise error("JSON value exceeds aggregate string-byte limit")
                try:
                    encoded = value.encode("utf-8", "strict")
                except UnicodeEncodeError as exc:
                    raise error("invalid Unicode string") from exc
                string_bytes += builtin_len(encoded)
                if string_bytes > max_bytes:
                    raise error("JSON value exceeds aggregate string-byte limit")
                return value
            if t is list_type:
                marker = builtin_id(value)
                if marker in seen:
                    raise error("shared/cyclic JSON container")
                seen.add(marker)
                out = []
                try:
                    for item in value:
                        out.append(detach(item, depth + 1))
                except runtime_error as exc:
                    raise error("JSON container mutated during snapshot") from exc
                return out
            if t is dict_type:
                marker = builtin_id(value)
                if marker in seen:
                    raise error("shared/cyclic JSON container")
                seen.add(marker)
                out = {}
                try:
                    for key, item in value.items():
                        if builtin_type(key) is not str_type:
                            raise error("JSON object key must be string")
                        if builtin_len(key) > max_bytes - string_bytes:
                            raise error("JSON value exceeds aggregate string-byte limit")
                        try:
                            encoded = key.encode("utf-8", "strict")
                        except UnicodeEncodeError as exc:
                            raise error("invalid Unicode object key") from exc
                        string_bytes += builtin_len(encoded)
                        if string_bytes > max_bytes:
                            raise error("JSON value exceeds aggregate string-byte limit")
                        out[key] = detach(item, depth + 1)
                except runtime_error as exc:
                    raise error("JSON container mutated during snapshot") from exc
                return out
            raise error(f"unsupported JSON type: {t.__name__}")

        detached = detach(root, 0)
        raw = dumps(
            detached, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8", "strict")
        if builtin_len(raw) > max_bytes:
            raise error("canonical JSON exceeds byte limit")
        return detached

    def strict_load(raw: bytes | str) -> Any:
        if builtin_type(raw) is bytes_type:
            if builtin_len(raw) > max_bytes:
                raise error("JSON input exceeds byte limit")
            try:
                text = raw.decode("utf-8", "strict")
            except UnicodeDecodeError as exc:
                raise error("invalid UTF-8") from exc
        elif builtin_type(raw) is str_type:
            try:
                encoded = raw.encode("utf-8", "strict")
            except UnicodeEncodeError as exc:
                raise error("invalid UTF-8") from exc
            if builtin_len(encoded) > max_bytes:
                raise error("JSON input exceeds byte limit")
            text = raw
        else:
            raise error("JSON input must be bytes or str")
        try:
            value = loads(
                text, object_pairs_hook=pairs, parse_int=parse_int,
                parse_float=reject_number, parse_constant=reject_number,
            )
        except error:
            raise
        except (decode_error, ValueError, OverflowError, RecursionError, UnicodeError) as exc:
            raise error("invalid JSON") from exc
        return snapshot(value)

    def canonical(value: Any) -> bytes:
        detached = snapshot(value)
        raw = dumps(
            detached, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8", "strict")
        if builtin_len(raw) > max_bytes:
            raise error("canonical JSON exceeds byte limit")
        return raw

    return snapshot, strict_load, canonical


_snapshot_direct, loads_strict, canonical_bytes = _build_codec()


def _build_process_clock():
    dt = datetime
    utc = timezone.utc

    def now():
        return dt.now(utc)

    return now


_utc_now = _build_process_clock()


def _build_engine(
    source_roots: Mapping[str, Mapping[str, Any]],
    prime_roots: Mapping[str, Mapping[str, Any]],
    workshare_roots: Mapping[str, Mapping[str, Any]],
    clock: Callable[[], datetime],
):
    error = QualificationError
    snapshot = _snapshot_direct
    canonical = canonical_bytes
    digest = hashlib.sha256
    packet_schema = PACKET_SCHEMA
    receipt_schema = RECEIPT_SCHEMA
    pursuit_id = PURSUIT_ID
    source_keys = SOURCE_KEYS
    prime_keys = PRIME_KEYS
    workshare_keys = WORKSHARE_KEYS
    prime_gates = tuple(PRIME_GATES)
    workshare_gates = tuple(WORKSHARE_GATES)
    sha_fullmatch = SHA_RE.fullmatch
    max_safe = MAX_SAFE_INTEGER
    dt_type = datetime
    fromiso = datetime.fromisoformat
    utc = timezone.utc
    trusted_clock = clock
    mapping_proxy = MappingProxyType

    def text(value: Any, label: str) -> str:
        if type(value) is not str or not value or value != value.strip():
            raise error(f"{label} must be a non-empty trimmed string")
        return value

    def sha(value: Any, label: str) -> str:
        if type(value) is not str or sha_fullmatch(value) is None:
            raise error(f"{label} must be lowercase SHA-256 hex")
        return value

    def instant(value: Any, label: str) -> datetime:
        raw = text(value, label)
        try:
            parsed = fromiso(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise error(f"{label} must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise error(f"{label} must include timezone")
        return parsed.astimezone(utc)

    def positive_int(value: Any, label: str) -> int:
        if type(value) is not int or value <= 0 or value > max_safe:
            raise error(f"{label} must be a positive safe integer")
        return value

    def exact(row: Any, keys: frozenset[str], label: str) -> dict[str, Any]:
        if type(row) is not dict or set(row) != set(keys):
            raise error(f"{label} must contain exact keys: {sorted(keys)}")
        return row

    def validate_source(row: Any, label: str) -> dict[str, Any]:
        row = exact(row, source_keys, label)
        text(row["id"], f"{label}.id")
        if row["authority"] != "BUYER_SOURCE_SET":
            raise error(f"{label}.authority must be BUYER_SOURCE_SET")
        sha(row["sha256"], f"{label}.sha256")
        effective = instant(row["effective_at"], f"{label}.effective_at")
        inquiry = instant(row["inquiry_deadline"], f"{label}.inquiry_deadline")
        proposal = instant(row["proposal_deadline"], f"{label}.proposal_deadline")
        if inquiry > proposal or effective > proposal:
            raise error(f"{label} timeline inconsistent")
        text(row["solicitation_id"], f"{label}.solicitation_id")
        text(row["submission_route"], f"{label}.submission_route")
        positive_int(row["initial_cap_usd"], f"{label}.initial_cap_usd")
        positive_int(row["extension_cap_usd"], f"{label}.extension_cap_usd")
        text(row["pricing_generation"], f"{label}.pricing_generation")
        return row

    def validate_prime(row: Any, label: str) -> dict[str, Any]:
        row = exact(row, prime_keys, label)
        text(row["id"], f"{label}.id")
        text(row["org_id"], f"{label}.org_id")
        if row["gate"] not in prime_gates:
            raise error(f"{label}.gate invalid")
        sha(row["sha256"], f"{label}.sha256")
        return row

    def validate_workshare(row: Any, label: str) -> dict[str, Any]:
        row = exact(row, workshare_keys, label)
        text(row["id"], f"{label}.id")
        if row["gate"] not in workshare_gates:
            raise error(f"{label}.gate invalid")
        sha(row["sha256"], f"{label}.sha256")
        return row

    def freeze(roots, validator, label):
        if not isinstance(roots, Mapping):
            raise error(f"{label} roots must be mapping")
        frozen = {}
        for key, value in roots.items():
            key = text(key, f"{label}.id")
            row = dict(validator(snapshot(dict(value)), f"{label}[{key}]"))
            if row["id"] != key:
                raise error(f"{label} key/id mismatch")
            frozen[key] = row
        return mapping_proxy(frozen)

    trusted_sources = freeze(source_roots, validate_source, "source_roots")
    trusted_primes = freeze(prime_roots, validate_prime, "prime_roots")
    trusted_workshare = freeze(workshare_roots, validate_workshare, "workshare_roots")

    def compile_packet(untrusted_packet: Any) -> dict[str, Any]:
        packet = exact(
            snapshot(untrusted_packet),
            frozenset({"schema", "pursuit_id", "buyer_source_sets", "prime_evidence", "workshare_evidence"}),
            "packet",
        )
        if packet["schema"] != packet_schema:
            raise error("packet schema mismatch")
        if packet["pursuit_id"] != pursuit_id:
            raise error("pursuit_id mismatch")

        buyer_rows = packet["buyer_source_sets"]
        if type(buyer_rows) is not list:
            raise error("buyer_source_sets must be array")
        admitted_sources = []
        source_ids = set()
        for idx, row in enumerate(buyer_rows):
            row = exact(row, source_keys, f"buyer_source_sets[{idx}]")
            sid = text(row["id"], f"buyer_source_sets[{idx}].id")
            if sid in source_ids:
                raise error("duplicate buyer source id")
            source_ids.add(sid)
            validate_source(row, f"buyer_source_sets[{idx}]")
            trusted = trusted_sources.get(sid)
            if trusted is not None and row == trusted:
                admitted_sources.append((instant(row["effective_at"], f"{sid}.effective_at"), sid, row))

        current = None
        if admitted_sources:
            admitted_sources.sort(key=lambda item: (item[0], item[1]))
            newest = admitted_sources[-1][0]
            newest_rows = [item for item in admitted_sources if item[0] == newest]
            if len(newest_rows) != 1:
                raise error("ambiguous current official buyer generation")
            current = newest_rows[0]

        prime_rows = packet["prime_evidence"]
        if type(prime_rows) is not list:
            raise error("prime_evidence must be array")
        prime_by_org: dict[str, set[str]] = {}
        admitted_prime_ids = []
        seen_prime_ids = set()
        for idx, row in enumerate(prime_rows):
            row = exact(row, prime_keys, f"prime_evidence[{idx}]")
            eid = text(row["id"], f"prime_evidence[{idx}].id")
            if eid in seen_prime_ids:
                raise error("duplicate prime evidence id")
            seen_prime_ids.add(eid)
            validate_prime(row, f"prime_evidence[{idx}]")
            trusted = trusted_primes.get(eid)
            if trusted is not None and row == trusted:
                admitted_prime_ids.append(eid)
                prime_by_org.setdefault(row["org_id"], set()).add(row["gate"])

        work_rows = packet["workshare_evidence"]
        if type(work_rows) is not list:
            raise error("workshare_evidence must be array")
        work_gates = set()
        admitted_work_ids = []
        seen_work_ids = set()
        for idx, row in enumerate(work_rows):
            row = exact(row, workshare_keys, f"workshare_evidence[{idx}]")
            eid = text(row["id"], f"workshare_evidence[{idx}].id")
            if eid in seen_work_ids:
                raise error("duplicate workshare evidence id")
            seen_work_ids.add(eid)
            validate_workshare(row, f"workshare_evidence[{idx}]")
            trusted = trusted_workshare.get(eid)
            if trusted is not None and row == trusted:
                admitted_work_ids.append(eid)
                work_gates.add(row["gate"])

        now = trusted_clock()
        if not isinstance(now, dt_type) or now.tzinfo is None:
            raise error("trusted clock must return aware datetime")
        now = now.astimezone(utc)
        qualified = sorted(
            org for org, gates in prime_by_org.items()
            if set(prime_gates).issubset(gates)
        )
        missing_work = [gate for gate in workshare_gates if gate not in work_gates]

        state = "HOLD_MISSING_BUYER_SOURCE"
        posture = "RESEARCH_HOLD"
        reason = "no source-owned current official buyer source set is admitted"
        if current is not None:
            source = current[2]
            if now >= instant(source["proposal_deadline"], "current.proposal_deadline"):
                state = "HOLD_DEADLINE"
                reason = "trusted process time is at or after the admitted proposal deadline"
            elif not qualified:
                state = "HOLD_NO_QUALIFIED_PRIME"
                posture = "PARTNER_FIRST"
                reason = "no source-owned prime candidate satisfies every mandatory prime qualification gate"
            elif missing_work:
                state = "HOLD_WORKSHARE_EVIDENCE"
                posture = "PARTNER_FIRST"
                reason = "TJLabs specialist workshare evidence is incomplete"
            else:
                state = "PARTNER_PACKET_READY_FOR_OWNER_REVIEW"
                posture = "PARTNER_FIRST"
                reason = "buyer source, qualified prime, and specialist workshare evidence are complete for owner review"

        source_receipt = None
        if current is not None:
            row = current[2]
            source_receipt = {
                "id": row["id"],
                "sha256": row["sha256"],
                "effective_at": current[0].isoformat().replace("+00:00", "Z"),
                "solicitation_id": row["solicitation_id"],
                "inquiry_deadline": row["inquiry_deadline"],
                "proposal_deadline": row["proposal_deadline"],
                "submission_route": row["submission_route"],
                "initial_cap_usd": row["initial_cap_usd"],
                "extension_cap_usd": row["extension_cap_usd"],
                "pricing_generation": row["pricing_generation"],
            }

        result = {
            "schema": receipt_schema,
            "pursuit_id": pursuit_id,
            "evaluated_at": now.isoformat().replace("+00:00", "Z"),
            "state": state,
            "commercial_posture": posture,
            "reason": reason,
            "official_source_set": source_receipt,
            "qualified_prime_org_ids": qualified,
            "missing_workshare_gates": missing_work,
            "admitted_prime_evidence_ids": sorted(admitted_prime_ids),
            "admitted_workshare_evidence_ids": sorted(admitted_work_ids),
            "input_digest_sha256": digest(canonical(packet)).hexdigest(),
            "authority": {
                "buyer_contact": False,
                "partner_contact": False,
                "muse": False,
                "provider_mutation": False,
                "sign": False,
                "register": False,
                "box_upload": False,
                "submit": False,
                "payment": False,
                "revenue": False,
                "public_commons_backlink": False,
            },
        }
        core = dict(result)
        result["receipt_sha256"] = digest(canonical(core)).hexdigest()
        return result

    return compile_packet


_PRODUCTION_ENGINE = _build_engine(
    _PRODUCTION_SOURCE_ROOTS,
    _PRODUCTION_PRIME_ROOTS,
    _PRODUCTION_WORKSHARE_ROOTS,
    _utc_now,
)


def _build_public_api(engine, loader):
    production_engine = engine
    strict_loader = loader

    def compile_packet(packet: Any) -> dict[str, Any]:
        return production_engine(packet)

    def compile_json(raw: bytes | str) -> dict[str, Any]:
        return production_engine(strict_loader(raw))

    return compile_packet, compile_json


compile_packet, compile_json = _build_public_api(_PRODUCTION_ENGINE, loads_strict)
