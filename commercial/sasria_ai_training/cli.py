"""CLI for compiling a fail-closed Sasria RFP2026/22 readiness pack."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .core import (
    BuyerTechnicalScore,
    EvidenceRef,
    PaidWorkshare,
    PrimeCandidate,
    SubmissionAuthority,
    TrainingPathway,
    compile_readiness_pack,
    render_markdown,
)


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    return data


def _ref(value: Any) -> EvidenceRef | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("evidence reference must be an object")
    return EvidenceRef(label=value.get("label", ""), locator=value.get("locator", ""), note=value.get("note", ""))


def _refs(values: Any) -> tuple[EvidenceRef, ...]:
    if values is None:
        return ()
    if not isinstance(values, list):
        raise ValueError("evidence references must be a list")
    return tuple(ref for item in values if (ref := _ref(item)) is not None)


def compile_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    prime_data = data.get("prime", {})
    score_data = data.get("technical_score", {})
    workshare_data = data.get("paid_workshare", {})
    authority_data = data.get("submission_authority", {})
    if not all(isinstance(value, dict) for value in (prime_data, score_data, workshare_data, authority_data)):
        raise ValueError("prime, technical_score, paid_workshare, and submission_authority must be objects")

    prime = PrimeCandidate(
        legal_name=prime_data.get("legal_name", ""),
        company_profile_ref=_ref(prime_data.get("company_profile_ref")),
        returnables=prime_data.get("returnables", {}),
        framework_alignment=tuple(prime_data.get("framework_alignment", [])),
        framework_evidence=_refs(prime_data.get("framework_evidence", [])),
        training_body_accreditation_ref=_ref(prime_data.get("training_body_accreditation_ref")),
        recognized_certification_capability_ref=_ref(prime_data.get("recognized_certification_capability_ref")),
        platform_access_12_months_ref=_ref(prime_data.get("platform_access_12_months_ref")),
        regulated_environment_training_ref=_ref(prime_data.get("regulated_environment_training_ref")),
        financial_services_training_ref=_ref(prime_data.get("financial_services_training_ref")),
        facilitator_refs=_refs(prime_data.get("facilitator_refs", [])),
        reference_letter_refs=_refs(prime_data.get("reference_letter_refs", [])),
        ai_trainings_last_3y=prime_data.get("ai_trainings_last_3y"),
    )
    technical_score = BuyerTechnicalScore(
        scores=score_data.get("scores", {}),
        evidence_refs=_refs(score_data.get("evidence_refs", [])),
    )
    pathways = tuple(
        TrainingPathway(
            role_group=item.get("role_group", ""),
            learning_outcomes=tuple(item.get("learning_outcomes", [])),
            delivery_modes=tuple(item.get("delivery_modes", [])),
            evaluation_methods=tuple(item.get("evaluation_methods", [])),
            artefacts=tuple(item.get("artefacts", [])),
        )
        for item in data.get("training_pathways", [])
        if isinstance(item, dict)
    )
    workshare = PaidWorkshare(
        owner=workshare_data.get("owner", ""),
        deliverables=tuple(workshare_data.get("deliverables", [])),
        acceptance_criteria=tuple(workshare_data.get("acceptance_criteria", [])),
        exclusions=tuple(workshare_data.get("exclusions", [])),
        commercial_state=workshare_data.get("commercial_state", "PAID_SCOPE_TO_BE_AGREED"),
    )
    authority = SubmissionAuthority(
        portal_account_confirmed=authority_data.get("portal_account_confirmed") is True,
        authorized_signatory_confirmed=authority_data.get("authorized_signatory_confirmed") is True,
        prime_approved_submission=authority_data.get("prime_approved_submission") is True,
    )
    return compile_readiness_pack(
        prime=prime,
        technical_score=technical_score,
        pathways=pathways,
        workshare=workshare,
        submission_authority=authority,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Sasria RFP2026/22 evidence without inventing prime qualifications.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args(argv)
    pack = compile_from_dict(_load(args.input))
    rendered = json.dumps(pack, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.markdown_out:
        args.markdown_out.write_text(render_markdown(pack), encoding="utf-8")
    return 0 if pack["submission_status"] == "SUBMISSION_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
