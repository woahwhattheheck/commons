from __future__ import annotations
import argparse
import json
from datetime import datetime
from pathlib import Path

class ValidationError(ValueError):
    pass

TOP = {"schema_version","operation","opportunity","sources","qualification","workshare","target","authority"}
AUTH_KEYS = {
    "buyer_contact_authorized","target_contact_authorized","muse_clearance_present",
    "portal_submission_authorized","signature_authorized","accepted_workshare",
    "award_claimed","payment_claimed","revenue_claimed",
}
ALLOWED_SOURCE_CLASSES = {"BUYER_OFFICIAL","BUYER_REGISTRY","MARKETPLACE_MIRROR","TARGET_FIRST_PARTY"}

def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValidationError(f"duplicate key: {key}")
        out[key] = value
    return out

def loads_exact(raw: str):
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda v: (_ for _ in ()).throw(ValidationError(f"non-finite: {v}")))
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(str(exc)) from exc
    return value

def _exact_keys(obj, expected, where):
    if not isinstance(obj, dict):
        raise ValidationError(f"{where}: object required")
    got = set(obj)
    if got != set(expected):
        raise ValidationError(f"{where}: keys mismatch missing={sorted(set(expected)-got)} extra={sorted(got-set(expected))}")

def _string(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{where}: nonempty string required")
    return value

def _false(value, where):
    if value is not False:
        raise ValidationError(f"{where}: must remain false")

def validate(packet):
    _exact_keys(packet, TOP, "packet")
    if packet["schema_version"] != 1 or isinstance(packet["schema_version"], bool):
        raise ValidationError("schema_version: expected integer 1")
    if packet["operation"] != "FCS-12527-PURSUIT-PACKET-RECOVERY-ZSOL-20260917":
        raise ValidationError("operation: wrong carrier")

    opportunity = packet["opportunity"]
    _exact_keys(opportunity, {
        "buyer","solicitation","registry_id","response_deadline","questions_deadline",
        "response_channel","budget","source_state"
    }, "opportunity")
    expected = {
        "buyer":"Fulton County School System",
        "solicitation":"125-27 Professional and Consulting Services for the Strategy and Technology Division",
        "registry_id":"PE-55101-NONST-2027-000000191",
        "response_deadline":"2026-09-29T14:30:00-04:00",
        "questions_deadline":"2026-09-15T16:00:00-04:00",
        "response_channel":"Euna Procurement / Bonfire",
        "budget":"UNKNOWN",
        "source_state":"PUBLIC_SOURCE_BOUND",
    }
    for key, wanted in expected.items():
        if opportunity[key] != wanted:
            raise ValidationError(f"opportunity.{key}: drift")
    if datetime.fromisoformat(opportunity["questions_deadline"]) >= datetime.fromisoformat(opportunity["response_deadline"]):
        raise ValidationError("opportunity: chronology invalid")

    sources = packet["sources"]
    if not isinstance(sources, list) or len(sources) < 4:
        raise ValidationError("sources: at least four required")
    seen_urls = set()
    for i, row in enumerate(sources):
        _exact_keys(row, {"class","url","claim"}, f"sources[{i}]")
        if row["class"] not in ALLOWED_SOURCE_CLASSES:
            raise ValidationError(f"sources[{i}].class: unsupported")
        url = _string(row["url"], f"sources[{i}].url")
        if not url.startswith("https://"):
            raise ValidationError(f"sources[{i}].url: https required")
        if url in seen_urls:
            raise ValidationError(f"sources[{i}]: duplicate url")
        seen_urls.add(url)
        _string(row["claim"], f"sources[{i}].claim")
    if not any(row["class"] == "BUYER_OFFICIAL" for row in sources):
        raise ValidationError("sources: buyer official source required")
    if not any(row["class"] == "BUYER_REGISTRY" for row in sources):
        raise ValidationError("sources: buyer registry source required")
    if sum(row["class"] == "TARGET_FIRST_PARTY" for row in sources) < 2:
        raise ValidationError("sources: target first-party evidence insufficient")

    qualification = packet["qualification"]
    _exact_keys(qualification, {"posture","direct_prime_ready","known_owner_side_blockers","buyer_question_window"}, "qualification")
    if qualification["posture"] != "TEAM_ONLY" or qualification["direct_prime_ready"] is not False:
        raise ValidationError("qualification: direct-prime escalation forbidden")
    if qualification["buyer_question_window"] != "CLOSED":
        raise ValidationError("qualification: question-window drift")
    blockers = qualification["known_owner_side_blockers"]
    if not isinstance(blockers, list) or len(blockers) < 6 or any(not isinstance(x, str) or not x for x in blockers):
        raise ValidationError("qualification: blocker set incomplete")

    workshare = packet["workshare"]
    _exact_keys(workshare, {"state","fixed_price_usd","target_duration_business_days_after_complete_intake","deliverables","excluded_authority"}, "workshare")
    if workshare["state"] != "PROPOSED_NOT_ACCEPTED":
        raise ValidationError("workshare: acceptance cannot be asserted")
    if type(workshare["fixed_price_usd"]) is not int or workshare["fixed_price_usd"] != 25000:
        raise ValidationError("workshare.fixed_price_usd: expected 25000")
    if type(workshare["target_duration_business_days_after_complete_intake"]) is not int or workshare["target_duration_business_days_after_complete_intake"] != 15:
        raise ValidationError("workshare duration: drift")
    if not isinstance(workshare["deliverables"], list) or len(workshare["deliverables"]) < 5:
        raise ValidationError("workshare: deliverables incomplete")
    if not isinstance(workshare["excluded_authority"], list) or len(workshare["excluded_authority"]) < 8:
        raise ValidationError("workshare: authority exclusions incomplete")

    target = packet["target"]
    _exact_keys(target, {"organization","route","role","state","fit","collision_census"}, "target")
    if target["organization"] != "MGT" or target["route"] != "obhatti@mgt.us":
        raise ValidationError("target: identity/route drift")
    if target["state"] != "RESEARCHED_NOT_CONTACTED":
        raise ValidationError("target: repository may not mint contact state")
    if not isinstance(target["fit"], list) or len(target["fit"]) < 4:
        raise ValidationError("target: fit evidence incomplete")
    census = target["collision_census"]
    _exact_keys(census, {"slack_exact_route","slack_domain_since_2026_09_01","gmail_domain_or_route","captured_at"}, "target.collision_census")
    for key in ("slack_exact_route","slack_domain_since_2026_09_01","gmail_domain_or_route"):
        if type(census[key]) is not int or census[key] != 0:
            raise ValidationError(f"target.collision_census.{key}: expected exact zero at carrier capture")
    datetime.fromisoformat(census["captured_at"])

    authority = packet["authority"]
    _exact_keys(authority, AUTH_KEYS, "authority")
    for key in AUTH_KEYS:
        _false(authority[key], f"authority.{key}")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    raw = args.packet.read_text(encoding="utf-8")
    validate(loads_exact(raw))
    print("VALID")

if __name__ == "__main__":
    main()
