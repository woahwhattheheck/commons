"""Recorded provider evidence, independent of caller-authored receipt fields.

This is a historical evidence catalogue, not a signature or live CI attestation.
The entries were retrieved through GitHub's connected Actions API and the archive
SHA-256 was checked against GitHub's artifact metadata. Adding an entry requires
that same independent retrieval and source review; the producer cannot enroll it.
The installed, reviewed verifier source is trusted. Arbitrary mutation of Python
code or its process is outside this data-validation contract.
"""
from __future__ import annotations

from typing import Any
from evidence_contract import EvidenceError, canonical_sha256

# Full canonical JSON hashes INCLUDING receiptSha256. These are also the raw
# SHA-256 hashes of the unchanged JSON members in the retrieved archive.
_RECORDED_RECEIPTS = (
    ("serial_v1", "74ec227c9673c09b26b0f00a6cbb975b67fb3b241a1b237628c96fa8cf8f0c3b"),
    ("vectorized_v2", "8a46fca8106e6113a725919efecefe5b1dd1508bcbca80b82f6c297bd937dcbc"),
)


def recorded_provenance(receipt: dict[str, Any]) -> dict[str, Any]:
    """Match the entire supplied receipt to independently recorded exact content.

    There is deliberately no caller-provided registry, approval boolean, signing
    key, environment override, or registration API. Reusing the real receipt is
    valid historical evidence; changing any value requires a different record.
    """
    if not isinstance(receipt, dict) or not isinstance(receipt.get("candidate"), dict):
        raise EvidenceError("receipt candidate must be an object")
    try:
        digest = canonical_sha256(receipt)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError("receipt must be JSON") from exc
    label = receipt["candidate"].get("label")
    if not any(label == name and digest == expected for name, expected in _RECORDED_RECEIPTS):
        raise EvidenceError("measurement provenance unrecorded; self-hash proves content integrity only")
    return {
        "kind": "RECORDED_GITHUB_ACTIONS_ARTIFACT",
        "historicalEvidence": True,
        "liveCiStatusAttested": False,
        "cryptographicExecutionAttestation": False,
        "repository": "woahwhattheheck/commons",
        "runId": "34938483198",
        "runAttempt": "1",
        "jobId": "104281505774",
        "jobName": "public-development-evidence",
        "observedConclusion": "success",
        "headSha": "36be284452141d26cdff4b74efb8f185b27c4b32",
        "checkoutSha": "a1e6c04b5b73accfe930567b99f094db076b82bc",
        "workflowPath": ".github/workflows/learn2design-public-evidence.yml",
        "workflowGitBlobSha1": "448315c9722dc08c325076bc33a1baab5c886743",
        "artifactId": "10384626623",
        "artifactSha256": "e9a57d1e87adfad905b5617e8b987545a346f461052a2c8d633db310649a3bcb",
        "artifactCreatedAt": "2026-09-15T06:53:43Z",
        "artifactExpiresAt": "2026-09-29T06:53:43Z",
        "receiptCanonicalSha256": digest,
    }
