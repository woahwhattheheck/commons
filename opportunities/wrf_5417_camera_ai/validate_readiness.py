#!/usr/bin/env python3
"""Fail-closed WRF 5417 readiness compiler. Offline/internal only."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import sys
from zoneinfo import ZoneInfo

READY = "READY_FOR_AUTHORIZED_SUBMITTER_REVIEW"
HOLD = "HOLD"
SCHEMA_VERSION = 2
AUTHORITY_SCHEMA_VERSION = 1
MAX_FILE_BYTES = 262_144
MAX_INT_DIGITS = 18
MAX_FUTURE_SKEW_SECONDS = 300

OPPORTUNITY_ID = "WRF-5417"
DEADLINE_LOCAL = "2026-09-14T15:00:00"
DEADLINE_ZONE = "America/Denver"
WRF_REQUEST_CEILING_CENTS = 30_000_000
MIN_CONTRIBUTION_NUM, MIN_CONTRIBUTION_DEN = 33, 100
MAX_INDIRECT_NUM, MAX_INDIRECT_DEN = 15, 100
MIN_DISTINCT_UTILITY_SITES = 2

REQUIRED_GATES = (
    "organization_my_portal_account",
    "applying_entity_identity",
    "w9_or_applicable_entity_tax_document",
    "financial_statements_packet",
    "financial_grant_management_capabilities_form",
    "certification_and_assurance_form",
    "pi_owner_eligibility",
    "pi_and_copi_identified",
    "current_and_pending_forms",
    "team_qualification_evidence",
    "consenting_multi_site_utility_participation",
    "water_wastewater_domain_lead",
    "computer_vision_lead",
    "cost_share_commitments",
    "technical_proposal_components",
    "legal_ip_pfa_review",
    "final_pdf_and_portal_qa",
)
REQUIRED_BUDGET_ARTIFACTS = ("budget_workbook", "budget_narrative")
ALLOWED_SECTORS = {"drinking_water", "wastewater", "both"}

CONTRACT = {
    "schema_version": SCHEMA_VERSION,
    "opportunity_id": OPPORTUNITY_ID,
    "deadline_local": DEADLINE_LOCAL,
    "deadline_zone": DEADLINE_ZONE,
    "wrf_request_ceiling_cents": WRF_REQUEST_CEILING_CENTS,
    "minimum_contribution_fraction": [MIN_CONTRIBUTION_NUM, MIN_CONTRIBUTION_DEN],
    "indirect_reimbursement_ceiling_fraction": [MAX_INDIRECT_NUM, MAX_INDIRECT_DEN],
    "minimum_distinct_utility_sites": MIN_DISTINCT_UTILITY_SITES,
    "required_sectors": ["drinking_water", "wastewater"],
    "required_gates": list(REQUIRED_GATES),
    "required_budget_artifacts": list(REQUIRED_BUDGET_ARTIFACTS),
}


class ReadinessError(ValueError):
    pass


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


CONTRACT_DIGEST = digest(CONTRACT)


def _reject_constant(token):
    raise ReadinessError(f"non-finite number: {token}")


def _reject_float(token):
    raise ReadinessError(f"floats are not admitted: {token}")


def _parse_int(token):
    body = token[1:] if token.startswith("-") else token
    if len(body) > MAX_INT_DIGITS:
        raise ReadinessError("integer token too large")
    return int(token)


def _pairs_no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ReadinessError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json_bytes(raw):
    if len(raw) > MAX_FILE_BYTES:
        raise ReadinessError("JSON input exceeds byte limit")
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=_pairs_no_duplicates,
                          parse_constant=_reject_constant, parse_int=_parse_int,
                          parse_float=_reject_float)
    except ReadinessError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ReadinessError(f"invalid JSON: {exc}") from exc


def read_regular_file(path):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(os.fspath(path), flags)
    except OSError as exc:
        raise ReadinessError(f"cannot open retained file safely: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ReadinessError("retained input must be a regular file")
        if before.st_size > MAX_FILE_BYTES:
            raise ReadinessError("retained input exceeds byte limit")
        chunks, total = [], 0
        while True:
            part = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - total))
            if not part:
                break
            chunks.append(part)
            total += len(part)
            if total > MAX_FILE_BYTES:
                raise ReadinessError("retained input exceeds byte limit")
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ReadinessError("retained input changed while reading")
        return b"".join(chunks)
    finally:
        os.close(fd)


def load_strict_file(path):
    return strict_json_bytes(read_regular_file(path))


def exact_keys(obj, expected, label):
    if type(obj) is not dict:
        raise ReadinessError(f"{label} must be an object")
    got, want = set(obj), set(expected)
    if got != want:
        raise ReadinessError(f"{label} keys mismatch: missing={sorted(want-got)} extra={sorted(got-want)}")


def string(value, label, max_len=512):
    if type(value) is not str or not value or len(value) > max_len:
        raise ReadinessError(f"{label} must be a nonempty bounded string")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise ReadinessError(f"{label} contains lone surrogate")
    return value


def sha256_text(value, label):
    value = string(value, label, 64)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ReadinessError(f"{label} must be lowercase sha256")
    return value


def nonnegative_int(value, label):
    if type(value) is not int or value < 0:
        raise ReadinessError(f"{label} must be a nonnegative integer")
    return value


def parse_utc(value, label):
    value = string(value, label, 32)
    if not value.endswith("Z"):
        raise ReadinessError(f"{label} must be whole-second UTC")
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError as exc:
        raise ReadinessError(f"{label} must be whole-second UTC") from exc


def utc_text(value):
    if value.tzinfo is None:
        raise ReadinessError("verification clock must be timezone-aware")
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def deadline_utc():
    return dt.datetime.fromisoformat(DEADLINE_LOCAL).replace(tzinfo=ZoneInfo(DEADLINE_ZONE)).astimezone(dt.timezone.utc)


def gate_fact(gate, entry):
    exact_keys(entry, ("status", "subject"), f"hard_gates.{gate}")
    return {"kind":"GATE", "opportunity_id":OPPORTUNITY_ID, "gate":gate,
            "subject":string(entry["subject"], f"hard_gates.{gate}.subject"),
            "status":string(entry["status"], f"hard_gates.{gate}.status", 16)}


def artifact_fact(gate, entry):
    exact_keys(entry, ("status", "subject"), f"budget_artifacts.{gate}")
    return {"kind":"BUDGET_ARTIFACT", "opportunity_id":OPPORTUNITY_ID, "gate":gate,
            "subject":string(entry["subject"], f"budget_artifacts.{gate}.subject"),
            "status":string(entry["status"], f"budget_artifacts.{gate}.status", 16)}


def utility_fact(entry):
    exact_keys(entry, ("utility_id","site_id","role","sector","status"), "utility participant")
    sector = string(entry["sector"], "utility.sector", 32)
    if sector not in ALLOWED_SECTORS:
        raise ReadinessError("utility.sector invalid")
    return {"kind":"UTILITY_CONSENT", "opportunity_id":OPPORTUNITY_ID,
            "utility_id":string(entry["utility_id"], "utility.utility_id"),
            "site_id":string(entry["site_id"], "utility.site_id"),
            "role":string(entry["role"], "utility.role"), "sector":sector,
            "status":string(entry["status"], "utility.status", 16)}


def budget_fact(budget):
    keys = ("wrf_request_usd_cents","documented_eligible_contribution_usd_cents","direct_cost_base_usd_cents","reimbursed_indirect_usd_cents")
    exact_keys(budget, keys, "budget")
    return {"kind":"BUDGET", "opportunity_id":OPPORTUNITY_ID,
            **{k:nonnegative_int(budget[k], f"budget.{k}") for k in keys}}


def manifest_facts(manifest):
    exact_keys(manifest, ("schema_version","opportunity_id","owner","intended_submission_state","hard_gates","budget","budget_artifacts","utility_participants","submission_authority","notes"), "manifest")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise ReadinessError("manifest schema_version mismatch")
    if manifest["opportunity_id"] != OPPORTUNITY_ID:
        raise ReadinessError("wrong opportunity_id")
    string(manifest["owner"], "owner")
    if manifest["intended_submission_state"] not in {HOLD, READY}:
        raise ReadinessError("invalid intended_submission_state")
    gates = manifest["hard_gates"]
    if type(gates) is not dict or set(gates) != set(REQUIRED_GATES):
        raise ReadinessError("hard_gates must equal immutable required gate set")
    gate_facts = {g:gate_fact(g, gates[g]) for g in REQUIRED_GATES}
    artifacts = manifest["budget_artifacts"]
    if type(artifacts) is not dict or set(artifacts) != set(REQUIRED_BUDGET_ARTIFACTS):
        raise ReadinessError("budget_artifacts must equal immutable required artifact set")
    artifact_facts = {g:artifact_fact(g, artifacts[g]) for g in REQUIRED_BUDGET_ARTIFACTS}
    bfact = budget_fact(manifest["budget"])
    participants = manifest["utility_participants"]
    if type(participants) is not list or len(participants) > 64:
        raise ReadinessError("utility_participants must be a bounded array")
    ufacts = [utility_fact(p) for p in participants]
    auth = manifest["submission_authority"]
    exact_keys(auth, ("carrier_may_submit","authorized_submitter","final_submission_status"), "submission_authority")
    if auth != {"carrier_may_submit":False,"authorized_submitter":None,"final_submission_status":"NOT_AUTHORIZED"}:
        raise ReadinessError("repository carrier submission authority must remain hard false")
    if type(manifest["notes"]) is not list or not all(type(x) is str for x in manifest["notes"]):
        raise ReadinessError("notes must be an array of strings")
    return gate_facts, artifact_facts, bfact, ufacts


def authority_records(authority, now):
    exact_keys(authority, ("schema_version","opportunity_id","authority_generation","source_generation","records"), "authority")
    if authority["schema_version"] != AUTHORITY_SCHEMA_VERSION:
        raise ReadinessError("authority schema_version mismatch")
    if authority["opportunity_id"] != OPPORTUNITY_ID:
        raise ReadinessError("authority opportunity mismatch")
    generation = string(authority["authority_generation"], "authority_generation")
    source = authority["source_generation"]
    exact_keys(source, ("id","sha256","observed_at"), "source_generation")
    sid = string(source["id"], "source_generation.id")
    ssha = sha256_text(source["sha256"], "source_generation.sha256")
    observed = parse_utc(source["observed_at"], "source_generation.observed_at")
    if observed > now + dt.timedelta(seconds=MAX_FUTURE_SKEW_SECONDS):
        raise ReadinessError("authority source generation is from the future")
    records = authority["records"]
    if type(records) is not list or len(records) > 256:
        raise ReadinessError("authority.records must be a bounded array")
    by_id = {}
    semantic_identity = set()
    for i, record in enumerate(records):
        exact_keys(record, ("evidence_id","kind","gate","subject","opportunity_id","source_generation","source_sha256","verified_at","fact_sha256"), f"records[{i}]")
        eid = string(record["evidence_id"], f"records[{i}].evidence_id")
        if eid in by_id:
            raise ReadinessError("duplicate evidence_id")
        kind = string(record["kind"], f"records[{i}].kind", 32)
        gate = string(record["gate"], f"records[{i}].gate")
        subject = string(record["subject"], f"records[{i}].subject")
        if record["opportunity_id"] != OPPORTUNITY_ID:
            raise ReadinessError("cross-opportunity authority evidence")
        if record["source_generation"] != sid or record["source_sha256"] != ssha:
            raise ReadinessError("authority record source generation mismatch")
        verified = parse_utc(record["verified_at"], f"records[{i}].verified_at")
        if verified > now + dt.timedelta(seconds=MAX_FUTURE_SKEW_SECONDS):
            raise ReadinessError("authority evidence is from the future")
        fsha = sha256_text(record["fact_sha256"], f"records[{i}].fact_sha256")
        ident = (kind, gate, subject, record["opportunity_id"], fsha)
        if ident in semantic_identity:
            raise ReadinessError("duplicate retained evidence identity")
        semantic_identity.add(ident)
        by_id[eid] = record
    return generation, sid, ssha, by_id


def has_exact_record(records, kind, gate, subject, fact):
    target = digest(fact)
    matches = [r for r in records.values() if r["kind"] == kind and r["gate"] == gate and r["subject"] == subject and r["fact_sha256"] == target]
    return len(matches) == 1


def compile_readiness(manifest, authority, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ReadinessError("verification clock must be timezone-aware")
    now = now.astimezone(dt.timezone.utc).replace(microsecond=0)
    gate_facts, artifact_facts, bfact, ufacts = manifest_facts(manifest)
    generation, sid, ssha, records = authority_records(authority, now)
    reasons = []
    if manifest["intended_submission_state"] == HOLD:
        reasons.append("owner intent remains HOLD")
    due = deadline_utc()
    if now >= due:
        reasons.append("deadline expired")

    for gate, fact in gate_facts.items():
        if fact["status"] != "PROVEN":
            reasons.append(f"{gate}: {fact['status']}")
        elif not has_exact_record(records, "GATE", gate, fact["subject"], fact):
            reasons.append(f"{gate}: missing exact retained authority")
    for gate, fact in artifact_facts.items():
        if fact["status"] != "PROVEN":
            reasons.append(f"{gate}: {fact['status']}")
        elif not has_exact_record(records, "BUDGET_ARTIFACT", gate, fact["subject"], fact):
            reasons.append(f"{gate}: missing exact retained authority")

    request = bfact["wrf_request_usd_cents"]
    contribution = bfact["documented_eligible_contribution_usd_cents"]
    direct_base = bfact["direct_cost_base_usd_cents"]
    indirect = bfact["reimbursed_indirect_usd_cents"]
    if request <= 0 or request > WRF_REQUEST_CEILING_CENTS:
        reasons.append("WRF request amount outside immutable contract")
    if contribution * MIN_CONTRIBUTION_DEN < request * MIN_CONTRIBUTION_NUM:
        reasons.append("documented eligible contribution below immutable 33% floor")
    if indirect * MAX_INDIRECT_DEN > direct_base * MAX_INDIRECT_NUM:
        reasons.append("reimbursed indirect exceeds immutable 15% direct-cost-base ceiling")
    if not has_exact_record(records, "BUDGET", "budget", OPPORTUNITY_ID, bfact):
        reasons.append("budget: missing exact retained authority")

    sites, drinking, wastewater = set(), set(), set()
    for i, fact in enumerate(ufacts):
        subject = f"{fact['utility_id']}|{fact['site_id']}|{fact['role']}"
        if fact["status"] != "PROVEN":
            reasons.append(f"utility {i}: consent not proven")
            continue
        if not has_exact_record(records, "UTILITY_CONSENT", "utility_consent", subject, fact):
            reasons.append(f"utility {i}: missing exact retained consent authority")
            continue
        key = (fact["utility_id"], fact["site_id"])
        sites.add(key)
        if fact["sector"] in {"drinking_water", "both"}: drinking.add(key)
        if fact["sector"] in {"wastewater", "both"}: wastewater.add(key)
    if len(sites) < MIN_DISTINCT_UTILITY_SITES:
        reasons.append("fewer than two distinct consenting utility sites")
    if not drinking or not wastewater:
        reasons.append("consenting sites do not span drinking water and wastewater")

    state = READY if not reasons else HOLD
    if manifest["intended_submission_state"] == READY and reasons:
        reasons.insert(0, "READY spoofed while blockers remain")
    receipt = {
        "schema_version":SCHEMA_VERSION, "opportunity_id":OPPORTUNITY_ID,
        "contract_digest":CONTRACT_DIGEST, "candidate_digest":digest(manifest),
        "authority_digest":digest(authority), "authority_generation":generation,
        "source_generation":sid, "source_sha256":ssha,
        "evaluated_at":utc_text(now), "deadline_utc":utc_text(due),
        "state":state, "reasons":reasons,
        "authority":{"carrier_may_submit":False,"portal_mutation":False,"buyer_or_partner_contact":False,"award_payment_revenue":False},
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(receipt, manifest, authority, now=None):
    if type(receipt) is not dict or type(receipt.get("receipt_sha256")) is not str:
        return False, ["receipt digest missing"]
    body = dict(receipt); claimed = body.pop("receipt_sha256")
    if digest(body) != claimed:
        return False, ["receipt digest mismatch"]
    try:
        evaluated = parse_utc(receipt.get("evaluated_at"), "receipt.evaluated_at")
        if compile_readiness(manifest, authority, evaluated) != receipt:
            return False, ["receipt semantic mismatch"]
        current = compile_readiness(manifest, authority, now)
    except ReadinessError as exc:
        return False, [str(exc)]
    if current["state"] != receipt["state"] or current["reasons"] != receipt["reasons"]:
        return False, ["current readiness differs from retained receipt"]
    return True, []


def write_exclusive(path, raw):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(os.fspath(path), flags, 0o600)
    try:
        view = memoryview(raw)
        while view:
            n = os.write(fd, view)
            if n <= 0: raise OSError("short write")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("manifest")
    p.add_argument("authority")
    p.add_argument("--receipt-out")
    args = p.parse_args(argv)
    try:
        receipt = compile_readiness(load_strict_file(args.manifest), load_strict_file(args.authority))
        raw = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        if args.receipt_out: write_exclusive(args.receipt_out, raw)
        sys.stdout.buffer.write(raw)
        return 0 if receipt["state"] == READY else 3
    except (ReadinessError, OSError) as exc:
        print(json.dumps({"state":HOLD,"error":str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
