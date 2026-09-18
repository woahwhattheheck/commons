"""Migration donor for provider-cost gates; does not mutate active provider-cost code."""
from __future__ import annotations
from typing import Any, Mapping
from .codec import AuthorityError
from .core import compile_current

def compile_provider_cost_authority(candidate:Any,manifest_bytes:bytes,sources:Mapping[str,bytes],pinned_root_sha256:str)->dict[str,Any]:
    """Return a source-bound provider fact suitable for a downstream adapter.

    Downstream code must consume this derived receipt/fact rather than accepting
    a caller-authored ``authority='PROVIDER_AUTHENTICATED'`` string.
    """
    receipt=compile_current(candidate,manifest_bytes,sources,pinned_root_sha256)
    fact=receipt.get("authority_fact")
    if not receipt.get("current_authority") or not isinstance(fact,dict) or fact.get("authority_class")!="PROVIDER_AUTHENTICATED":
        return {"provider_authenticated":False,"authority_receipt_sha256":receipt["receipt_sha256"],"external_side_effects_authorized":False}
    return {
        "provider_authenticated":True,"record_id":fact["record_id"],"issuer":fact["issuer"],"subject":fact["subject"],
        "claim_kind":fact["claim_kind"],"scope":fact["scope"],"generation":fact["generation"],
        "claim_payload_sha256":fact["claim_payload_sha256"],"source_sha256":fact["source_sha256"],
        "authority_receipt_sha256":receipt["receipt_sha256"],"external_side_effects_authorized":False,
    }
