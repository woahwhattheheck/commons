#!/usr/bin/env python3
"""Hamilton County 065-26/JW source-bound pursuit recovery compiler.

The retained authority currently proves only that the controlling County packet
has NOT been captured. Secondary discovery may drive a recovery work order, but
it can never mint PRIME/TEAMING readiness or buyer-mandatory requirements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "tjlabs.hamilton-06526jw-pursuit/v1"
OWNER_SCHEMA = "tjlabs.hamilton-06526jw-owner-evidence/v1"
AUTHORITY_SCHEMA = "tjlabs.hamilton-06526jw-retained-authority/v1"
EXPECTED_AUTHORITY_SHA256 = "2850f15a9e36f6759992fd2edc77779b9425a42613888c21a08245bcc3868a52"
MAX_INPUT_BYTES = 512_000
MAX_OUTPUT_BYTES = 2_000_000
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_CAPABILITIES = (
    "api_integration",
    "event_driven_integration",
    "data_mapping_validation",
    "observability_evidence",
    "migration_cutover",
    "security_compliance_delivery",
    "justice_niem_delivery",
    "regulated_environment_references",
)
AUTHORITY_FLAGS = (
    "county_contact",
    "partner_contact",
    "portal_registration",
    "proposal_submission",
    "pricing_commitment",
    "signature_or_certification",
    "award_claim",
    "payment_or_revenue_claim",
)


class PursuitError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _strict_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise PursuitError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def parse_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    if len(data) > MAX_INPUT_BYTES:
        raise PursuitError(f"{label} exceeds {MAX_INPUT_BYTES} bytes")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                PursuitError(f"{label} non-finite number: {token}")
            ),
        )
    except PursuitError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PursuitError(f"{label} must be strict UTF-8 JSON: {exc}") from exc
    if type(value) is not dict:
        raise PursuitError(f"{label} must be a JSON object")
    return value


def _read_regular(path: Path, label: str) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            raise PursuitError(f"{label} must be a non-symlink regular file")
        before = path.stat()
        if before.st_size > MAX_INPUT_BYTES:
            raise PursuitError(f"{label} exceeds {MAX_INPUT_BYTES} bytes")
        data = path.read_bytes()
        after = path.stat()
    except PursuitError:
        raise
    except OSError as exc:
        raise PursuitError(f"cannot read {label}: {exc}") from exc
    generation = lambda st: (
        st.st_dev,
        st.st_ino,
        st.st_mode,
        st.st_size,
        st.st_mtime_ns,
        st.st_ctime_ns,
    )
    if generation(before) != generation(after) or len(data) != after.st_size:
        raise PursuitError(f"{label} changed while being read")
    return data


def _utc(value: Any, label: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise PursuitError(f"{label} must be canonical UTC seconds")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise PursuitError(f"{label} must be canonical UTC seconds") from exc
    return parsed


def _safe_id(value: Any, label: str) -> str:
    if type(value) is not str or not SAFE_ID.fullmatch(value):
        raise PursuitError(f"{label} must be a safe opaque identifier")
    if "@" in value or "/" in value or "\\" in value:
        raise PursuitError(f"{label} must not contain contact/path material")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or not HEX64.fullmatch(value):
        raise PursuitError(f"{label} must be lowercase sha256")
    return value


def load_retained_authority(path: Path | None = None) -> dict[str, Any]:
    source = path or Path(__file__).with_name("retained_authority.json")
    data = _read_regular(source, "retained authority")
    actual = hashlib.sha256(data).hexdigest()
    if actual != EXPECTED_AUTHORITY_SHA256:
        raise PursuitError("retained authority root mismatch")
    value = parse_json_bytes(data, "retained authority")
    required = {
        "schema",
        "opportunity_id",
        "buyer",
        "solicitation_id",
        "title",
        "controlling_packet_status",
        "official_portal",
        "secondary_observation",
        "authority_ceiling",
    }
    if set(value) != required:
        raise PursuitError("retained authority keys drift")
    if value["schema"] != AUTHORITY_SCHEMA:
        raise PursuitError("retained authority schema drift")
    if (
        value["opportunity_id"] != "HAMILTON-OH-065-26-JW"
        or value["solicitation_id"] != "065-26/JW"
    ):
        raise PursuitError("retained opportunity identity drift")
    if value["controlling_packet_status"] != "NOT_CAPTURED":
        raise PursuitError("v1 retained authority must remain NOT_CAPTURED")
    portal = value["official_portal"]
    if type(portal) is not dict or set(portal) != {
        "url",
        "source_class",
        "packet_sha256",
        "addenda_complete",
        "captured_at_utc",
    }:
        raise PursuitError("official portal descriptor drift")
    if (
        portal["url"] != "https://hamiltoncountyohio.gob2g.com/"
        or portal["source_class"] != "OFFICIAL_PORTAL_POINTER"
    ):
        raise PursuitError("official portal identity drift")
    if (
        portal["packet_sha256"] is not None
        or portal["captured_at_utc"] is not None
        or portal["addenda_complete"] is not False
    ):
        raise PursuitError("uncaptured official packet cannot carry packet authority")
    secondary = value["secondary_observation"]
    if (
        type(secondary) is not dict
        or secondary.get("source_class") != "SECONDARY_DISCOVERY_ONLY"
    ):
        raise PursuitError("secondary observation authority drift")
    _utc(
        secondary.get("observed_at_utc"),
        "secondary_observation.observed_at_utc",
    )
    facts = secondary.get("facts")
    if (
        type(facts) is not list
        or not facts
        or any(type(item) is not str or not item for item in facts)
    ):
        raise PursuitError("secondary discovery facts invalid")
    ceiling = value["authority_ceiling"]
    if type(ceiling) is not dict or tuple(sorted(ceiling)) != tuple(
        sorted(AUTHORITY_FLAGS)
    ):
        raise PursuitError("authority ceiling keys drift")
    if any(ceiling[name] is not False for name in AUTHORITY_FLAGS):
        raise PursuitError("retained authority ceiling must deny external mutations")
    return value


def normalize_owner_evidence(
    raw: Mapping[str, Any] | None, *, as_of: str
) -> dict[str, Any]:
    if raw is None:
        return {
            "schema": OWNER_SCHEMA,
            "organization_ref": "owner-evidence-not-supplied",
            "capabilities": [],
            "partner": {
                "state": "NONE",
                "partner_ref": None,
                "evidence_sha256": None,
            },
        }
    if type(raw) is not dict:
        raise PursuitError("owner evidence must be an object")
    expected = {"schema", "organization_ref", "capabilities", "partner"}
    if set(raw) != expected or raw["schema"] != OWNER_SCHEMA:
        raise PursuitError("owner evidence schema/keys drift")
    organization_ref = _safe_id(raw["organization_ref"], "organization_ref")
    capabilities = raw["capabilities"]
    if type(capabilities) is not list or len(capabilities) > len(ALLOWED_CAPABILITIES):
        raise PursuitError("capabilities must be a bounded list")
    normalized = []
    seen = set()
    for index, item in enumerate(capabilities):
        if type(item) is not dict or set(item) != {
            "capability_id",
            "state",
            "evidence_sha256",
            "observed_at_utc",
        }:
            raise PursuitError(f"capabilities[{index}] keys drift")
        capability_id = item["capability_id"]
        if capability_id not in ALLOWED_CAPABILITIES:
            raise PursuitError(f"capabilities[{index}].capability_id unsupported")
        if capability_id in seen:
            raise PursuitError(f"duplicate capability_id: {capability_id}")
        seen.add(capability_id)
        state = item["state"]
        if state not in {"PROVEN", "GAP", "UNKNOWN"}:
            raise PursuitError(f"capabilities[{index}].state unsupported")
        evidence_sha = item["evidence_sha256"]
        observed = item["observed_at_utc"]
        if state == "PROVEN":
            _sha(evidence_sha, f"capabilities[{index}].evidence_sha256")
            if _utc(
                observed, f"capabilities[{index}].observed_at_utc"
            ) > _utc(as_of, "as_of"):
                raise PursuitError(f"capabilities[{index}] is future evidence")
        elif evidence_sha is not None or observed is not None:
            raise PursuitError(
                f"capabilities[{index}] non-PROVEN state cannot carry evidence"
            )
        normalized.append(dict(item))
    normalized.sort(key=lambda row: row["capability_id"])

    partner = raw["partner"]
    if type(partner) is not dict or set(partner) != {
        "state",
        "partner_ref",
        "evidence_sha256",
    }:
        raise PursuitError("partner keys drift")
    state = partner["state"]
    if state not in {"NONE", "IDENTIFIED_NOT_COMMITTED", "COMMITTED"}:
        raise PursuitError("partner.state unsupported")
    if state == "NONE":
        if partner["partner_ref"] is not None or partner["evidence_sha256"] is not None:
            raise PursuitError("NONE partner cannot carry identity/evidence")
    else:
        _safe_id(partner["partner_ref"], "partner.partner_ref")
        if state == "COMMITTED":
            _sha(partner["evidence_sha256"], "partner.evidence_sha256")
        elif partner["evidence_sha256"] is not None:
            raise PursuitError(
                "uncommitted partner cannot carry commitment evidence"
            )
    return {
        "schema": OWNER_SCHEMA,
        "organization_ref": organization_ref,
        "capabilities": normalized,
        "partner": dict(partner),
    }


def _provisional_matrix(
    authority: Mapping[str, Any], owner: Mapping[str, Any]
) -> list[dict[str, Any]]:
    del authority
    proven = {
        row["capability_id"]
        for row in owner["capabilities"]
        if row["state"] == "PROVEN"
    }
    rows = [
        ("source_complete", "controlling solicitation + addenda", None),
        ("teaming_rules", "prime/subcontract/team participation rules", None),
        ("evaluation", "evaluation factors and scoring", None),
        (
            "submission",
            "proposal forms, certifications, format and submission mechanics",
            None,
        ),
        ("pricing", "buyer pricing workbook/unit structure", None),
        ("insurance", "buyer insurance and legal conditions", None),
        (
            "api",
            "API-first synchronous/asynchronous integration",
            "api_integration",
        ),
        (
            "events",
            "event-driven real-time integration",
            "event_driven_integration",
        ),
        (
            "mapping",
            "message translation, mapping and validation",
            "data_mapping_validation",
        ),
        (
            "observability",
            "logging, monitoring, alerting and evidence",
            "observability_evidence",
        ),
        (
            "cutover",
            "legacy migration/cutover and resilience",
            "migration_cutover",
        ),
        (
            "security",
            "CJIS/FedRAMP/security obligations",
            "security_compliance_delivery",
        ),
        ("niem", "NIEM integration expectations", "justice_niem_delivery"),
        (
            "references",
            "similar justice/regulated-environment references",
            "regulated_environment_references",
        ),
    ]
    result = []
    for gate_id, description, capability_id in rows:
        result.append(
            {
                "gate_id": gate_id,
                "description": description,
                "buyer_authority": "UNVERIFIED_CONTROLLING_PACKET_MISSING",
                "owner_evidence": (
                    "PROVEN_SPECIALIST_EVIDENCE_ONLY"
                    if capability_id in proven
                    else "NOT_PROVEN"
                ),
                "capability_id": capability_id,
                "route_effect": "CANNOT_SCORE_OR_CLEAR",
            }
        )
    return result


def compile_pursuit(
    owner_evidence: Mapping[str, Any] | None,
    *,
    as_of: str,
    authority_path: Path | None = None,
) -> dict[str, Any]:
    now = _utc(as_of, "as_of")
    authority = load_retained_authority(authority_path)
    observed = _utc(
        authority["secondary_observation"]["observed_at_utc"],
        "secondary observed_at",
    )
    if now < observed:
        raise PursuitError("as_of predates retained secondary observation")
    owner = normalize_owner_evidence(owner_evidence, as_of=as_of)
    matrix = _provisional_matrix(authority, owner)
    proven = [
        row["capability_id"]
        for row in owner["capabilities"]
        if row["state"] == "PROVEN"
    ]

    reasons = [
        "CONTROLLING_COUNTY_PACKET_NOT_CAPTURED",
        "ADDENDA_COMPLETENESS_UNPROVEN",
        "MANDATORY_REQUIREMENTS_UNVERIFIED",
        "TEAMING_RULES_UNVERIFIED",
        "EVALUATION_AND_SUBMISSION_MECHANICS_UNVERIFIED",
    ]
    if owner["partner"]["state"] != "COMMITTED":
        reasons.append("NO_EVIDENCE_BOUND_TEAMING_COMMITMENT")
    if "justice_niem_delivery" not in proven:
        reasons.append("NIEM_DELIVERY_NOT_PROVEN")
    if "security_compliance_delivery" not in proven:
        reasons.append("CJIS_FEDRAMP_DELIVERY_NOT_PROVEN")
    if "regulated_environment_references" not in proven:
        reasons.append("REGULATED_JUSTICE_REFERENCES_NOT_PROVEN")

    receipt = {
        "schema": SCHEMA,
        "opportunity": {
            "opportunity_id": authority["opportunity_id"],
            "buyer": authority["buyer"],
            "solicitation_id": authority["solicitation_id"],
            "title": authority["title"],
        },
        "evaluated_at_utc": as_of,
        "retained_authority_sha256": EXPECTED_AUTHORITY_SHA256,
        "source_state": {
            "controlling_packet_status": authority["controlling_packet_status"],
            "official_portal": authority["official_portal"],
            "secondary_observation": authority["secondary_observation"],
            "secondary_facts_are_buyer_requirements": False,
        },
        "owner_evidence_digest": digest(owner),
        "owner_evidence_summary": {
            "organization_ref": owner["organization_ref"],
            "proven_specialist_capabilities": proven,
            "partner_state": owner["partner"]["state"],
        },
        "disposition": "HOLD_CONTROLLING_PACKET",
        "reasons": sorted(set(reasons)),
        "requirement_matrix": matrix,
        "teaming_posture": {
            "state": "DISCOVERY_ONLY_NOT_PARTNER_READY",
            "prime_profile": [
                "evidence-backed justice or similarly regulated integration prime",
                "buyer-acceptable NIEM delivery history if confirmed controlling requirement",
                "buyer-acceptable CJIS and FedRAMP High delivery posture if confirmed",
                "buyer-acceptable insurance and public-sector references if confirmed",
            ],
            "bounded_specialist_workshare_candidates": [
                "integration adapter and contract testing",
                "data validation and transformation regression",
                "event replay/idempotency/resilience evidence",
                "observability and claim-to-test evidence packs",
                "migration/cutover verification",
            ],
            "partner_contact_authorized": False,
        },
        "next_work_order": [
            "capture the complete controlling County RFP packet from the official procurement portal",
            "capture every current addendum, form, pricing workbook and buyer Q&A/pre-proposal artifact",
            "hash and retain the complete official source generation before extracting mandatory gates",
            "verify proposal/question deadlines, teaming/subcontract rules, evaluation formula and submission mechanics from buyer-controlled sources",
            "extract exact NIEM, CJIS, FedRAMP, reference, insurance, SBE and implementation requirements without promoting secondary summaries",
            "map actual owner and candidate-prime evidence to the exact official gate set",
            "only after source and teaming rules are bound, identify a prime and request Muse single-writer arbitration before any outreach",
        ],
        "authority": dict(authority["authority_ceiling"]),
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(
    receipt: Mapping[str, Any],
    owner_evidence: Mapping[str, Any] | None,
    *,
    as_of: str,
    authority_path: Path | None = None,
) -> bool:
    if type(receipt) is not dict:
        raise PursuitError("receipt must be an object")
    supplied = receipt.get("receipt_sha256")
    if type(supplied) is not str or not HEX64.fullmatch(supplied):
        raise PursuitError("receipt_sha256 missing/invalid")
    without = dict(receipt)
    without.pop("receipt_sha256", None)
    if digest(without) != supplied:
        raise PursuitError("receipt digest mismatch")
    rebuilt = compile_pursuit(
        owner_evidence, as_of=as_of, authority_path=authority_path
    )
    if canonical_bytes(rebuilt) != canonical_bytes(receipt):
        raise PursuitError("receipt does not match exact current inputs")
    return True


def render_markdown(receipt: Mapping[str, Any]) -> str:
    if receipt.get("disposition") != "HOLD_CONTROLLING_PACKET":
        raise PursuitError("v1 renderer only supports current HOLD posture")
    lines = [
        "# Hamilton County 065-26/JW — pursuit recovery",
        "",
        f"**Disposition:** `{receipt['disposition']}`  ",
        f"**Receipt:** `{receipt['receipt_sha256']}`  ",
        "**External action authority:** none",
        "",
        "## Why this is HOLD",
    ]
    lines.extend(f"- {reason}" for reason in receipt["reasons"])
    lines += [
        "",
        "## Provisional matrix",
        "",
        "| Gate | Buyer authority | Owner evidence |",
        "|---|---|---|",
    ]
    for row in receipt["requirement_matrix"]:
        lines.append(
            f"| `{row['gate_id']}` | {row['buyer_authority']} | {row['owner_evidence']} |"
        )
    lines += ["", "## Next work order"]
    lines.extend(
        f"{i}. {item}" for i, item in enumerate(receipt["next_work_order"], 1)
    )
    lines += [
        "",
        "## Truth boundary",
        "",
        "Secondary discovery is not promoted to a County mandate. This artifact performs no County/partner contact, portal registration, pricing, certification, signature, proposal submission, award/payment claim, or revenue recognition.",
        "",
    ]
    return "\n".join(lines)


def _write_exclusive(path: Path, data: bytes) -> None:
    if len(data) > MAX_OUTPUT_BYTES:
        raise PursuitError("output exceeds safety bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise PursuitError(f"output unavailable for exclusive create: {exc}") from exc
    success = False
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise PursuitError("short output write")
            view = view[written:]
        os.fsync(fd)
        success = True
    finally:
        os.close(fd)
        if not success:
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compile_cmd = sub.add_parser("compile")
    compile_cmd.add_argument("--as-of", required=True)
    compile_cmd.add_argument("--owner-evidence", type=Path)
    compile_cmd.add_argument("--json-out", type=Path)
    compile_cmd.add_argument("--markdown-out", type=Path)
    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("receipt_json", type=Path)
    verify_cmd.add_argument("--as-of", required=True)
    verify_cmd.add_argument("--owner-evidence", type=Path)
    args = parser.parse_args(argv)
    try:
        owner = None
        if args.owner_evidence:
            owner = parse_json_bytes(
                _read_regular(args.owner_evidence, "owner evidence"),
                "owner evidence",
            )
        if args.command == "compile":
            receipt = compile_pursuit(owner, as_of=args.as_of)
            json_bytes = canonical_bytes(receipt)
            md_bytes = render_markdown(receipt).encode("utf-8")
            outputs = [
                path
                for path in (args.json_out, args.markdown_out)
                if path is not None
            ]
            if any(path.exists() or path.is_symlink() for path in outputs):
                raise PursuitError(
                    "compile output path already exists; refusing partial/state-mixed publication"
                )
            created: list[Path] = []
            try:
                if args.json_out:
                    _write_exclusive(args.json_out, json_bytes)
                    created.append(args.json_out)
                else:
                    print(json_bytes.decode("utf-8"), end="")
                if args.markdown_out:
                    _write_exclusive(args.markdown_out, md_bytes)
                    created.append(args.markdown_out)
            except Exception:
                for path in created:
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                raise
            return 0
        receipt = parse_json_bytes(
            _read_regular(args.receipt_json, "receipt"), "receipt"
        )
        verify_receipt(receipt, owner, as_of=args.as_of)
        print("VERIFIED")
        return 0
    except PursuitError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
