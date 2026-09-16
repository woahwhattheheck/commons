"""Non-authorizing teaming evidence carrier for Land Bank T12-09-26.

This module may hash bytes that are actually opened by this process and may
assemble a paid TJLabs workshare review packet. It deliberately cannot certify
that those bytes are buyer-authored, cannot qualify a prime, and cannot grant
submission authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
from typing import Any, Iterable, Mapping

SCHEMA = "tjlabs.land_bank_online_library_readiness.v2"
SOLICITATION = "T12-09-26"
BUYER = "Land and Agricultural Development Bank of South Africa"
CLOSING = "2026-10-08T11:00:00+02:00"

REQUIRED_PRIME_EVIDENCE = (
    "legal_library_platform_rights",
    "oem_osm_or_authorized_partner",
    "enterprise_reference_evidence",
    "cloud_hosting_capability",
    "uptime_and_disaster_recovery_capability",
    "security_and_encryption_capability",
    "independent_penetration_testing_capability",
    "south_africa_csd_registration",
    "sars_tax_compliance",
    "bbbee_evidence",
    "fica_kyc_evidence",
)

WORKSHARE_DELIVERABLES = (
    "content_migration_metadata_acceptance",
    "rbac_entitlement_acceptance",
    "search_retrieval_regression",
    "integration_data_contract_qa",
    "security_dr_evidence_matrix",
    "training_handover_acceptance",
    "requirements_traceability_pack",
)


class EvidenceError(ValueError):
    """A retained-file or evidence-shape check failed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _unique_strings(values: Iterable[object]) -> list[str]:
    return sorted({v.strip() for v in values if isinstance(v, str) and v.strip()})


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _hash_retained_regular_file(path_value: object, *, expected_sha256: object = "") -> dict[str, Any]:
    """Open one retained regular file and hash the bytes actually read.

    The returned receipt proves only that this process read a stable regular
    file generation. It does *not* prove buyer authorship or legal authority.
    A caller-supplied expected digest is only a constraining comparison; it is
    never used as the computed digest.
    """
    if not isinstance(path_value, (str, os.PathLike)):
        raise EvidenceError("candidate buyer source path is missing")
    path = os.fspath(path_value)
    if not path:
        raise EvidenceError("candidate buyer source path is empty")

    expected = expected_sha256.strip() if isinstance(expected_sha256, str) else ""
    if expected and not _valid_sha256(expected):
        raise EvidenceError("expected_sha256 must be empty or 64 lowercase hex characters")

    try:
        lst = os.lstat(path)
    except OSError as exc:
        raise EvidenceError("candidate buyer source is not readable") from exc
    if stat.S_ISLNK(lst.st_mode):
        raise EvidenceError("candidate buyer source must not be a symlink")
    if not stat.S_ISREG(lst.st_mode):
        raise EvidenceError("candidate buyer source must be a regular file")
    if lst.st_size > 67_108_864:
        raise EvidenceError("candidate buyer source exceeds 64 MiB")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK

    fd = -1
    try:
        fd = os.open(path, flags)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise EvidenceError("opened candidate source is not a regular file")
        if (before.st_dev, before.st_ino) != (lst.st_dev, lst.st_ino):
            raise EvidenceError("candidate source changed between lstat and open")
        if before.st_size > 67_108_864:
            raise EvidenceError("opened candidate source exceeds 64 MiB")

        digest = sha256()
        total = 0
        while True:
            chunk = os.read(fd, min(1_048_576, 67_108_865 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > 67_108_864:
                raise EvidenceError("candidate source exceeded 64 MiB while reading")
            digest.update(chunk)

        after = os.fstat(fd)
        stable_fields_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        stable_fields_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if stable_fields_before != stable_fields_after or total != after.st_size:
            raise EvidenceError("candidate source changed while being retained")
    except OSError as exc:
        raise EvidenceError("candidate buyer source could not be retained") from exc
    finally:
        if fd >= 0:
            os.close(fd)

    computed = digest.hexdigest()
    if expected and computed != expected:
        raise EvidenceError("candidate source digest does not match expected_sha256")
    return {"sha256": computed, "byte_size": total}


@dataclass(frozen=True)
class EvidenceRef:
    label: str
    locator: str
    note: str = ""

    def valid(self) -> bool:
        return _nonempty(self.label) and _nonempty(self.locator) and isinstance(self.note, str)

    def as_dict(self) -> dict[str, str]:
        if not self.valid():
            raise EvidenceError("invalid evidence reference")
        return {
            "label": self.label.strip(),
            "locator": self.locator.strip(),
            "note": self.note.strip(),
        }


@dataclass(frozen=True)
class SourceCustody:
    candidate_buyer_source_path: str | Path | None
    candidate_buyer_source_label: str = "Candidate buyer source"
    candidate_buyer_source_locator: str = ""
    expected_sha256: str = ""
    secondary_listing_refs: tuple[EvidenceRef, ...] = ()

    def result(self) -> dict[str, Any]:
        blockers: list[str] = []
        retained_candidate: dict[str, Any] | None = None

        if not _nonempty(self.candidate_buyer_source_label):
            blockers.append("candidate_source_label_missing")
        if not _nonempty(self.candidate_buyer_source_locator):
            blockers.append("candidate_source_locator_missing")
        if not blockers:
            try:
                hashed = _hash_retained_regular_file(
                    self.candidate_buyer_source_path,
                    expected_sha256=self.expected_sha256,
                )
                retained_candidate = {
                    "label": self.candidate_buyer_source_label.strip(),
                    "locator": self.candidate_buyer_source_locator.strip(),
                    **hashed,
                }
            except EvidenceError:
                blockers.append("candidate_buyer_source_not_retained_and_hashed")

        secondary = [
            ref.as_dict()
            for ref in self.secondary_listing_refs
            if isinstance(ref, EvidenceRef) and ref.valid()
        ]
        return {
            "status": "RETAINED_SOURCE_CANDIDATE_HASHED" if not blockers else "HOLD",
            "blockers": blockers,
            "retained_candidate": retained_candidate,
            "secondary_listing_refs": secondary,
            "secondary_sources_are_authority": False,
            "buyer_source_authority_established": False,
            "authority_note": (
                "A computed digest proves only retained-file custody in this process; "
                "buyer authorship and procurement authority require external review."
            ),
        }


@dataclass(frozen=True)
class PrimeCandidate:
    legal_name: str
    evidence: Mapping[str, EvidenceRef | None]

    def result(self) -> dict[str, Any]:
        blockers: list[str] = []
        if not _nonempty(self.legal_name):
            blockers.append("missing_legal_name")

        rows: dict[str, dict[str, str] | None] = {}
        for key in REQUIRED_PRIME_EVIDENCE:
            ref = self.evidence.get(key)
            if not isinstance(ref, EvidenceRef) or not ref.valid():
                blockers.append(f"missing_prime_evidence:{key}")
                rows[key] = None
            else:
                rows[key] = ref.as_dict()

        unknown = sorted(set(self.evidence) - set(REQUIRED_PRIME_EVIDENCE))
        if unknown:
            blockers.append("unknown_prime_evidence_keys")

        return {
            "status": "PRIME_EVIDENCE_INVENTORY_COMPLETE" if not blockers else "HOLD",
            "blockers": sorted(blockers),
            "legal_name": self.legal_name.strip() if isinstance(self.legal_name, str) else "",
            "evidence": rows,
            "unknown_evidence_keys": unknown,
            "prime_qualification_established": False,
            "authority_note": (
                "Evidence references are an inventory for external qualification review; "
                "this carrier does not certify prime eligibility."
            ),
        }


@dataclass(frozen=True)
class PaidWorkshare:
    owner: str
    deliverables: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    exclusions: tuple[str, ...]
    commercial_state: str = "PAID_SCOPE_TO_BE_AGREED"

    def result(self) -> dict[str, Any]:
        blockers: list[str] = []
        owner = self.owner.strip() if isinstance(self.owner, str) else ""
        if not owner:
            blockers.append("missing_workshare_owner")

        deliverables = _unique_strings(self.deliverables)
        unknown = sorted(set(deliverables) - set(WORKSHARE_DELIVERABLES))
        missing = sorted(set(WORKSHARE_DELIVERABLES) - set(deliverables))
        if missing:
            blockers.append("missing_workshare_deliverables")
        if unknown:
            blockers.append("unknown_workshare_deliverables")

        acceptance = _unique_strings(self.acceptance_criteria)
        exclusions = _unique_strings(self.exclusions)
        if not acceptance:
            blockers.append("missing_acceptance_criteria")
        if not exclusions:
            blockers.append("missing_exclusions")
        if self.commercial_state != "PAID_SCOPE_TO_BE_AGREED":
            blockers.append("unsupported_commercial_state")

        return {
            "status": "WORKSHARE_READY_FOR_REVIEW" if not blockers else "HOLD",
            "blockers": sorted(set(blockers)),
            "owner": owner,
            "deliverables": deliverables,
            "missing_deliverables": missing,
            "unknown_deliverables": unknown,
            "acceptance_criteria": acceptance,
            "exclusions": exclusions,
            "commercial_state": self.commercial_state,
        }


def compile_readiness(
    *,
    source_custody: SourceCustody,
    prime: PrimeCandidate,
    workshare: PaidWorkshare,
) -> dict[str, Any]:
    source = source_custody.result()
    prime_result = prime.result()
    workshare_result = workshare.result()

    teaming_blockers: list[str] = []
    if source["status"] != "RETAINED_SOURCE_CANDIDATE_HASHED":
        teaming_blockers.append("source_custody")
    if workshare_result["status"] != "WORKSHARE_READY_FOR_REVIEW":
        teaming_blockers.append("paid_workshare")

    prime_review_blockers = list(teaming_blockers)
    if prime_result["status"] != "PRIME_EVIDENCE_INVENTORY_COMPLETE":
        prime_review_blockers.append("prime_evidence_inventory")

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "opportunity": {
            "buyer": BUYER,
            "solicitation": SOLICITATION,
            "closing": CLOSING,
        },
        "source_custody": source,
        "prime": prime_result,
        "paid_workshare": workshare_result,
        "teaming_status": (
            "TEAMING_WORKSHARE_PACKET_READY_FOR_REVIEW" if not teaming_blockers else "HOLD"
        ),
        "teaming_blockers": sorted(teaming_blockers),
        "prime_review_status": (
            "EVIDENCE_INVENTORY_READY_FOR_EXTERNAL_QUALIFICATION_REVIEW"
            if not prime_review_blockers
            else "HOLD"
        ),
        "prime_review_blockers": sorted(prime_review_blockers),
        "submission_status": "HOLD_EXTERNAL_PRIME_AUTHORITY_REQUIRED",
        "external_authority": {
            "buyer_source_authority_established": False,
            "prime_qualification_established": False,
            "authorized_signatory_established": False,
            "prime_submission_approval_established": False,
            "physical_delivery_authority_established": False,
            "submission_authority_established": False,
            "award_established": False,
            "payment_established": False,
            "revenue_established": False,
        },
        "claims_boundary": (
            "Non-authorizing evidence carrier only. A retained-file digest proves custody, "
            "not buyer authorship. Evidence references are inventory, not prime qualification. "
            "This carrier has no input capable of granting signatory, submission, award, "
            "payment, cash, or revenue authority."
        ),
    }
    payload["receipt_sha256"] = sha256(_canonical(payload)).hexdigest()
    return payload


def render_markdown(pack: Mapping[str, Any]) -> str:
    lines = [
        "# Land Bank T12-09-26 non-authorizing teaming pack",
        "",
        f"- Teaming review packet: **{pack['teaming_status']}**",
        f"- Prime evidence review: **{pack['prime_review_status']}**",
        f"- Submission: **{pack['submission_status']}**",
        f"- Retained source candidate: **{pack['source_custody']['status']}**",
        f"- Prime evidence inventory: **{pack['prime']['status']}**",
        f"- Paid workshare: **{pack['paid_workshare']['status']}**",
        f"- Receipt SHA-256: `{pack['receipt_sha256']}`",
        "",
        "## Teaming blockers",
    ]
    lines.extend([f"- `{x}`" for x in pack["teaming_blockers"]] or ["- none"])
    lines.extend(["", "## Prime-review blockers"])
    lines.extend([f"- `{x}`" for x in pack["prime_review_blockers"]] or ["- none"])
    lines.extend(
        [
            "",
            "## Submission authority",
            "- `HOLD_EXTERNAL_PRIME_AUTHORITY_REQUIRED` (hard-coded; not caller promotable)",
            "",
            "## Claims boundary",
            str(pack["claims_boundary"]),
            "",
        ]
    )
    return "\n".join(lines)
