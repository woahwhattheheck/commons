"""Source-bound internal pursuit snapshot; source recovery is not qualification.

The data and its requirements/source identities form one reviewed generation.
No network, contact, submission, scheduling or commercial action is performed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

OPPORTUNITY_ID = "INVEST-APPALACHIA-FRAMER-LMS-20260916"
BUYER = "Invest Appalachia"
DEADLINE = "2026-09-22T21:00:00Z"
CAP = 60000
START = "2026-10-13"
END = "2027-04-30"
SOURCE = "https://investappalachia.org/framer-rfp/"
RFP = "https://investappalachia.org/wp-content/uploads/2026/08/1.-draft2_RFP_Invest_Appalachia_Framer_Training_LMS.docx.pdf"
ZIP = "https://investappalachia.org/wp-content/uploads/2026/08/Zipped-RFP-Docs.zip"
SUBJECT = "RFP Proposal Submission - Invest Appalachia Framer Training LMS"
CURRENT_PACKET_SHA256 = "79e1bfc46617239e1c05b4c22e97e4d6672743103041e2b6b7b3e71bd6d1b30d"
REQUIREMENTS_SHA256 = "5d012da1612cb220cfe0d7c4c02c47175a726bad1254855240c24afa6926ef66"
SOURCE_MANIFEST_SHA256 = "a70c78c77a7084ef9cf1499f0e7831e2031d4e635405c8955df25b57c6f01093"
GATES = ("two_lms_platform_implementations", "adult_learning_packaging", "start_capacity_2026_10_13", "w9_available", "general_liability_available", "professional_liability_available", "cybersecurity_insurance_available", "two_relevant_project_examples", "two_prior_client_references")
AUTH = ("external_contact_authorized", "submission_authorized", "signature_authorized", "contract_acceptance_authorized", "spend_authorized", "payment_authorized", "award_or_revenue_asserted")


class PursuitError(ValueError):
    pass


def _make_generation():
    # Capture reviewed constants/functions; changing compatibility globals later
    # cannot substitute another packet, source bundle or receipt interpretation.
    packet_sha = CURRENT_PACKET_SHA256
    requirements_sha = REQUIREMENTS_SHA256
    manifest_sha = SOURCE_MANIFEST_SHA256
    gates, auth = GATES, AUTH
    opportunity_id, deadline = OPPORTUNITY_ID, DEADLINE
    expected_opportunity = (OPPORTUNITY_ID, BUYER, SOURCE, RFP, ZIP, DEADLINE, CAP, START, END, SUBJECT, "RECOVERED_BUYER_DOCUMENTS")
    binding = {"generation_id": "framer-reviewed-sources-20260919", "source_manifest_sha256": manifest_sha, "requirements_sha256": requirements_sha}
    base = Path(__file__).resolve().parent
    error, dumps, loads, sha256 = PursuitError, json.dumps, json.loads, hashlib.sha256

    def canon(value: Any) -> bytes:
        try:
            return dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8", "strict")
        except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError) as exc:
            raise error(f"cannot canonicalize packet: {exc}") from exc

    def digest(value: Any) -> str:
        return sha256(canon(value)).hexdigest()

    def exact(value: Any, keys: set[str], where: str):
        if type(value) is not dict or set(value) != keys:
            raise error(f"{where}: exact object contract mismatch")
        return value

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise error(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(token):
        raise error(f"non-finite JSON: {token}")

    def load_json(path: Path) -> Any:
        try:
            value = loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=reject_constant)
            canon(value)
            return value
        except error:
            raise
        except (OSError, UnicodeError, ValueError, TypeError, RecursionError, OverflowError) as exc:
            raise error(f"invalid packet: {exc}") from exc

    def validate_sources(requirements=None, source_manifest=None):
        requirements = load_json(base / "requirements.json") if requirements is None else requirements
        source_manifest = load_json(base / "source_generation.json") if source_manifest is None else source_manifest
        if digest(requirements) != requirements_sha:
            raise error("requirements do not match reviewed source generation")
        if digest(source_manifest) != manifest_sha:
            raise error("source manifest does not match reviewed source generation")
        if requirements["source_manifest_sha256"] != manifest_sha or requirements["source_generation_id"] != binding["generation_id"]:
            raise error("requirements/source generation binding mismatch")
        return dict(binding)

    def normalize(raw: Any, requirements=None, source_manifest=None) -> dict[str, Any]:
        captured = canon(raw)
        if sha256(captured).hexdigest() != packet_sha:
            raise error("packet does not match retained current qualification generation")
        # Use the exact captured bytes throughout validation and receipt creation.
        p = loads(captured)
        exact(p, {"opportunity", "qualification", "proposal", "authority", "source_generation", "eligibility"}, "packet")
        if p["source_generation"] != validate_sources(requirements, source_manifest):
            raise error("packet/source generation binding mismatch")
        o = exact(p["opportunity"], {"opportunity_id", "buyer", "source_url", "rfp_url", "attachments_zip_url", "deadline_utc", "budget_cap_usd", "contract_start", "contract_end", "submission_subject", "attachments_status"}, "opportunity")
        fields = ("opportunity_id", "buyer", "source_url", "rfp_url", "attachments_zip_url", "deadline_utc", "budget_cap_usd", "contract_start", "contract_end", "submission_subject", "attachments_status")
        if tuple(o[key] for key in fields) != expected_opportunity:
            raise error("official opportunity/current-source binding mismatch")
        q = exact(p["qualification"], set(gates), "qualification")
        for name in gates:
            g = exact(q[name], {"state", "evidence_refs", "note"}, name)
            if g["state"] not in {"VERIFIED", "MISSING", "HOLD"}:
                raise error(f"{name}: bad state")
            if type(g["evidence_refs"]) is not list or any(type(x) is not str or not x for x in g["evidence_refs"]):
                raise error(f"{name}: bad evidence")
            if g["state"] == "VERIFIED" and not g["evidence_refs"]:
                raise error(f"{name}: VERIFIED requires retained evidence")
            if type(g["note"]) is not str or not g["note"]:
                raise error(f"{name}: note required")
        e = exact(p["eligibility"], {"us_registered_prime"}, "eligibility")
        if e["us_registered_prime"]["state"] != "HOLD" or e["us_registered_prime"]["evidence_refs"]:
            raise error("U.S.-prime eligibility remains unverified")
        pr = exact(p["proposal"], {"proposed_total_usd", "year1_license_usd", "post_year1_recurring_usd", "platform_recommendation", "attachments_complete", "pricing_state"}, "proposal")
        for key in ("proposed_total_usd", "year1_license_usd", "post_year1_recurring_usd"):
            if type(pr[key]) is not int or pr[key] != 0:
                raise error(f"{key}: retained unpriced zero placeholder required")
        if pr["pricing_state"] != "UNPRICED_ZERO_PLACEHOLDERS" or pr["attachments_complete"] is not False:
            raise error("bidder responses remain unpriced and incomplete")
        a = exact(p["authority"], set(auth), "authority")
        if any(value is not False for value in a.values()):
            raise error("all external/commercial authority must remain false")
        return p

    def evaluate(raw: Any, requirements=None, source_manifest=None) -> dict[str, Any]:
        n = normalize(raw, requirements, source_manifest)
        out = {
            "schema": "invest_appalachia_framer_lms.pursuit_receipt.v4",
            "opportunity_id": opportunity_id,
            "prime_status": "PRIME_HOLD",
            "teaming_status": "TEAMING_ROUTE_OPEN_INTERNAL",
            "unverified_or_missing_gates": sorted(key for key, value in n["qualification"].items() if value["state"] != "VERIFIED"),
            "us_prime_eligibility": "UNVERIFIED",
            "attachments_status": "RECOVERED_BUYER_DOCUMENTS",
            "bidder_response_status": "INCOMPLETE",
            "proposal_budget_state": "HOLD_UNPRICED_ATTACHMENTS_INCOMPLETE",
            "proposal_budget_within_cap": False,
            "submission_deadline_utc": deadline,
            "deadline_currentness_authoritative": False,
            "fresh_deadline_recensus_required_before_action": True,
            "qualification_generation_sha256": packet_sha,
            "source_generation": dict(binding),
            "source_identity_basis": "RETAINED_REVIEW_RECORDS_NOT_NEW_DOWNLOAD",
            "experience_evidence_route": "COLLECTIVE_NAMED_KEY_PERSONNEL_INCLUDING_NAMED_SPECIALIST",
            **{key: False for key in auth},
            "normalized_input_sha256": digest(n),
        }
        out["receipt_sha256"] = digest(out)
        return out

    return canon, digest, exact, load_json, validate_sources, normalize, evaluate


canon, digest, exact, load_json, validate_sources, normalize, evaluate = _make_generation()
del _make_generation


def _make_main(evaluate_fn, load_fn, path_type, dumps, error_type):
    base = path_type(__file__).resolve().parent

    def main(argv=None):
        import argparse
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--current-packet", type=path_type, default=base / "current_packet.json")
        parser.add_argument("--requirements", type=path_type, default=base / "requirements.json")
        parser.add_argument("--source-manifest", type=path_type, default=base / "source_generation.json")
        args = parser.parse_args(argv)
        try:
            receipt = evaluate_fn(load_fn(args.current_packet), load_fn(args.requirements), load_fn(args.source_manifest))
        except error_type as exc:
            parser.error(str(exc))
        print(dumps(receipt, indent=2, sort_keys=True))
        return 0
    return main


main = _make_main(evaluate, load_json, Path, json.dumps, PursuitError)
del _make_main

if __name__ == "__main__":
    raise SystemExit(main())
