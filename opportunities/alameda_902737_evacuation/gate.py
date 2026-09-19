"""Fail-closed evidence classifier for Alameda County RFP 902737.

The production surface is deliberately source-HOLD until exact buyer evidence is
retained and compiled into trusted roots. Replay helpers are non-production and
can never emit the production terminal state.
"""
from __future__ import annotations

from copy import deepcopy as _deepcopy_import
from datetime import datetime as _datetime_import, timezone as _timezone_import
from hashlib import sha256 as _sha256_import
import json as _json_import
import re as _re_import

OPPORTUNITY_ID = "ALAMEDA-902737"
EXPECTED_DEADLINE = "2026-10-13T14:00:00-07:00"
_SCHEMA = "alameda-902737-qualification/v2"
_PRODUCTION_READY = "QUALIFIED_FOR_INTERNAL_NEXT_EDGE"
_REPLAY_READY = "QUALIFIED_REPLAY_ONLY"

OFFICIAL_ROOTS = {}
PRIME_ROOTS = {}
LOCAL_ROOTS = {}
WORKSHARE_ROOTS = {}


class GateError(ValueError):
    pass


def _make_runtime_generation():
    """Capture strict parsing, canonicalization, digest, and process clock once."""
    deepcopy_fn = _deepcopy_import
    dumps_fn = _json_import.dumps
    sha256_fn = _sha256_import
    id_re = _re_import.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    hex_re = _re_import.compile(r"^[0-9a-f]{64}$")
    datetime_cls = _datetime_import
    timezone_obj = _timezone_import
    max_bytes = 256_000
    max_rows = 128

    def strict_id(value, name):
        if type(value) is not str or not id_re.fullmatch(value):
            raise GateError(f"{name}: invalid")
        return value

    def strict_sha(value, name):
        if type(value) is not str or not hex_re.fullmatch(value):
            raise GateError(f"{name}: invalid")
        return value

    def canonical_bytes(value):
        try:
            raw = dumps_fn(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise GateError("non-canonical input") from exc
        if len(raw) > max_bytes:
            raise GateError("input too large")
        return raw

    def digest(value):
        return sha256_fn(canonical_bytes(value)).hexdigest()

    def normalize_roots(value, label):
        if type(value) is not dict:
            raise GateError(f"{label}: roots must be dict")
        out = {}
        for digest0, descriptor0 in value.items():
            digest1 = strict_sha(digest0, f"{label}.sha")
            if type(descriptor0) not in (tuple, list) or len(descriptor0) != 5:
                raise GateError(f"{label}: descriptor must have five fields")
            kind, subject, gate, claim_value, generation = descriptor0
            descriptor = (
                strict_id(kind, f"{label}.kind"),
                strict_id(subject, f"{label}.subject"),
                strict_id(gate, f"{label}.gate"),
                strict_id(claim_value, f"{label}.value"),
                strict_id(generation, f"{label}.generation"),
            )
            out[digest1] = descriptor
        return out

    def normalize_rows(packet):
        rows0 = packet.get("evidence")
        if type(rows0) is not list or len(rows0) > max_rows:
            raise GateError("evidence must be a bounded list")
        rows = []
        seen = set()
        for i, row0 in enumerate(rows0):
            if type(row0) is not dict:
                raise GateError(f"evidence[{i}] must be object")
            row = {
                "source_id": strict_id(row0.get("source_id"), f"evidence[{i}].source_id"),
                "sha256": strict_sha(row0.get("sha256"), f"evidence[{i}].sha256"),
                "kind": strict_id(row0.get("kind"), f"evidence[{i}].kind"),
                "subject": strict_id(row0.get("subject"), f"evidence[{i}].subject"),
                "gate": strict_id(row0.get("gate"), f"evidence[{i}].gate"),
                "value": strict_id(row0.get("value"), f"evidence[{i}].value"),
                "generation": strict_id(row0.get("generation"), f"evidence[{i}].generation"),
            }
            identity = (row["source_id"], row["sha256"])
            if identity in seen:
                raise GateError("duplicate evidence identity")
            seen.add(identity)
            rows.append(row)
        return tuple(rows)

    def trusted_claim(rows, roots, kind, subject, gate):
        matches = [
            row for row in rows
            if (row["kind"], row["subject"], row["gate"]) == (kind, subject, gate)
        ]
        if not matches:
            return None
        admitted = []
        for row in matches:
            descriptor = (
                row["kind"], row["subject"], row["gate"],
                row["value"], row["generation"],
            )
            if roots.get(row["sha256"]) != descriptor:
                return None
            admitted.append((row["value"], row["generation"]))
        unique = set(admitted)
        if len(unique) != 1:
            return None
        return admitted[0]

    def process_now():
        return datetime_cls.now(timezone_obj.utc)

    return (
        deepcopy_fn,
        canonical_bytes,
        digest,
        normalize_roots,
        normalize_rows,
        trusted_claim,
        process_now,
        datetime_cls,
        timezone_obj,
    )


_RUNTIME = _make_runtime_generation()


def _make_classifier(*, official_roots, prime_roots, local_roots, workshare_roots,
                     clock, terminal_state):
    (
        deepcopy_fn,
        _canonical_bytes_fn,
        digest_fn,
        normalize_roots_fn,
        normalize_rows_fn,
        trusted_claim_fn,
        _process_now_fn,
        datetime_cls,
        _timezone_obj,
    ) = _RUNTIME
    official = normalize_roots_fn(dict(official_roots), "official")
    prime = normalize_roots_fn(dict(prime_roots), "prime")
    local = normalize_roots_fn(dict(local_roots), "local")
    workshare = normalize_roots_fn(dict(workshare_roots), "workshare")
    clock_fn = clock
    expected_deadline = EXPECTED_DEADLINE
    opportunity_id = OPPORTUNITY_ID
    schema = _SCHEMA
    workshare_roots_local = workshare

    def classify_impl(packet0):
        if type(packet0) is not dict:
            raise GateError("packet must be object")
        packet = deepcopy_fn(packet0)
        if packet.get("opportunity_id") != opportunity_id:
            raise GateError("wrong opportunity")
        rows = normalize_rows_fn(packet)

        buyer_packet = trusted_claim_fn(
            rows, official, "OFFICIAL_PACKET", "alameda-county", "buyer_packet"
        )
        if buyer_packet is None:
            state = "HOLD_MISSING_OFFICIAL_PACKET"
        else:
            addenda = trusted_claim_fn(
                rows, official, "OFFICIAL_ADDENDA_INDEX", "alameda-county", "addenda_generation"
            )
            if addenda is None:
                state = "HOLD_ADDENDA_UNBOUND"
            else:
                deadline_claim = trusted_claim_fn(
                    rows, official, "OFFICIAL_CLAIM", "alameda-county", "deadline"
                )
                teaming_claim = trusted_claim_fn(
                    rows, official, "OFFICIAL_CLAIM", "alameda-county", "teaming"
                )
                local_claim = trusted_claim_fn(
                    rows, official, "OFFICIAL_CLAIM", "alameda-county", "local_participation"
                )
                claims = (deadline_claim, teaming_claim, local_claim)
                if any(claim is None for claim in claims):
                    state = "HOLD_BUYER_CLAIMS_UNBOUND"
                else:
                    packet_generation = buyer_packet[1]
                    controlling_generations = {
                        packet_generation,
                        addenda[1],
                        deadline_claim[1],
                        teaming_claim[1],
                        local_claim[1],
                    }
                    if len(controlling_generations) != 1:
                        state = "HOLD_SOURCE_GENERATION_MISMATCH"
                    elif deadline_claim[0] != "DUE_2026_10_13_1400_PT":
                        state = "HOLD_DEADLINE_CLAIM_UNKNOWN"
                    elif teaming_claim[0] == "PROHIBITED":
                        state = "NO_PARTNER_ROUTE"
                    elif teaming_claim[0] != "PERMITTED":
                        state = "HOLD_TEAMING_UNKNOWN"
                    elif local_claim[0] not in ("REQUIRED", "NOT_REQUIRED"):
                        state = "HOLD_LOCAL_PARTICIPATION_UNKNOWN"
                    else:
                        current = clock_fn()
                        if not isinstance(current, datetime_cls) or current.tzinfo is None:
                            raise GateError("clock returned invalid datetime")
                        if current >= datetime_cls.fromisoformat(expected_deadline):
                            state = "NO_BID_DEADLINE_CLOSED"
                        else:
                            prime_obj = packet.get("prime")
                            if type(prime_obj) is not dict:
                                raise GateError("prime must be object")
                            org = prime_obj.get("org_id")
                            if type(org) is not str:
                                raise GateError("prime.org_id invalid")
                            required = (
                                "platform",
                                "three_similar_jurisdictions",
                                "insurance",
                                "security_accessibility",
                                "support_24x7",
                            )
                            prime_claims = [
                                trusted_claim_fn(rows, prime, "PRIME_EVIDENCE", org, gate)
                                for gate in required
                            ]
                            if any(claim is None or claim[0] != "VERIFIED" for claim in prime_claims):
                                state = "HOLD_PRIME_EVIDENCE"
                            elif len({claim[1] for claim in prime_claims}) != 1:
                                state = "HOLD_PRIME_GENERATION_MISMATCH"
                            elif local_claim[0] == "REQUIRED":
                                local_evidence = trusted_claim_fn(
                                    rows, local, "LOCAL_PARTICIPATION_EVIDENCE", org,
                                    "local_participation"
                                )
                                if local_evidence is None or local_evidence[0] != "VERIFIED":
                                    state = "HOLD_LOCAL_PARTICIPATION_EVIDENCE"
                                else:
                                    workshare_claim = trusted_claim_fn(
                                        rows, workshare_roots_local,
                                        "INTERNAL_WORKSHARE_EVIDENCE", org, "paid_tjlabs_seam"
                                    )
                                    state = (
                                        terminal_state
                                        if workshare_claim is not None and workshare_claim[0] == "DEFINED"
                                        else "HOLD_PAID_WORKSHARE_UNBOUND"
                                    )
                            else:
                                workshare_claim = trusted_claim_fn(
                                    rows, workshare_roots_local,
                                    "INTERNAL_WORKSHARE_EVIDENCE", org, "paid_tjlabs_seam"
                                )
                                state = (
                                    terminal_state
                                    if workshare_claim is not None and workshare_claim[0] == "DEFINED"
                                    else "HOLD_PAID_WORKSHARE_UNBOUND"
                                )

        semantic = {
            "opportunity_id": opportunity_id,
            "state": state,
            "deadline": expected_deadline,
            "external_authority": False,
            "evidence_generation_sha256": digest_fn(list(rows)),
        }
        return {
            "schema": schema,
            "semantic": semantic,
            "receipt_sha256": digest_fn(semantic),
        }

    return classify_impl


def _make_production_surfaces():
    (
        _deepcopy_fn,
        _canonical_bytes_fn,
        digest_fn,
        _normalize_roots_fn,
        _normalize_rows_fn,
        _trusted_claim_fn,
        process_now_fn,
        _datetime_cls,
        _timezone_obj,
    ) = _RUNTIME
    production_classifier = _make_classifier(
        official_roots=OFFICIAL_ROOTS,
        prime_roots=PRIME_ROOTS,
        local_roots=LOCAL_ROOTS,
        workshare_roots=WORKSHARE_ROOTS,
        clock=process_now_fn,
        terminal_state=_PRODUCTION_READY,
    )

    def classify_public(packet0):
        return production_classifier(packet0)

    def production_state_public():
        return production_classifier({
            "opportunity_id": OPPORTUNITY_ID,
            "prime": {"org_id": "unselected-prime"},
            "evidence": [],
        })

    def verify_receipt_public(receipt0):
        if type(receipt0) is not dict:
            return False
        try:
            receipt = _deepcopy_fn(receipt0)
            if receipt.get("schema") != _SCHEMA:
                return False
            semantic = receipt.get("semantic")
            if type(semantic) is not dict:
                return False
            if semantic.get("opportunity_id") != OPPORTUNITY_ID:
                return False
            if semantic.get("external_authority") is not False:
                return False
            return receipt.get("receipt_sha256") == digest_fn(semantic)
        except (GateError, TypeError, ValueError):
            return False

    return classify_public, production_state_public, verify_receipt_public


classify, production_state, verify_receipt = _make_production_surfaces()


def build_replay_classifier(*, official_roots, prime_roots, local_roots,
                            workshare_roots, now):
    """NON-PRODUCTION deterministic replay helper; never emits production READY."""
    (
        _deepcopy_fn,
        _canonical_bytes_fn,
        _digest_fn,
        _normalize_roots_fn,
        _normalize_rows_fn,
        _trusted_claim_fn,
        _process_now_fn,
        datetime_cls,
        _timezone_obj,
    ) = _RUNTIME
    if not isinstance(now, datetime_cls) or now.tzinfo is None:
        raise GateError("replay now must be offset-aware")
    frozen_now = now

    def replay_clock():
        return frozen_now

    return _make_classifier(
        official_roots=official_roots,
        prime_roots=prime_roots,
        local_roots=local_roots,
        workshare_roots=workshare_roots,
        clock=replay_clock,
        terminal_state=_REPLAY_READY,
    )
