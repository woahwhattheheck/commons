#!/usr/bin/env python3
"""Fail-closed release validator for the Diversey Proof-of-Clean proposal carrier."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA = "DIVERSEY_PROOF_CLEAN_2026_READINESS_V1"
OFFICIAL_URL = "https://www.innocentive.com/challenges/novel-technologies-for-rapid-proof-of-clean-in-professional-environments/"
DEADLINE = "2026-09-21T23:59:00-04:00"

REQUIRED_GATES = {
    "challenge_agreement_reviewed",
    "solver_eligibility_verified",
    "participation_type_selected",
    "applicant_identity_completed",
    "first_hand_experience_completed",
    "technical_owner_reviewed",
    "trl_confirmed",
    "scientific_claims_verified",
    "ip_and_freedom_to_operate_reviewed",
    "partnership_posture_authorized",
    "human_rewrite_complete",
    "final_proposal_human_reviewed",
    "external_submission_authorized",
}

REQUIRED_PROPOSAL_HEADINGS = [
    "## 1. Participation Type",
    "## 2. Solution Level",
    "## 3. Partnering",
    "## 4. Problem & Opportunity",
    "## 5. Solution Overview",
    "## 6. Solution Feasibility / Scientific Basis",
    "## 7. Performance Expectations",
    "## 8. Experience",
    "## 9. Solution Risks",
    "## 10. Development Timeline and Capability",
    "## 11. Online References",
]

REQUIRED_SCIENCE_REFS = [
    "10.1016/j.talanta.2023.125561",
    "pubmed.ncbi.nlm.nih.gov/42107219",
    "pubmed.ncbi.nlm.nih.gov/36495704",
    "pubmed.ncbi.nlm.nih.gov/39194631",
]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def _safe_file(root: Path, value: str, field: str, errors: list[str]) -> Path | None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{field}: path must stay inside the competition directory")
        return None
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{field}: resolved path escapes competition directory")
        return None
    if not resolved.is_file():
        errors.append(f"{field}: file does not exist: {value}")
        return None
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(root: Path) -> tuple[str, list[str]]:
    errors: list[str] = []
    manifest_path = root / "readiness.json"
    try:
        manifest = _load_json(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return "UNKNOWN", [f"readiness.json: {exc}"]

    state = manifest.get("state")
    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if state not in {"BLOCKED", "READY"}:
        errors.append("state must be BLOCKED or READY")

    opportunity = manifest.get("opportunity")
    if not isinstance(opportunity, dict):
        errors.append("opportunity must be an object")
        opportunity = {}
    if opportunity.get("official_url") != OFFICIAL_URL:
        errors.append("official opportunity URL drifted")
    if opportunity.get("deadline_local") != DEADLINE:
        errors.append("challenge deadline drifted; revalidate official page before changing it")
    if opportunity.get("advertised_award_usd") != 10000:
        errors.append("advertised award must remain 10000 unless revalidated and validator updated")

    concept = manifest.get("concept")
    if not isinstance(concept, dict):
        errors.append("concept must be an object")
        concept = {}
    if concept.get("integrated_prototype_exists") is not False:
        errors.append("integrated_prototype_exists must remain false until evidence-backed source update")
    if concept.get("measured_integrated_performance_exists") is not False:
        errors.append("measured_integrated_performance_exists must remain false until evidence-backed source update")
    if concept.get("strain_level_claimed") is not False:
        errors.append("strain_level_claimed must remain false without binder-specific validation")
    if concept.get("whole_room_claimed") is not False:
        errors.append("whole_room_claimed must remain false for this surface-sampling concept")

    source_files = manifest.get("source_files")
    if not isinstance(source_files, list) or not source_files:
        errors.append("source_files must be a non-empty list")
    else:
        for index, item in enumerate(source_files):
            if not isinstance(item, str):
                errors.append(f"source_files[{index}] must be a string")
                continue
            _safe_file(root, item, f"source_files[{index}]", errors)

    gates = manifest.get("human_gates")
    if not isinstance(gates, dict):
        errors.append("human_gates must be an object")
        gates = {}
    missing_gates = sorted(REQUIRED_GATES - set(gates))
    extra_gates = sorted(set(gates) - REQUIRED_GATES)
    if missing_gates:
        errors.append("missing human gates: " + ", ".join(missing_gates))
    if extra_gates:
        errors.append("unknown human gates: " + ", ".join(extra_gates))
    for name in REQUIRED_GATES & set(gates):
        if not isinstance(gates[name], bool):
            errors.append(f"human_gates.{name} must be boolean")

    external = manifest.get("external_actions")
    if not isinstance(external, dict):
        errors.append("external_actions must be an object")
        external = {}
    for name, value in external.items():
        if not isinstance(value, bool):
            errors.append(f"external_actions.{name} must be boolean")

    if external.get("submitted") and not gates.get("external_submission_authorized"):
        errors.append("submitted cannot be true without external_submission_authorized")
    if external.get("award_received") and not external.get("submitted"):
        errors.append("award_received cannot be true without submitted")
    if external.get("payment_received") and not external.get("award_received"):
        errors.append("payment_received cannot be true without award_received")
    if external.get("challenge_agreement_accepted") and not gates.get("challenge_agreement_reviewed"):
        errors.append("Challenge Agreement cannot be marked accepted before human review gate")

    draft_path = root / "PROPOSAL-DRAFT.md"
    if not draft_path.is_file():
        errors.append("PROPOSAL-DRAFT.md is missing")
    else:
        draft = draft_path.read_text(encoding="utf-8")
        for heading in REQUIRED_PROPOSAL_HEADINGS:
            if heading not in draft:
                errors.append(f"proposal draft missing form heading: {heading}")
        if OFFICIAL_URL not in draft:
            errors.append("proposal draft missing official challenge URL")

    science_path = root / "SCIENTIFIC-BASIS.md"
    if not science_path.is_file():
        errors.append("SCIENTIFIC-BASIS.md is missing")
    else:
        science = science_path.read_text(encoding="utf-8")
        for ref in REQUIRED_SCIENCE_REFS:
            if ref not in science:
                errors.append(f"scientific basis missing required precedent: {ref}")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("artifacts must be an object")
        artifacts = {}
    final = artifacts.get("final_proposal")
    if not isinstance(final, dict):
        errors.append("artifacts.final_proposal must be an object")
        final = {}
    final_path = final.get("path")
    final_sha = final.get("sha256")
    if (final_path is None) != (final_sha is None):
        errors.append("final proposal path and sha256 must be set together")

    resolved_final: Path | None = None
    if final_path is not None:
        if not isinstance(final_path, str) or not isinstance(final_sha, str):
            errors.append("final proposal path and sha256 must be strings")
        else:
            resolved_final = _safe_file(root, final_path, "artifacts.final_proposal.path", errors)
            if len(final_sha) != 64 or any(c not in "0123456789abcdef" for c in final_sha.lower()):
                errors.append("artifacts.final_proposal.sha256 must be 64 hex characters")
            elif resolved_final is not None and _sha256(resolved_final) != final_sha.lower():
                errors.append("final proposal sha256 does not match file bytes")

    if state == "BLOCKED" and gates.get("external_submission_authorized"):
        errors.append("BLOCKED state cannot have external_submission_authorized=true")

    if state == "READY":
        false_gates = sorted(name for name in REQUIRED_GATES if gates.get(name) is not True)
        if false_gates:
            errors.append("READY requires every human gate true: " + ", ".join(false_gates))
        if not external.get("challenge_agreement_accepted"):
            errors.append("READY requires human acceptance of the current Challenge Agreement")
        if final_path is None or resolved_final is None:
            errors.append("READY requires a hashed final human proposal artifact")
        elif final_path == "PROPOSAL-DRAFT.md":
            errors.append("READY final proposal must be a separate human-rewritten artifact, not PROPOSAL-DRAFT.md")
        else:
            final_text = resolved_final.read_text(encoding="utf-8", errors="replace")
            forbidden = ("[HUMAN:", "[UNMEASURED", "DO NOT SUBMIT THIS FILE VERBATIM")
            for marker in forbidden:
                if marker in final_text:
                    errors.append(f"final human proposal still contains draft marker: {marker}")

    return str(state or "UNKNOWN"), errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)

    state, errors = validate(args.root)
    result = {"state": state, "valid": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        return 1
    if args.require_ready and state != "READY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
