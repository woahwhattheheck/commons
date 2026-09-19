#!/usr/bin/env python3
"""Deterministic generator for the UIOWA-109 case and its defect fixtures.

Every fixture in this kit is the SAME clean base with exactly ONE documented
mutation applied. That is deliberate: when `timeline-disagreement.json` fires a
finding and `clean.json` does not, the only thing that changed is the mutation,
so the fixture proves the checker reacts to that defect and nothing else.

Hand-editing a fixture would destroy that property, so regenerate instead:

    python3 make_fixtures.py

It overwrites only `case.json` and `fixtures/*.json`. It never touches a report.

Everything produced here is FICTIONAL. `ess-prod` is not a real environment,
`SVC-ESS` is not a real service, and no date, digest or measurement below
describes the University of Iowa or any real release or incident.
"""

import copy
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")

FICTION = (
    "SYNTHETIC / FICTIONAL. Every service, environment, release, digest, date and "
    "measurement in this file was invented for artifact review. Nothing here describes "
    "the University of Iowa, any real service, any real release, or any real incident. "
    "Do not cite any figure in this file as a finding."
)


def digest(label):
    """A stable, obviously-synthetic 64-hex digest derived from a label."""
    return hashlib.sha256(f"uiowa-109-synthetic:{label}".encode()).hexdigest()


def revision(label):
    return hashlib.sha1(f"uiowa-109-synthetic-rev:{label}".encode()).hexdigest()


def ev(evidence_id, locator, owner_role, kind="synthetic",
       captured_at="2026-09-18T09:00:00Z"):
    return {"evidence_id": evidence_id, "locator": locator, "owner_role": owner_role,
            "kind": kind, "captured_at": captured_at}


def event(event_id, kind, observed_at, evidence_id):
    return {"event_id": event_id, "kind": kind, "observed_at": observed_at,
            "evidence_id": evidence_id}


def ref(event_id, asserted_at=None):
    """An event reference. `asserted_at` is the citing component's OWN claim."""
    return {"event_id": event_id, "asserted_at": asserted_at}


ARTIFACT_SHA = digest("artifact-fictional-2.3.0")
SRC_REV = revision("approved")
REPO = "https://example.invalid/fictional-ess-service"


# ---------------------------------------------------------------------------
# Clean base -- must return AGREED with ZERO findings.
# ---------------------------------------------------------------------------

def clean_case():
    """A release verified in the environment it was deployed to, fully recovered.

    This is the false-positive guard. If the checker fires anything at all on this
    case, the checker is wrong -- not the fixture.
    """
    return {
        "fiction_notice": FICTION,
        "schema_version": 1,
        "case_id": "SYN-109-CLEAN",
        "data_class": "synthetic",
        "as_of": "2026-09-18T12:00:00Z",
        "evidence": [
            ev("EV-SYN-APPROVAL", "synthetic-records.md#approval",
               "Service change coordinator"),
            ev("EV-SYN-BUILD", "synthetic-records.md#build", "Build-platform maintainer"),
            ev("EV-SYN-ARTIFACT", "synthetic-records.md#artifact", "Release custodian"),
            ev("EV-SYN-DEPLOY", "synthetic-records.md#deployment",
               "Service operations owner"),
            ev("EV-SYN-VERIFY-PROD", "synthetic-records.md#verify-prod",
               "Service operations owner"),
            ev("EV-SYN-IAM-BACKUP", "synthetic-records.md#iam-backup",
               "Identity and Access team"),
            ev("EV-SYN-IAM-RESTORE", "synthetic-records.md#iam-restore",
               "Identity and Access team"),
            ev("EV-SYN-IAM-BIZVERIFY", "synthetic-records.md#iam-bizverify",
               "Identity and Access team"),
            ev("EV-SYN-RIS-BACKUP", "synthetic-records.md#ris-backup",
               "Research Information team"),
            ev("EV-SYN-RIS-RESTORE", "synthetic-records.md#ris-restore",
               "Research Information team"),
            ev("EV-SYN-RIS-DEPVERIFY", "synthetic-records.md#ris-depverify",
               "Research Information team"),
            ev("EV-SYN-RIS-BIZVERIFY", "synthetic-records.md#ris-bizverify",
               "Research Information team"),
        ],
        "events": [
            event("EVT-SRC-APPROVED", "source_approved", "2026-09-17T14:00:00Z",
                  "EV-SYN-APPROVAL"),
            event("EVT-BUILD-STARTED", "build_started", "2026-09-17T15:00:00Z",
                  "EV-SYN-BUILD"),
            event("EVT-BUILD-FINISHED", "build_finished", "2026-09-17T15:20:00Z",
                  "EV-SYN-BUILD"),
            event("EVT-DEPLOY", "deployment", "2026-09-17T22:00:00Z", "EV-SYN-DEPLOY"),
            event("EVT-VERIFY-PROD", "verification", "2026-09-17T22:10:00Z",
                  "EV-SYN-VERIFY-PROD"),
            event("EVT-IAM-BACKUP", "backup_completed", "2026-09-17T21:00:00Z",
                  "EV-SYN-IAM-BACKUP"),
            event("EVT-IAM-DISRUPT", "disruption", "2026-09-17T22:20:00Z",
                  "EV-SYN-IAM-RESTORE"),
            event("EVT-IAM-PIT", "restored_data_as_of", "2026-09-17T21:00:00Z",
                  "EV-SYN-IAM-RESTORE"),
            event("EVT-IAM-RESTORE", "restore_completed", "2026-09-17T22:50:00Z",
                  "EV-SYN-IAM-RESTORE"),
            event("EVT-IAM-BIZVERIFY", "business_verification", "2026-09-17T23:00:00Z",
                  "EV-SYN-IAM-BIZVERIFY"),
            event("EVT-RIS-BACKUP", "backup_completed", "2026-09-17T21:10:00Z",
                  "EV-SYN-RIS-BACKUP"),
            event("EVT-RIS-DISRUPT", "disruption", "2026-09-17T22:20:00Z",
                  "EV-SYN-RIS-RESTORE"),
            event("EVT-RIS-PIT", "restored_data_as_of", "2026-09-17T21:10:00Z",
                  "EV-SYN-RIS-RESTORE"),
            event("EVT-RIS-RESTORE", "restore_completed", "2026-09-17T23:20:00Z",
                  "EV-SYN-RIS-RESTORE"),
            event("EVT-RIS-DEPVERIFY", "dependency_verification",
                  "2026-09-17T23:05:00Z", "EV-SYN-RIS-DEPVERIFY"),
            event("EVT-RIS-BIZVERIFY", "business_verification", "2026-09-17T23:30:00Z",
                  "EV-SYN-RIS-BIZVERIFY"),
        ],
        "environments": [
            {"environment_id": "ess-prod",
             "purpose": "fictional environment that serves the release"},
        ],
        "release": {
            "source": {
                "source_id": "SRC-1", "repository": REPO, "revision": SRC_REV,
                "approved_revision": SRC_REV,
                "approved": ref("EVT-SRC-APPROVED", "2026-09-17T14:00:00Z"),
                "approval_evidence_id": "EV-SYN-APPROVAL",
            },
            "build": {
                "build_id": "BLD-1", "source_id": "SRC-1", "observed_repository": REPO,
                "observed_revision": SRC_REV, "builder_id": "synthetic/build-platform",
                "input_coverage": "declared_complete",
                "started": ref("EVT-BUILD-STARTED", "2026-09-17T15:00:00Z"),
                "finished": ref("EVT-BUILD-FINISHED", "2026-09-17T15:20:00Z"),
                "evidence_id": "EV-SYN-BUILD",
            },
            "artifact": {
                "artifact_id": "ART-1", "build_id": "BLD-1", "version": "fictional-2.3.0",
                "sha256": ARTIFACT_SHA, "evidence_id": "EV-SYN-ARTIFACT",
            },
            "deployment": {
                "deployment_id": "DEP-1", "artifact_id": "ART-1", "environment": "ess-prod",
                "observed_version": "fictional-2.3.0", "observed_sha256": ARTIFACT_SHA,
                "deployed": ref("EVT-DEPLOY", "2026-09-17T22:00:00Z"),
                "evidence_id": "EV-SYN-DEPLOY",
            },
        },
        "verifications": [
            {"verification_id": "VER-PROD", "environment": "ess-prod",
             "artifact_version": "fictional-2.3.0", "outcome": "PASSED",
             "performed": ref("EVT-VERIFY-PROD", "2026-09-17T22:10:00Z"),
             "evidence_id": "EV-SYN-VERIFY-PROD"},
        ],
        "recovery": {
            "assessment_id": "SYN-109-CLEAN-RECOVERY",
            "services": [
                {
                    "service_id": "SVC-IAM", "name": "Synthetic sign-in",
                    "business_function": "Authenticate users to in-scope services",
                    "target_rpo_minutes": 90, "target_rto_minutes": 60,
                    "dependencies": [],
                    "backup": {"last_successful": ref("EVT-IAM-BACKUP"),
                               "evidence_id": "EV-SYN-IAM-BACKUP"},
                    "exercise": {
                        "exercise_id": "EX-SYN-IAM-01",
                        "disruption": ref("EVT-IAM-DISRUPT", "2026-09-17T22:20:00Z"),
                        "restored_data_as_of": ref("EVT-IAM-PIT"),
                        "restore_completed": ref("EVT-IAM-RESTORE",
                                                 "2026-09-17T22:50:00Z"),
                        "business_verification": ref("EVT-IAM-BIZVERIFY"),
                        "dependency_results": [],
                    },
                },
                {
                    "service_id": "SVC-RIS", "name": "Synthetic research submission",
                    "business_function": "Submit and route a research administration packet",
                    "target_rpo_minutes": 90, "target_rto_minutes": 120,
                    "dependencies": ["SVC-IAM"],
                    "backup": {"last_successful": ref("EVT-RIS-BACKUP"),
                               "evidence_id": "EV-SYN-RIS-BACKUP"},
                    "exercise": {
                        "exercise_id": "EX-SYN-RIS-01",
                        "disruption": ref("EVT-RIS-DISRUPT", "2026-09-17T22:20:00Z"),
                        "restored_data_as_of": ref("EVT-RIS-PIT"),
                        "restore_completed": ref("EVT-RIS-RESTORE",
                                                 "2026-09-17T23:20:00Z"),
                        "business_verification": ref("EVT-RIS-BIZVERIFY"),
                        "dependency_results": [
                            {"dependency_id": "SVC-IAM",
                             "verified": ref("EVT-RIS-DEPVERIFY", "2026-09-17T23:05:00Z"),
                             "evidence_id": "EV-SYN-RIS-DEPVERIFY"},
                        ],
                    },
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# The narrative case the order asks for
# ---------------------------------------------------------------------------

def narrative_case():
    """The order's story: known artifact version, environment difference, a FAILED
    verification, and the recovery records that follow.

    Deliberately shows BOTH a strength and a real gap:
      strength -- SVC-ESS recovers with a complete evidence chain (DEMONSTRATED)
      gap      -- SVC-RIS's dependency verification has no observed time, so its
                  claim is unsupported and it stays PARTIAL; SVC-IAM was never
                  exercised at all and its backup rests on interview evidence.
    """
    case = clean_case()
    case["case_id"] = "SYN-109-ESS-RELEASE-01"
    case["recovery"]["assessment_id"] = "SYN-109-ESS-RELEASE-01-RECOVERY"

    case["environments"] = [
        {"environment_id": "ess-stage",
         "purpose": "fictional pre-release verification environment"},
        {"environment_id": "ess-prod",
         "purpose": "fictional environment that serves the release"},
    ]

    # Evidence: add the staging verification and the SVC-ESS rows; SVC-IAM's backup
    # is interview-only on purpose, to exercise UIOWA-057's rule that interview
    # evidence without artifact corroboration stays UNKNOWN.
    case["evidence"] = [e for e in case["evidence"]
                        if e["evidence_id"] not in {"EV-SYN-IAM-BACKUP"}]
    case["evidence"].extend([
        ev("EV-SYN-VERIFY-STAGE", "synthetic-records.md#verify-stage",
           "Release custodian"),
        ev("EV-SYN-IAM-BACKUP", "synthetic-records.md#iam-backup-interview",
           "Identity and Access team", kind="interview"),
        ev("EV-SYN-ESS-BACKUP", "synthetic-records.md#ess-backup",
           "Enterprise Applications team"),
        ev("EV-SYN-ESS-RESTORE", "synthetic-records.md#ess-restore",
           "Enterprise Applications team"),
        ev("EV-SYN-ESS-DEPVERIFY", "synthetic-records.md#ess-depverify",
           "Enterprise Applications team"),
        ev("EV-SYN-ESS-BIZVERIFY", "synthetic-records.md#ess-bizverify",
           "Enterprise Applications team"),
        ev("EV-SYN-DISRUPT", "synthetic-records.md#disruption",
           "Service operations owner"),
    ])

    # Events: the staging pass, the prod FAILURE, one shared disruption, and the
    # SVC-ESS / SVC-RIS recovery chains.
    keep = {"EVT-SRC-APPROVED", "EVT-BUILD-STARTED", "EVT-BUILD-FINISHED", "EVT-DEPLOY",
            "EVT-RIS-BACKUP"}
    case["events"] = [e for e in case["events"] if e["event_id"] in keep]
    case["events"].extend([
        event("EVT-VERIFY-STAGE", "verification", "2026-09-17T16:00:00Z",
              "EV-SYN-VERIFY-STAGE"),
        # The failed verification the order asks for.
        event("EVT-VERIFY-PROD", "verification", "2026-09-17T22:15:00Z",
              "EV-SYN-VERIFY-PROD"),
        event("EVT-DISRUPT", "disruption", "2026-09-17T22:20:00Z", "EV-SYN-DISRUPT"),
        event("EVT-IAM-BACKUP", "backup_completed", "2026-09-17T20:45:00Z",
              "EV-SYN-IAM-BACKUP"),
        event("EVT-ESS-BACKUP", "backup_completed", "2026-09-17T21:30:00Z",
              "EV-SYN-ESS-BACKUP"),
        event("EVT-ESS-PIT", "restored_data_as_of", "2026-09-17T21:30:00Z",
              "EV-SYN-ESS-RESTORE"),
        event("EVT-ESS-RESTORE", "restore_completed", "2026-09-17T23:10:00Z",
              "EV-SYN-ESS-RESTORE"),
        event("EVT-ESS-DEPVERIFY", "dependency_verification", "2026-09-17T22:55:00Z",
              "EV-SYN-ESS-DEPVERIFY"),
        event("EVT-ESS-BIZVERIFY", "business_verification", "2026-09-17T23:25:00Z",
              "EV-SYN-ESS-BIZVERIFY"),
        event("EVT-RIS-PIT", "restored_data_as_of", "2026-09-17T21:00:00Z",
              "EV-SYN-RIS-RESTORE"),
        event("EVT-RIS-RESTORE", "restore_completed", "2026-09-17T23:40:00Z",
              "EV-SYN-RIS-RESTORE"),
        # UNKNOWN on purpose: the exercise sheet recorded the dependency check but
        # nobody wrote down when. It must stay UNKNOWN and be reported unschedulable.
        event("EVT-RIS-DEPVERIFY", "dependency_verification", None,
              "EV-SYN-RIS-DEPVERIFY"),
    ])
    for e in case["events"]:
        if e["event_id"] == "EVT-RIS-BACKUP":
            e["observed_at"] = "2026-09-17T21:00:00Z"

    # The release went to ess-prod; only ess-stage ever passed.
    case["verifications"] = [
        {"verification_id": "VER-STAGE", "environment": "ess-stage",
         "artifact_version": "fictional-2.3.0", "outcome": "PASSED",
         "performed": ref("EVT-VERIFY-STAGE", "2026-09-17T16:00:00Z"),
         "evidence_id": "EV-SYN-VERIFY-STAGE"},
        {"verification_id": "VER-PROD", "environment": "ess-prod",
         "artifact_version": "fictional-2.3.0", "outcome": "FAILED",
         "performed": ref("EVT-VERIFY-PROD", "2026-09-17T22:15:00Z"),
         "evidence_id": "EV-SYN-VERIFY-PROD"},
    ]

    case["recovery"]["services"] = [
        {   # The strength: a complete evidence chain.
            "service_id": "SVC-ESS", "name": "Synthetic employee self-service",
            "business_function": "An employee can open and submit a self-service request",
            "target_rpo_minutes": 60, "target_rto_minutes": 120,
            "dependencies": ["SVC-IAM"],
            "backup": {"last_successful": ref("EVT-ESS-BACKUP"),
                       "evidence_id": "EV-SYN-ESS-BACKUP"},
            "exercise": {
                "exercise_id": "EX-SYN-ESS-01",
                "disruption": ref("EVT-DISRUPT", "2026-09-17T22:20:00Z"),
                "restored_data_as_of": ref("EVT-ESS-PIT"),
                "restore_completed": ref("EVT-ESS-RESTORE", "2026-09-17T23:10:00Z"),
                "business_verification": ref("EVT-ESS-BIZVERIFY"),
                "dependency_results": [
                    {"dependency_id": "SVC-IAM",
                     "verified": ref("EVT-ESS-DEPVERIFY", "2026-09-17T22:55:00Z"),
                     "evidence_id": "EV-SYN-ESS-DEPVERIFY"},
                ],
            },
        },
        {   # Honest absence: never exercised, and its backup is interview-only.
            "service_id": "SVC-IAM", "name": "Synthetic sign-in",
            "business_function": "Authenticate users to in-scope services",
            "target_rpo_minutes": 60, "target_rto_minutes": 60,
            "dependencies": [],
            "backup": {"last_successful": ref("EVT-IAM-BACKUP"),
                       "evidence_id": "EV-SYN-IAM-BACKUP"},
            "exercise": None,
        },
        {   # The gap: a dependency verification claimed with no observed time.
            "service_id": "SVC-RIS", "name": "Synthetic research submission",
            "business_function": "Submit and route a research administration packet",
            "target_rpo_minutes": 60, "target_rto_minutes": 120,
            "dependencies": ["SVC-ESS"],
            "backup": {"last_successful": ref("EVT-RIS-BACKUP"),
                       "evidence_id": "EV-SYN-RIS-BACKUP"},
            "exercise": {
                "exercise_id": "EX-SYN-RIS-01",
                "disruption": ref("EVT-DISRUPT", "2026-09-17T22:20:00Z"),
                "restored_data_as_of": ref("EVT-RIS-PIT"),
                "restore_completed": ref("EVT-RIS-RESTORE", "2026-09-17T23:40:00Z"),
                "business_verification": None,
                "dependency_results": [
                    {"dependency_id": "SVC-ESS",
                     "verified": ref("EVT-RIS-DEPVERIFY"),
                     "evidence_id": "EV-SYN-RIS-DEPVERIFY"},
                ],
            },
        },
    ]
    return case


# ---------------------------------------------------------------------------
# One mutation per defect class
# ---------------------------------------------------------------------------

def _event(case, event_id):
    for e in case["events"]:
        if e["event_id"] == event_id:
            return e
    raise KeyError(event_id)


def _service(case, service_id):
    for s in case["recovery"]["services"]:
        if s["service_id"] == service_id:
            return s
    raise KeyError(service_id)


def mutate_timeline_disagreement(case):
    """The provenance export's own clock drifts 5 minutes from the shared register."""
    case["case_id"] = "SYN-109-TIMELINE-DISAGREEMENT"
    case["release"]["deployment"]["deployed"]["asserted_at"] = "2026-09-17T22:05:00Z"
    return case


def mutate_unresolved_source_id(case):
    """A recovery record cites a source id that is not in the evidence register."""
    case["case_id"] = "SYN-109-UNRESOLVED-SOURCE-ID"
    _service(case, "SVC-IAM")["backup"]["evidence_id"] = "EV-SYN-NOT-IN-REGISTER"
    return case


def mutate_unsupported_recovery_claim(case):
    """The business function is claimed verified, but no record carries the claim."""
    case["case_id"] = "SYN-109-UNSUPPORTED-RECOVERY-CLAIM"
    _event(case, "EVT-RIS-BIZVERIFY")["evidence_id"] = None
    return case


def mutate_ordering_inversion(case):
    """A restore completes before the disruption that required it."""
    case["case_id"] = "SYN-109-ORDERING-INVERSION"
    _event(case, "EVT-RIS-RESTORE")["observed_at"] = "2026-09-17T22:10:00Z"
    ex = _service(case, "SVC-RIS")["exercise"]
    ex["restore_completed"]["asserted_at"] = "2026-09-17T22:10:00Z"
    return case


def mutate_unknown_timestamp(case):
    """The deployment has no observed time. It must stay UNKNOWN, not default."""
    case["case_id"] = "SYN-109-UNKNOWN-TIMESTAMP"
    _event(case, "EVT-DEPLOY")["observed_at"] = None
    case["release"]["deployment"]["deployed"]["asserted_at"] = None
    return case


def mutate_id_collision(case):
    """One identifier means two different things: an evidence id reuses an event id."""
    case["case_id"] = "SYN-109-ID-COLLISION"
    case["evidence"].append(
        ev("EVT-DEPLOY", "synthetic-records.md#collision", "Service operations owner"))
    return case


def mutate_environment_difference(case):
    """The only passing verification ran somewhere other than where the release ran."""
    case["case_id"] = "SYN-109-ENVIRONMENT-DIFFERENCE"
    case["environments"].append(
        {"environment_id": "ess-stage",
         "purpose": "fictional pre-release verification environment"})
    case["verifications"][0]["environment"] = "ess-stage"
    return case


MUTATIONS = {
    "clean": (lambda c: c, "no mutation -- must come back AGREED with zero findings"),
    "timeline-disagreement": (mutate_timeline_disagreement,
                              "provenance asserts a deploy time 5 minutes off the register"),
    "unresolved-source-id": (mutate_unresolved_source_id,
                             "a backup record cites an evidence id that does not exist"),
    "unsupported-recovery-claim": (mutate_unsupported_recovery_claim,
                                   "business verification claimed with no source record"),
    "ordering-inversion": (mutate_ordering_inversion,
                           "restore completes before the disruption"),
    "unknown-timestamp": (mutate_unknown_timestamp,
                          "the deployment event has no observed time"),
    "id-collision": (mutate_id_collision,
                     "an evidence id reuses an existing event id"),
    "environment-difference": (mutate_environment_difference,
                               "the passing verification ran in another environment"),
}


def write(path, payload):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def main():
    os.makedirs(FIXTURES, exist_ok=True)
    written = [write(os.path.join(HERE, "case.json"), narrative_case())]
    for name, (mutate, _why) in sorted(MUTATIONS.items()):
        written.append(write(os.path.join(FIXTURES, f"{name}.json"),
                             mutate(copy.deepcopy(clean_case()))))
    for path in written:
        print(os.path.relpath(path, HERE))


if __name__ == "__main__":
    main()
