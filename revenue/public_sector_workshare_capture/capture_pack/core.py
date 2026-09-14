"""Deterministic public-sector SI workshare capture packet compiler.

This package has no send, bid, portal, payment, or contracting authority.  It compiles
bounded prime-facing workshare hypotheses from public opportunity evidence and refuses
missing/stale source or collision-control inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import unicodedata
from typing import Any, Iterable, Mapping

SCHEMA = "tjl.public-sector-workshare/v1"
STATUS = "PROPOSED_NOT_ACCEPTED"
SEND_AUTHORIZED = False
AUTHORITY_CEILING = [
    "NO_BUYER_OR_PRIME_CONTACT",
    "NO_BID_OR_PORTAL_MUTATION",
    "NO_TEAMING_OR_LEGAL_COMMITMENT",
    "NO_CERTIFICATION_OR_PAST_PERFORMANCE_INVENTION",
    "NO_SPEND_PAYMENT_OR_REVENUE_AUTHORITY",
]
OUTBOUND_PRECONDITIONS = [
    "fresh relationship/provider history re-read",
    "exact opportunity+target+channel/address lease acquired",
    "source/deadline/eligibility facts revalidated",
    "human approval of target-specific draft and commercial ask",
    "separate sender with explicit external authority",
]
_ALLOWED_CHANNELS = {"email", "portal", "phone", "linkedin", "other"}
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{1,127}$")


class CaptureError(ValueError):
    pass


def _nfc_text(name: str, value: object, *, max_len: int = 512) -> str:
    if not isinstance(value, str):
        raise CaptureError(f"{name} must be a string")
    out = unicodedata.normalize("NFC", value).strip()
    if not out or len(out) > max_len:
        raise CaptureError(f"{name} must be non-empty and <= {max_len} characters")
    if any(unicodedata.category(ch) in {"Cc", "Cf", "Zl", "Zp"} for ch in out):
        raise CaptureError(f"{name} contains a control/format/separator character")
    return out


def _identifier(name: str, value: object) -> str:
    out = _nfc_text(name, value, max_len=128)
    if not _ID_RE.fullmatch(out):
        raise CaptureError(f"{name} must match {_ID_RE.pattern}")
    return out


def _utc(value: object, name: str) -> datetime:
    text = _nfc_text(name, value, max_len=64)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CaptureError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise CaptureError(f"{name} must carry a timezone")
    return parsed.astimezone(timezone.utc)


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_obj(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def collision_key(*, opportunity_id: str, target_company: str, channel: str, address: str) -> str:
    opp = _identifier("opportunity_id", opportunity_id).casefold()
    company = _nfc_text("target_company", target_company, max_len=256).casefold()
    chan = _nfc_text("channel", channel, max_len=32).casefold()
    if chan not in _ALLOWED_CHANNELS:
        raise CaptureError(f"unsupported channel: {chan}")
    addr = _nfc_text("address", address, max_len=320).casefold()
    seam = {"opportunity_id": opp, "target_company": company, "channel": chan, "address": addr}
    return "psw:v1:" + sha256_obj(seam)


@dataclass(frozen=True)
class Evidence:
    source_url: str
    captured_at: str
    authority: str
    facts: tuple[str, ...]

    def validate(self, as_of: datetime, freshness_days: int) -> dict[str, Any]:
        url = _nfc_text("source_url", self.source_url, max_len=2048)
        if not (url.startswith("https://") or url.startswith("http://")):
            raise CaptureError("source_url must be http(s)")
        captured = _utc(self.captured_at, "captured_at")
        if captured > as_of:
            raise CaptureError("evidence captured_at cannot be in the future")
        age_seconds = (as_of - captured).total_seconds()
        fresh = age_seconds <= freshness_days * 86400
        authority = _nfc_text("authority", self.authority, max_len=64)
        facts = tuple(_nfc_text("fact", f, max_len=1000) for f in self.facts)
        if not facts:
            raise CaptureError("evidence must contain at least one bounded fact")
        return {
            "source_url": url,
            "captured_at": captured.isoformat().replace("+00:00", "Z"),
            "authority": authority,
            "facts": list(facts),
            "fresh": fresh,
            "age_days": round(age_seconds / 86400, 6),
        }


@dataclass(frozen=True)
class WorkshareModule:
    module_id: str
    name: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    acceptance: tuple[str, ...]
    exclusions: tuple[str, ...]

    def validate(self) -> dict[str, Any]:
        mid = _identifier("module_id", self.module_id)
        name = _nfc_text("module_name", self.name, max_len=160)
        def seq(label: str, items: Iterable[str]) -> list[str]:
            vals = [_nfc_text(label, x, max_len=800) for x in items]
            if not vals:
                raise CaptureError(f"{label} cannot be empty")
            return vals
        return {
            "module_id": mid,
            "name": name,
            "inputs": seq("input", self.inputs),
            "outputs": seq("output", self.outputs),
            "acceptance": seq("acceptance", self.acceptance),
            "exclusions": seq("exclusion", self.exclusions),
        }


@dataclass(frozen=True)
class PricingShape:
    price_id: str
    name: str
    amount_usd: int
    duration_weeks_min: int
    duration_weeks_max: int
    scope: tuple[str, ...]
    status: str = STATUS

    def validate(self) -> dict[str, Any]:
        pid = _identifier("price_id", self.price_id)
        name = _nfc_text("price_name", self.name, max_len=160)
        if isinstance(self.amount_usd, bool) or not isinstance(self.amount_usd, int) or self.amount_usd <= 0:
            raise CaptureError("amount_usd must be a positive integer")
        if not (1 <= self.duration_weeks_min <= self.duration_weeks_max <= 52):
            raise CaptureError("invalid pricing duration")
        if self.status != STATUS:
            raise CaptureError(f"pricing status must remain {STATUS}")
        scope = [_nfc_text("price_scope", s, max_len=800) for s in self.scope]
        if not scope:
            raise CaptureError("pricing scope cannot be empty")
        return {
            "price_id": pid,
            "name": name,
            "amount_usd": self.amount_usd,
            "duration_weeks_min": self.duration_weeks_min,
            "duration_weeks_max": self.duration_weeks_max,
            "scope": scope,
            "status": self.status,
        }


def _validate_opportunity(op: Mapping[str, Any], *, as_of: datetime, freshness_days: int) -> dict[str, Any]:
    allowed = {
        "opportunity_id", "buyer", "title", "deadline", "scope_summary", "workshare_wedge",
        "prime_owned", "named_target_candidates", "evidence", "modules", "deadline_authority",
    }
    unknown = set(op) - allowed
    if unknown:
        raise CaptureError(f"unknown opportunity keys: {sorted(unknown)}")
    oid = _identifier("opportunity_id", op.get("opportunity_id"))
    buyer = _nfc_text("buyer", op.get("buyer"), max_len=256)
    title = _nfc_text("title", op.get("title"), max_len=300)
    deadline = _utc(op.get("deadline"), "deadline")
    scope = _nfc_text("scope_summary", op.get("scope_summary"), max_len=2000)
    wedge = [_nfc_text("workshare_wedge", x, max_len=800) for x in op.get("workshare_wedge", [])]
    prime_owned = [_nfc_text("prime_owned", x, max_len=800) for x in op.get("prime_owned", [])]
    if not wedge or not prime_owned:
        raise CaptureError("workshare_wedge and prime_owned must be non-empty")
    modules = [_identifier("module", x) for x in op.get("modules", [])]
    if not modules:
        raise CaptureError("opportunity must map at least one module")
    candidates = []
    for row in op.get("named_target_candidates", []):
        if not isinstance(row, Mapping):
            raise CaptureError("target candidate must be an object")
        company = _nfc_text("candidate.company", row.get("company"), max_len=256)
        evidence_status = _nfc_text("candidate.evidence_status", row.get("evidence_status"), max_len=64)
        if evidence_status not in {"FIRST_PARTY_VERIFIED", "REVALIDATE_BEFORE_OUTREACH"}:
            raise CaptureError("unsupported target evidence_status")
        candidates.append({"company": company, "evidence_status": evidence_status})
    ev_rows = []
    for row in op.get("evidence", []):
        if not isinstance(row, Mapping):
            raise CaptureError("evidence row must be an object")
        ev = Evidence(
            source_url=row.get("source_url"), captured_at=row.get("captured_at"),
            authority=row.get("authority"), facts=tuple(row.get("facts", [])),
        )
        ev_rows.append(ev.validate(as_of, freshness_days))
    if not ev_rows:
        raise CaptureError("opportunity requires source evidence")
    deadline_authority = _nfc_text("deadline_authority", op.get("deadline_authority"), max_len=64)
    if deadline_authority not in {"FIRST_PARTY_VERIFIED", "REVALIDATE_BEFORE_REPRESENTATION"}:
        raise CaptureError("invalid deadline_authority")
    return {
        "opportunity_id": oid,
        "buyer": buyer,
        "title": title,
        "deadline": deadline.isoformat().replace("+00:00", "Z"),
        "deadline_open_at_compile": deadline > as_of,
        "deadline_authority": deadline_authority,
        "scope_summary": scope,
        "workshare_wedge": wedge,
        "prime_owned": prime_owned,
        "named_target_candidates": candidates,
        "modules": modules,
        "evidence": ev_rows,
        "all_evidence_fresh": all(x["fresh"] for x in ev_rows),
    }


def compile_pack(manifest: Mapping[str, Any], *, as_of: str | datetime, freshness_days: int = 7) -> dict[str, Any]:
    if isinstance(as_of, datetime):
        now = as_of.astimezone(timezone.utc)
    else:
        now = _utc(as_of, "as_of")
    if not isinstance(freshness_days, int) or isinstance(freshness_days, bool) or not (1 <= freshness_days <= 30):
        raise CaptureError("freshness_days must be an integer from 1 to 30")
    if manifest.get("schema") != SCHEMA:
        raise CaptureError(f"schema must be {SCHEMA}")
    if manifest.get("commercial_status") != STATUS:
        raise CaptureError(f"commercial_status must be {STATUS}")
    if manifest.get("external_send_authorized") is not SEND_AUTHORIZED:
        raise CaptureError("external_send_authorized must be false")

    modules = [WorkshareModule(**m).validate() for m in manifest.get("modules", [])]
    if len({m["module_id"] for m in modules}) != len(modules) or not modules:
        raise CaptureError("module IDs must be unique and non-empty")
    module_ids = {m["module_id"] for m in modules}

    prices = [PricingShape(**p).validate() for p in manifest.get("pricing", [])]
    if len({p["price_id"] for p in prices}) != len(prices) or not prices:
        raise CaptureError("price IDs must be unique and non-empty")

    opportunities = [_validate_opportunity(o, as_of=now, freshness_days=freshness_days)
                     for o in manifest.get("opportunities", [])]
    if len({o["opportunity_id"] for o in opportunities}) != len(opportunities) or not opportunities:
        raise CaptureError("opportunity IDs must be unique and non-empty")
    for op in opportunities:
        missing = sorted(set(op["modules"]) - module_ids)
        if missing:
            raise CaptureError(f"{op['opportunity_id']} references unknown modules: {missing}")

    packet = {
        "schema": SCHEMA,
        "as_of": now.isoformat().replace("+00:00", "Z"),
        "freshness_days": freshness_days,
        "commercial_status": STATUS,
        "external_send_authorized": False,
        "authority_ceiling": list(AUTHORITY_CEILING),
        "modules": sorted(modules, key=lambda x: x["module_id"]),
        "pricing": sorted(prices, key=lambda x: x["price_id"]),
        "opportunities": sorted(opportunities, key=lambda x: x["opportunity_id"]),
        "outbound_preconditions": list(OUTBOUND_PRECONDITIONS),
    }
    packet["packet_sha256"] = sha256_obj(packet)
    return packet


def verify_packet(packet: Mapping[str, Any]) -> bool:
    if not isinstance(packet, Mapping):
        return False
    body = dict(packet)
    supplied = body.pop("packet_sha256", None)
    return isinstance(supplied, str) and len(supplied) == 64 and supplied == sha256_obj(body)


def _strict_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise CaptureError(f"{name} must be a boolean")
    return value


def validate_compiled_pack(pack: Mapping[str, Any]) -> dict[str, Any]:
    """Re-derive the compiler's authority-critical fields before downstream use.

    A digest proves byte integrity, not semantic authority.  Target packets therefore
    revalidate the compiled structure and every freshness/deadline derivation instead
    of trusting a caller-resealed JSON object.
    """
    if not isinstance(pack, Mapping) or not verify_packet(pack):
        raise CaptureError("capture pack receipt is invalid")
    expected_top = {
        "schema", "as_of", "freshness_days", "commercial_status",
        "external_send_authorized", "authority_ceiling", "modules", "pricing",
        "opportunities", "outbound_preconditions", "packet_sha256",
    }
    unknown = set(pack) - expected_top
    missing = expected_top - set(pack)
    if unknown or missing:
        raise CaptureError(f"compiled pack shape mismatch: unknown={sorted(unknown)} missing={sorted(missing)}")
    if pack.get("schema") != SCHEMA or pack.get("commercial_status") != STATUS:
        raise CaptureError("compiled pack schema/commercial status mismatch")
    if pack.get("external_send_authorized") is not False:
        raise CaptureError("compiled pack cannot grant external send authority")
    if pack.get("authority_ceiling") != AUTHORITY_CEILING:
        raise CaptureError("compiled pack authority ceiling mismatch")
    if pack.get("outbound_preconditions") != OUTBOUND_PRECONDITIONS:
        raise CaptureError("compiled pack outbound preconditions mismatch")
    as_of = _utc(pack.get("as_of"), "pack.as_of")
    freshness_days = pack.get("freshness_days")
    if type(freshness_days) is not int or not (1 <= freshness_days <= 30):
        raise CaptureError("compiled freshness_days invalid")

    modules = pack.get("modules")
    if not isinstance(modules, list) or not modules:
        raise CaptureError("compiled modules must be a non-empty list")
    module_ids: set[str] = set()
    for row in modules:
        if not isinstance(row, Mapping) or set(row) != {"module_id", "name", "inputs", "outputs", "acceptance", "exclusions"}:
            raise CaptureError("compiled module shape invalid")
        normalized = WorkshareModule(
            module_id=row.get("module_id"), name=row.get("name"),
            inputs=tuple(row.get("inputs", [])), outputs=tuple(row.get("outputs", [])),
            acceptance=tuple(row.get("acceptance", [])), exclusions=tuple(row.get("exclusions", [])),
        ).validate()
        if normalized != dict(row):
            raise CaptureError("compiled module is not canonical")
        if normalized["module_id"] in module_ids:
            raise CaptureError("duplicate compiled module_id")
        module_ids.add(normalized["module_id"])

    pricing = pack.get("pricing")
    if not isinstance(pricing, list) or not pricing:
        raise CaptureError("compiled pricing must be a non-empty list")
    price_ids: set[str] = set()
    for row in pricing:
        if not isinstance(row, Mapping) or set(row) != {
            "price_id", "name", "amount_usd", "duration_weeks_min",
            "duration_weeks_max", "scope", "status"
        }:
            raise CaptureError("compiled pricing shape invalid")
        normalized = PricingShape(
            price_id=row.get("price_id"), name=row.get("name"), amount_usd=row.get("amount_usd"),
            duration_weeks_min=row.get("duration_weeks_min"), duration_weeks_max=row.get("duration_weeks_max"),
            scope=tuple(row.get("scope", [])), status=row.get("status"),
        ).validate()
        if normalized != dict(row):
            raise CaptureError("compiled pricing is not canonical")
        if normalized["price_id"] in price_ids:
            raise CaptureError("duplicate compiled price_id")
        price_ids.add(normalized["price_id"])

    opportunities = pack.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        raise CaptureError("compiled opportunities must be a non-empty list")
    opportunity_ids: set[str] = set()
    expected_op_keys = {
        "opportunity_id", "buyer", "title", "deadline", "deadline_open_at_compile",
        "deadline_authority", "scope_summary", "workshare_wedge", "prime_owned",
        "named_target_candidates", "modules", "evidence", "all_evidence_fresh",
    }
    for op in opportunities:
        if not isinstance(op, Mapping) or set(op) != expected_op_keys:
            raise CaptureError("compiled opportunity shape invalid")
        oid = _identifier("compiled.opportunity_id", op.get("opportunity_id"))
        if oid in opportunity_ids:
            raise CaptureError("duplicate compiled opportunity_id")
        opportunity_ids.add(oid)
        _nfc_text("compiled.buyer", op.get("buyer"), max_len=256)
        _nfc_text("compiled.title", op.get("title"), max_len=300)
        _nfc_text("compiled.scope_summary", op.get("scope_summary"), max_len=2000)
        deadline = _utc(op.get("deadline"), "compiled.deadline")
        if type(op.get("deadline_open_at_compile")) is not bool or op["deadline_open_at_compile"] != (deadline > as_of):
            raise CaptureError("compiled deadline-open derivation mismatch")
        if op.get("deadline_authority") not in {"FIRST_PARTY_VERIFIED", "REVALIDATE_BEFORE_REPRESENTATION"}:
            raise CaptureError("compiled deadline authority invalid")
        if not isinstance(op.get("modules"), list) or not op["modules"]:
            raise CaptureError("compiled opportunity modules invalid")
        for mid in op["modules"]:
            if _identifier("compiled.module", mid) not in module_ids:
                raise CaptureError("compiled opportunity references unknown module")
        for seq_name in ("workshare_wedge", "prime_owned"):
            seq = op.get(seq_name)
            if not isinstance(seq, list) or not seq:
                raise CaptureError(f"compiled {seq_name} invalid")
            for item in seq:
                _nfc_text(f"compiled.{seq_name}", item, max_len=800)
        candidates = op.get("named_target_candidates")
        if not isinstance(candidates, list):
            raise CaptureError("compiled candidates invalid")
        for candidate in candidates:
            if not isinstance(candidate, Mapping) or set(candidate) != {"company", "evidence_status"}:
                raise CaptureError("compiled candidate shape invalid")
            _nfc_text("compiled.candidate.company", candidate.get("company"), max_len=256)
            if candidate.get("evidence_status") not in {"FIRST_PARTY_VERIFIED", "REVALIDATE_BEFORE_OUTREACH"}:
                raise CaptureError("compiled candidate evidence status invalid")
        evidence = op.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise CaptureError("compiled evidence invalid")
        derived_fresh = []
        for ev in evidence:
            if not isinstance(ev, Mapping) or set(ev) != {
                "source_url", "captured_at", "authority", "facts", "fresh", "age_days"
            }:
                raise CaptureError("compiled evidence shape invalid")
            normalized = Evidence(
                source_url=ev.get("source_url"), captured_at=ev.get("captured_at"),
                authority=ev.get("authority"), facts=tuple(ev.get("facts", [])),
            ).validate(as_of, freshness_days)
            if normalized != dict(ev):
                raise CaptureError("compiled evidence freshness/canonicalization mismatch")
            derived_fresh.append(normalized["fresh"])
        if type(op.get("all_evidence_fresh")) is not bool or op["all_evidence_fresh"] != all(derived_fresh):
            raise CaptureError("compiled opportunity freshness derivation mismatch")
    return dict(pack)


def build_target_packet(pack: Mapping[str, Any], *, opportunity_id: str, target_company: str,
                        channel: str, address: str, relationship_checked: bool,
                        lease_acquired: bool, provider_history_rechecked: bool,
                        opportunity_facts_revalidated: bool) -> dict[str, Any]:
    validated = validate_compiled_pack(pack)
    relationship_checked = _strict_bool("relationship_checked", relationship_checked)
    lease_acquired = _strict_bool("lease_acquired", lease_acquired)
    provider_history_rechecked = _strict_bool("provider_history_rechecked", provider_history_rechecked)
    opportunity_facts_revalidated = _strict_bool("opportunity_facts_revalidated", opportunity_facts_revalidated)
    oid = _identifier("opportunity_id", opportunity_id)
    selected = next((o for o in validated["opportunities"] if o["opportunity_id"] == oid), None)
    if selected is None:
        raise CaptureError("unknown opportunity_id")
    seam = collision_key(opportunity_id=oid, target_company=target_company, channel=channel, address=address)
    controls_clear = all((relationship_checked, lease_acquired, provider_history_rechecked, opportunity_facts_revalidated))
    source_clear = bool(selected["all_evidence_fresh"] and selected["deadline_open_at_compile"])
    ready_for_owner_review = controls_clear and source_clear
    hold_reasons: list[str] = []
    if not relationship_checked:
        hold_reasons.append("RELATIONSHIP_HISTORY_NOT_CHECKED")
    if not lease_acquired:
        hold_reasons.append("EXACT_TARGET_LEASE_NOT_ACQUIRED")
    if not provider_history_rechecked:
        hold_reasons.append("PROVIDER_HISTORY_NOT_RECHECKED")
    if not opportunity_facts_revalidated:
        hold_reasons.append("OPPORTUNITY_FACTS_NOT_REVALIDATED")
    if not selected["all_evidence_fresh"]:
        hold_reasons.append("SOURCE_EVIDENCE_STALE")
    if not selected["deadline_open_at_compile"]:
        hold_reasons.append("OPPORTUNITY_DEADLINE_CLOSED")
    out = {
        "schema": "tjl.public-sector-workshare-target/v1",
        "capture_pack_sha256": validated["packet_sha256"],
        "opportunity_id": oid,
        "target_company": _nfc_text("target_company", target_company, max_len=256),
        "channel": _nfc_text("channel", channel, max_len=32).casefold(),
        "address": _nfc_text("address", address, max_len=320),
        "collision_key": seam,
        "relationship_checked": relationship_checked,
        "lease_acquired": lease_acquired,
        "provider_history_rechecked": provider_history_rechecked,
        "opportunity_facts_revalidated": opportunity_facts_revalidated,
        "source_evidence_fresh": selected["all_evidence_fresh"],
        "deadline_open_at_compile": selected["deadline_open_at_compile"],
        "controls_clear": controls_clear,
        "ready_for_owner_transport_review": ready_for_owner_review,
        "hold_reasons": hold_reasons,
        "state": "READY_FOR_OWNER_TRANSPORT_REVIEW" if ready_for_owner_review else "HOLD",
        "external_send_authorized": False,
        "commercial_status": STATUS,
    }
    out["packet_sha256"] = sha256_obj(out)
    return out
