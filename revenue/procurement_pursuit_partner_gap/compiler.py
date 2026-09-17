"""Evidence-bound pursuit gap -> partner capability shortlist compiler.

Consumes an exact verified generation from procurement_response_module_library.materializer
plus retained pursuit requirement sources. It performs deterministic crosswalk decisions;
it does not perform semantic matching, authenticate source providers, recommend partners,
or authorize external actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from revenue.procurement_response_module_library import materializer

REQUEST = "procurement-pursuit-partner-gap/request/v1"
PACKET = "procurement-pursuit-partner-gap/packet/v1"
RECEIPT = "procurement-pursuit-partner-gap/receipt/v1"
TRUTH_BOUNDARY = "RETAINED_REQUIREMENTS_AND_VERIFIED_MATERIALIZER_GENERATION_NOT_PROVIDER_AUTHENTICATION"
CARRIER_MODES = {"SYNTHETIC_ONLY", "RETAINED_CURRENT"}
AUTHORITIES = {"BUYER_OFFICIAL", "SYNTHETIC_FIXTURE"}
MAPPING = {"APPROVED", "PENDING", "NONE"}
PROOF_STATUS = {"VERIFIED", "PROVISIONAL"}
CLAIM_KINDS = {"CAPABILITY", "POLICY", "CERTIFICATION", "REFERENCE", "SLA", "SECURITY_CONTROL"}
FAMILIES = {
    "corporate_capability", "ai_data_governance", "cybersecurity", "accessibility",
    "implementation_delivery", "sla_support", "staffing", "references_past_performance",
    "pricing_assumptions", "subcontractor_partner_matrix", "compliance_crosswalk",
}
REQUIRED_PROOF = {
    "CAPABILITY": {"CAPABILITY_PROOF"},
    "POLICY": {"POLICY_PROOF"},
    "CERTIFICATION": {"ISSUER_VERIFIED_CERTIFICATION"},
    "REFERENCE": {"REFERENCE_PERMISSION_RECEIPT"},
    "SLA": {"ACCEPTED_SLA_RECEIPT"},
    "SECURITY_CONTROL": {"CONTROL_TEST_RECEIPT"},
}
PROOF_KINDS = set().union(*REQUIRED_PROOF.values())
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class Error(ValueError):
    pass


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise Error(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _bad_number(value):
    raise Error(f"non-integer JSON number forbidden: {value}")


def load(raw: bytes, label: str = "input"):
    if not isinstance(raw, (bytes, bytearray)):
        raise Error(f"{label}: bytes required")
    raw = bytes(raw)
    if raw.startswith(b"\xef\xbb\xbf"):
        raise Error(f"{label}: BOM forbidden")
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_pairs,
            parse_float=_bad_number, parse_constant=_bad_number,
        )
    except Error:
        raise
    except Exception as exc:
        raise Error(f"{label}: invalid JSON/UTF-8") from exc
    if not isinstance(value, dict):
        raise Error(f"{label}: object required")
    return value


def canon(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _keys(value, expected, where):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise Error(f"{where}: keys mismatch")


def _text(value, where, *, token=False, limit=4096):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise Error(f"{where}: invalid string")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise Error(f"{where}: non-scalar Unicode") from exc
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
        raise Error(f"{where}: invalid control character")
    if token and not TOKEN.fullmatch(value):
        raise Error(f"{where}: invalid token")
    return value


def _integer(value, where, low=0, high=10**9):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise Error(f"{where}: integer required")
    return value


def _sha(value, where):
    value = _text(value, where, limit=64)
    if not SHA.fullmatch(value):
        raise Error(f"{where}: sha256 required")
    return value


def _timestamp(value, where):
    value = _text(value, where, limit=20)
    try:
        if not TS.fullmatch(value):
            raise ValueError
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise Error(f"{where}: RFC3339 UTC second timestamp required") from exc
    return value


def _dt(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _https_uri(value, where):
    value = _text(value, where, limit=2048)
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise Error(f"{where}: credential-free https URI required")
    return value


def _tokens(value, where, *, minimum=0, maximum=64):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise Error(f"{where}: invalid list")
    out = [_text(item, f"{where}[{i}]", token=True, limit=128) for i, item in enumerate(value)]
    if len(out) != len(set(out)):
        raise Error(f"{where}: duplicate item")
    return sorted(out)


def _stable_id(prefix, *parts):
    return f"{prefix}-{digest(canon(list(parts)))[:24]}"


def _authority():
    return {
        "source_provider_authenticated": False,
        "buyer_officialness_authenticated": False,
        "partner_recommended": False,
        "partner_contact_authorized": False,
        "buyer_contact_authorized": False,
        "email_or_outreach_authorized": False,
        "bid_or_submission_authorized": False,
        "signature_authorized": False,
        "price_commitment_authorized": False,
        "qualification_certified": False,
        "award_recognized": False,
        "invoice_or_payment_authorized": False,
        "revenue_recognized": False,
    }


def _source(value, where):
    _keys(value, ("uri", "sha256", "observed_at", "expires_at", "authority"), where)
    authority = _text(value["authority"], where + ".authority", token=True, limit=32)
    if authority not in AUTHORITIES:
        raise Error(where + ": unsupported authority")
    return {
        "uri": _https_uri(value["uri"], where + ".uri"),
        "sha256": _sha(value["sha256"], where + ".sha256"),
        "observed_at": _timestamp(value["observed_at"], where + ".observed_at"),
        "expires_at": _timestamp(value["expires_at"], where + ".expires_at"),
        "authority": authority,
    }


def _requirement(value, where):
    _keys(value, (
        "requirement_id", "text", "text_sha256", "family", "claim_kind",
        "applicability_tags", "mapping_approval", "internal_claim_id",
        "partner_eligible", "capability_key", "required_proof_kind",
        "partner_deliverable",
    ), where)
    text = _text(value["text"], where + ".text")
    if digest(text.encode("utf-8")) != _sha(value["text_sha256"], where + ".text_sha256"):
        raise Error(where + ": text_sha256 mismatch")
    family = _text(value["family"], where + ".family", token=True)
    claim_kind = _text(value["claim_kind"], where + ".claim_kind", token=True)
    if family not in FAMILIES or claim_kind not in CLAIM_KINDS:
        raise Error(where + ": unsupported family/claim_kind")
    mapping = _text(value["mapping_approval"], where + ".mapping_approval", token=True)
    if mapping not in MAPPING:
        raise Error(where + ": unsupported mapping_approval")
    internal = value["internal_claim_id"]
    if internal is not None:
        internal = _text(internal, where + ".internal_claim_id", token=True)
    if mapping == "APPROVED" and internal is None:
        raise Error(where + ": APPROVED mapping requires internal_claim_id")
    if mapping == "NONE" and internal is not None:
        raise Error(where + ": NONE mapping forbids internal_claim_id")
    if not isinstance(value["partner_eligible"], bool):
        raise Error(where + ".partner_eligible: bool required")
    proof = _text(value["required_proof_kind"], where + ".required_proof_kind", token=True)
    if proof not in REQUIRED_PROOF[claim_kind]:
        raise Error(where + ": required_proof_kind incompatible with claim_kind")
    return {
        "requirement_id": _text(value["requirement_id"], where + ".requirement_id", token=True),
        "text": text,
        "text_sha256": value["text_sha256"],
        "family": family,
        "claim_kind": claim_kind,
        "applicability_tags": _tokens(value["applicability_tags"], where + ".applicability_tags", minimum=1),
        "mapping_approval": mapping,
        "internal_claim_id": internal,
        "partner_eligible": value["partner_eligible"],
        "capability_key": _text(value["capability_key"], where + ".capability_key", token=True),
        "required_proof_kind": proof,
        "partner_deliverable": _text(value["partner_deliverable"], where + ".partner_deliverable", limit=512),
    }


def _prime_proof(value, where):
    _keys(value, (
        "proof_id", "requirement_id", "proof_kind", "source_ref", "source_sha256",
        "verified_at", "expires_at", "status",
    ), where)
    status = _text(value["status"], where + ".status", token=True)
    if status not in PROOF_STATUS:
        raise Error(where + ": unsupported proof status")
    proof_kind = _text(value["proof_kind"], where + ".proof_kind", token=True)
    if proof_kind not in PROOF_KINDS:
        raise Error(where + ": unsupported proof_kind")
    return {
        "proof_id": _text(value["proof_id"], where + ".proof_id", token=True),
        "requirement_id": _text(value["requirement_id"], where + ".requirement_id", token=True),
        "proof_kind": proof_kind,
        "source_ref": _https_uri(value["source_ref"], where + ".source_ref"),
        "source_sha256": _sha(value["source_sha256"], where + ".source_sha256"),
        "verified_at": _timestamp(value["verified_at"], where + ".verified_at"),
        "expires_at": _timestamp(value["expires_at"], where + ".expires_at"),
        "status": status,
    }


def _normalize_request(value):
    _keys(value, (
        "schema", "generated_at", "max_pursuit_source_age_seconds", "truth_boundary",
        "carrier_mode", "pursuits", "prime_proofs",
    ), "request")
    if value["schema"] != REQUEST or value["truth_boundary"] != TRUTH_BOUNDARY:
        raise Error("request: unsupported schema/truth_boundary")
    generated_at = _timestamp(value["generated_at"], "request.generated_at")
    max_age = _integer(value["max_pursuit_source_age_seconds"], "request.max_pursuit_source_age_seconds", 1, 31536000)
    carrier_mode = _text(value["carrier_mode"], "request.carrier_mode", token=True, limit=32)
    if carrier_mode not in CARRIER_MODES:
        raise Error("request: unsupported carrier_mode")
    if not isinstance(value["pursuits"], list) or not value["pursuits"]:
        raise Error("request.pursuits: non-empty list required")
    pursuits = []
    pursuit_ids = set()
    requirement_ids = set()
    for i, raw in enumerate(value["pursuits"]):
        where = f"request.pursuits[{i}]"
        _keys(raw, ("pursuit_id", "title", "source", "requirements"), where)
        pursuit_id = _text(raw["pursuit_id"], where + ".pursuit_id", token=True)
        if pursuit_id in pursuit_ids:
            raise Error(where + ": duplicate pursuit_id")
        pursuit_ids.add(pursuit_id)
        source = _source(raw["source"], where + ".source")
        if not isinstance(raw["requirements"], list) or not raw["requirements"]:
            raise Error(where + ".requirements: non-empty list required")
        requirements = []
        for j, rr in enumerate(raw["requirements"]):
            requirement = _requirement(rr, f"{where}.requirements[{j}]")
            if requirement["requirement_id"] in requirement_ids:
                raise Error(f"{where}.requirements[{j}]: duplicate global requirement_id")
            requirement_ids.add(requirement["requirement_id"])
            requirements.append(requirement)
        pursuits.append({
            "pursuit_id": pursuit_id,
            "title": _text(raw["title"], where + ".title", limit=256),
            "source": source,
            "requirements": sorted(requirements, key=lambda row: row["requirement_id"]),
        })
    if not isinstance(value["prime_proofs"], list):
        raise Error("request.prime_proofs: list required")
    proofs = []
    proof_ids = set()
    for i, raw in enumerate(value["prime_proofs"]):
        proof = _prime_proof(raw, f"request.prime_proofs[{i}]")
        if proof["proof_id"] in proof_ids:
            raise Error(f"request.prime_proofs[{i}]: duplicate proof_id")
        if proof["requirement_id"] not in requirement_ids:
            raise Error(f"request.prime_proofs[{i}]: orphan requirement_id")
        proof_ids.add(proof["proof_id"])
        proofs.append(proof)
    return {
        "generated_at": generated_at,
        "max_pursuit_source_age_seconds": max_age,
        "carrier_mode": carrier_mode,
        "pursuits": sorted(pursuits, key=lambda row: row["pursuit_id"]),
        "prime_proofs": sorted(proofs, key=lambda row: row["proof_id"]),
    }


def _source_reasons(source, generated_at, max_age):
    reasons = []
    now = _dt(generated_at)
    observed = _dt(source["observed_at"])
    expires = _dt(source["expires_at"])
    if observed > now:
        reasons.append("SOURCE_OBSERVED_IN_FUTURE")
    if expires < now:
        reasons.append("SOURCE_EXPIRED")
    if int((now - observed).total_seconds()) > max_age:
        reasons.append("SOURCE_STALE")
    if source["authority"] != "BUYER_OFFICIAL":
        reasons.append("SOURCE_NOT_RETAINED_BUYER_OFFICIAL")
    return sorted(set(reasons))


def _proof_reasons(proof, requirement, generated_at):
    reasons = []
    now = _dt(generated_at)
    if proof["status"] != "VERIFIED":
        reasons.append("PRIME_PROOF_NOT_VERIFIED")
    if _dt(proof["verified_at"]) > now:
        reasons.append("PRIME_PROOF_VERIFIED_IN_FUTURE")
    if _dt(proof["expires_at"]) < now:
        reasons.append("PRIME_PROOF_EXPIRED")
    if proof["proof_kind"] != requirement["required_proof_kind"]:
        reasons.append("PRIME_PROOF_KIND_MISMATCH")
    return sorted(set(reasons))


def _materializer_indexes(source_raw, catalog_raw):
    try:
        normalized = materializer.normalize_source(materializer.load(source_raw, "materializer_source"))
        catalog = materializer.load(catalog_raw, "materializer_catalog")
    except materializer.Error as exc:
        raise Error(f"materializer generation invalid: {exc}") from exc

    records = {row["claim_id"]: row for row in normalized["records"]}
    approved_modules = {}
    evidence_status = {}
    for evidence in catalog.get("evidence", []):
        if isinstance(evidence, dict) and isinstance(evidence.get("evidence_id"), str):
            evidence_status[evidence["evidence_id"]] = evidence.get("status")
    for module in catalog.get("modules", []):
        if not isinstance(module, dict):
            continue
        for claim in module.get("claims", []):
            if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str):
                approved_modules[claim["claim_id"]] = {
                    "module_id": module.get("module_id"),
                    "owner_status": module.get("owner_status"),
                    "family": module.get("family"),
                    "tags": module.get("tags"),
                    "evidence_ids": claim.get("evidence_ids", []),
                    "claim_text": claim.get("text"),
                }
    return normalized, catalog, records, approved_modules, evidence_status


def _classify(requirement, source_reasons, proofs, generated_at, records, modules, evidence_status, internal_max_age):
    if source_reasons:
        return "OWNER_INPUT", source_reasons, [], []
    mapping = requirement["mapping_approval"]
    if mapping == "PENDING":
        return "OWNER_INPUT", ["INTERNAL_MAPPING_PENDING"], [], []

    if mapping == "APPROVED":
        claim_id = requirement["internal_claim_id"]
        record = records.get(claim_id)
        module = modules.get(claim_id)
        reasons = []
        if record is None or module is None:
            reasons.append("APPROVED_INTERNAL_CLAIM_NOT_IN_VERIFIED_GENERATION")
        else:
            if record.get("materialized_status") != "SUPPORTED":
                reasons.append("INTERNAL_EVIDENCE_NOT_SUPPORTED")
            if module.get("owner_status") != "APPROVED":
                reasons.append("INTERNAL_MODULE_NOT_APPROVED")
            now = _dt(generated_at)
            observed = _dt(record["observed_at"])
            expires = _dt(record["expires_at"])
            valid_from = _dt(record["valid_from"])
            valid_until = _dt(record["valid_until"])
            if observed > now:
                reasons.append("INTERNAL_EVIDENCE_OBSERVED_IN_FUTURE")
            if expires < now:
                reasons.append("INTERNAL_EVIDENCE_EXPIRED")
            if int((now - observed).total_seconds()) > internal_max_age:
                reasons.append("INTERNAL_EVIDENCE_STALE")
            if not valid_from <= now <= valid_until:
                reasons.append("INTERNAL_MODULE_OUTSIDE_VALIDITY_WINDOW")
            if record.get("family") != requirement["family"] or record.get("claim_kind") != requirement["claim_kind"]:
                reasons.append("INTERNAL_MAPPING_TYPE_MISMATCH")
            record_tags = set(record.get("applicability_tags", []))
            if not set(requirement["applicability_tags"]).issubset(record_tags):
                reasons.append("INTERNAL_APPLICABILITY_MISMATCH")
            evidence_ids = module.get("evidence_ids", [])
            if not isinstance(evidence_ids, list) or not evidence_ids:
                reasons.append("INTERNAL_EVIDENCE_MISSING")
            elif any(evidence_status.get(eid) != "SUPPORTED" for eid in evidence_ids):
                reasons.append("INTERNAL_EVIDENCE_NOT_SUPPORTED")
        if reasons:
            return "OWNER_INPUT", sorted(set(reasons)), [], []
        return "PASS", ["VERIFIED_MATERIALIZED_INTERNAL_CLAIM"], [record["module_id"], record["evidence_id"]], []

    proof_rows = proofs
    if proof_rows:
        failures = []
        for proof in proof_rows:
            failures.extend(_proof_reasons(proof, requirement, generated_at))
        if failures:
            return "OWNER_INPUT", sorted(set(failures + ["PRIME_PROOF_SET_REQUIRES_OWNER_REVIEW"])), [], [p["proof_id"] for p in proof_rows]
        return "PRIME_SUPPORTED", ["CURRENT_VERIFIED_PRIME_PROOF"], [], sorted(p["proof_id"] for p in proof_rows)

    if requirement["partner_eligible"]:
        return "PARTNER_REQUIRED", ["NO_INTERNAL_MAPPING_OR_CURRENT_PRIME_PROOF"], [], []
    return "OWNER_INPUT", ["NO_APPROVED_COVERAGE_ROUTE"], [], []


def compile_gap(
    request_raw: bytes,
    materializer_source_raw: bytes,
    materializer_catalog_raw: bytes,
    materializer_diff_raw: bytes,
    materializer_receipt_raw: bytes,
    materializer_previous_raw: bytes | None = None,
):
    request_obj = _normalize_request(load(request_raw, "request"))
    try:
        verified = materializer.verify_materializer(
            materializer_source_raw, materializer_catalog_raw, materializer_diff_raw,
            materializer_receipt_raw, materializer_previous_raw,
        )
    except materializer.Error as exc:
        raise Error(f"materializer verification failed: {exc}") from exc
    if not verified:
        raise Error("materializer generation verification failed")

    normalized, catalog, records, modules, evidence_status = _materializer_indexes(
        materializer_source_raw, materializer_catalog_raw
    )
    if _dt(normalized["generated_at"]) > _dt(request_obj["generated_at"]):
        raise Error("materializer generation is newer than request generated_at")

    proofs_by_requirement = defaultdict(list)
    for proof in request_obj["prime_proofs"]:
        proofs_by_requirement[proof["requirement_id"]].append(proof)

    results = []
    source_audit = []
    shortlist_buckets = {}
    all_current = True
    all_buyer = True

    for pursuit in request_obj["pursuits"]:
        src_reasons = _source_reasons(
            pursuit["source"], request_obj["generated_at"],
            request_obj["max_pursuit_source_age_seconds"],
        )
        if src_reasons:
            all_current = False
        if pursuit["source"]["authority"] != "BUYER_OFFICIAL":
            all_buyer = False
        source_audit.append({
            "pursuit_id": pursuit["pursuit_id"],
            "source_uri": pursuit["source"]["uri"],
            "source_sha256": pursuit["source"]["sha256"],
            "observed_at": pursuit["source"]["observed_at"],
            "expires_at": pursuit["source"]["expires_at"],
            "retained_authority": pursuit["source"]["authority"],
            "currentness_reasons": src_reasons,
        })
        for req in pursuit["requirements"]:
            state, reasons, internal_refs, prime_refs = _classify(
                req, src_reasons, proofs_by_requirement[req["requirement_id"]],
                request_obj["generated_at"], records, modules, evidence_status,
                normalized["evidence_max_age_seconds"],
            )
            row = {
                "pursuit_id": pursuit["pursuit_id"],
                "requirement_id": req["requirement_id"],
                "state": state,
                "reasons": reasons,
                "family": req["family"],
                "claim_kind": req["claim_kind"],
                "capability_key": req["capability_key"],
                "required_proof_kind": req["required_proof_kind"],
                "internal_refs": internal_refs,
                "prime_proof_ids": prime_refs,
            }
            results.append(row)
            if state == "PARTNER_REQUIRED":
                key_payload = [
                    req["capability_key"], req["family"], req["claim_kind"],
                    req["required_proof_kind"], req["partner_deliverable"],
                ]
                key = digest(canon(key_payload))
                bucket = shortlist_buckets.setdefault(key, {
                    "shortlist_id": _stable_id("partner-need", *key_payload),
                    "capability_key": req["capability_key"],
                    "family": req["family"],
                    "claim_kind": req["claim_kind"],
                    "required_proof_kind": req["required_proof_kind"],
                    "partner_deliverable": req["partner_deliverable"],
                    "requirement_refs": [],
                    "contact_authorized": False,
                })
                bucket["requirement_refs"].append({
                    "pursuit_id": pursuit["pursuit_id"],
                    "requirement_id": req["requirement_id"],
                })

    if request_obj["carrier_mode"] == "SYNTHETIC_ONLY":
        live_status = "SYNTHETIC_ONLY"
    elif len(request_obj["pursuits"]) < 5 or not all_current or not all_buyer:
        live_status = "LIVE_MATERIALIZATION_BLOCKED_NO_VERIFIED_CARRIER_SET"
    else:
        live_status = "RETAINED_CURRENT_CARRIER_SET_READY_FOR_OWNER_REVIEW"

    counts = {state: 0 for state in ("PASS", "PRIME_SUPPORTED", "PARTNER_REQUIRED", "OWNER_INPUT")}
    for row in results:
        counts[row["state"]] += 1

    packet = {
        "schema": PACKET,
        "truth_boundary": TRUTH_BOUNDARY,
        "generated_at": request_obj["generated_at"],
        "carrier_mode": request_obj["carrier_mode"],
        "live_materialization_status": live_status,
        "materializer_generation": {
            "library_id": normalized["library_id"],
            "source_sha256": digest(materializer_source_raw),
            "catalog_sha256": digest(materializer_catalog_raw),
            "diff_sha256": digest(materializer_diff_raw),
            "receipt_sha256": digest(materializer_receipt_raw),
            "verified": True,
        },
        "counts": counts,
        "pursuit_sources": sorted(source_audit, key=lambda row: row["pursuit_id"]),
        "requirement_results": sorted(results, key=lambda row: (row["pursuit_id"], row["requirement_id"])),
        "partner_capability_shortlist": sorted(
            (
                {**row, "requirement_refs": sorted(
                    row["requirement_refs"],
                    key=lambda ref: (ref["pursuit_id"], ref["requirement_id"]),
                )}
                for row in shortlist_buckets.values()
            ),
            key=lambda row: row["shortlist_id"],
        ),
        "authority": _authority(),
    }
    packet_raw = canon(packet)
    receipt = {
        "schema": RECEIPT,
        "truth_boundary": TRUTH_BOUNDARY,
        "request_sha256": digest(request_raw),
        "materializer_source_sha256": digest(materializer_source_raw),
        "materializer_catalog_sha256": digest(materializer_catalog_raw),
        "materializer_diff_sha256": digest(materializer_diff_raw),
        "materializer_receipt_sha256": digest(materializer_receipt_raw),
        "materializer_previous_sha256": None if materializer_previous_raw is None else digest(materializer_previous_raw),
        "packet_sha256": digest(packet_raw),
        "authority": _authority(),
    }
    return packet_raw, canon(receipt)


def verify_gap(
    request_raw, materializer_source_raw, materializer_catalog_raw,
    materializer_diff_raw, materializer_receipt_raw, packet_raw, receipt_raw,
    materializer_previous_raw=None,
):
    expected_packet, expected_receipt = compile_gap(
        request_raw, materializer_source_raw, materializer_catalog_raw,
        materializer_diff_raw, materializer_receipt_raw, materializer_previous_raw,
    )
    if packet_raw != expected_packet:
        raise Error("packet mismatch")
    if receipt_raw != expected_receipt:
        raise Error("receipt mismatch")
    return {
        "verified": True,
        "packet_sha256": digest(packet_raw),
        "receipt_sha256": digest(receipt_raw),
    }


def _read(path, label):
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise Error(f"{label}: read failed") from exc


def _publish(out: Path, files):
    try:
        out.mkdir(mode=0o700, parents=False, exist_ok=False)
    except OSError as exc:
        raise Error("output directory must not already exist") from exc
    made = []
    try:
        for name, data in files:
            path = out / name
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(data); fh.flush(); os.fsync(fh.fileno())
            made.append(path)
    except OSError as exc:
        for path in reversed(made):
            try:
                path.unlink()
            except OSError:
                pass
        try:
            out.rmdir()
        except OSError:
            pass
        raise Error("publication failed") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile pursuit qualification gaps into internal partner capability needs")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("compile", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--request", required=True)
        p.add_argument("--materializer-source", required=True)
        p.add_argument("--materializer-catalog", required=True)
        p.add_argument("--materializer-diff", required=True)
        p.add_argument("--materializer-receipt", required=True)
        p.add_argument("--materializer-previous")
        if name == "compile":
            p.add_argument("--out-dir", required=True)
        else:
            p.add_argument("--packet", required=True)
            p.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    try:
        common = (
            _read(args.request, "request"),
            _read(args.materializer_source, "materializer source"),
            _read(args.materializer_catalog, "materializer catalog"),
            _read(args.materializer_diff, "materializer diff"),
            _read(args.materializer_receipt, "materializer receipt"),
        )
        previous = _read(args.materializer_previous, "materializer previous") if args.materializer_previous else None
        if args.command == "compile":
            packet, receipt = compile_gap(*common, previous)
            _publish(Path(args.out_dir), (("gap_packet.json", packet), ("gap_receipt.json", receipt)))
            print(json.dumps({
                "live_materialization_status": json.loads(packet)["live_materialization_status"],
                "packet_sha256": digest(packet),
            }, sort_keys=True))
        else:
            result = verify_gap(*common, _read(args.packet, "packet"), _read(args.receipt, "receipt"), previous)
            print(json.dumps(result, sort_keys=True))
        return 0
    except (Error, materializer.Error) as exc:
        print(f"pursuit-gap error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
