from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

AWS_PLAN_SCHEMA = "opencv26-visual-evidence-aws-plan/v1"


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    return hashlib.sha256(payload).hexdigest()


def inactive_aws_plan() -> dict[str, Any]:
    """Describe a meaningful AWS execution boundary without claiming deployment.

    The source carrier deliberately performs no AWS SDK calls. A later owner-run
    deployment can bind real provider evidence to this plan without changing the
    visual-decision semantics.
    """
    plan: dict[str, Any] = {
        "schema": AWS_PLAN_SCHEMA,
        "status": "DESIGN_ONLY_NOT_DEPLOYED",
        "components": [
            {
                "service": "Amazon S3",
                "purpose": "rights-cleared input object and immutable trace artifact storage",
                "network_action_in_source": False,
            },
            {
                "service": "AWS Lambda container image",
                "purpose": "OpenCV 5 perception + deterministic policy execution",
                "network_action_in_source": False,
            },
            {
                "service": "Amazon CloudWatch",
                "purpose": "latency, HOLD reason, and human-control observability",
                "network_action_in_source": False,
            },
        ],
        "required_provider_evidence_for_deployed_claim": [
            "exact AWS account-scoped deployment receipt",
            "Lambda image digest containing OpenCV 5+",
            "CloudWatch execution evidence for the same artifact generation",
        ],
        "aws_deployment_verified": False,
        "aws_spend_authorized": False,
        "provider_mutation_authorized": False,
    }
    plan["plan_sha256"] = _digest(plan)
    return plan


def deployment_claim_is_admissible(plan: Mapping[str, Any], provider_evidence: Mapping[str, Any] | None) -> bool:
    """Fail closed until a future provider-authenticated integration is reviewed."""
    if dict(plan) != inactive_aws_plan():
        return False
    _ = provider_evidence
    return False
