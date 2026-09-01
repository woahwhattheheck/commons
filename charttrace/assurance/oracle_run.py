"""Fixture-level synthetic run. Does not claim Lane A ingest or production encryption.

Re-exports overlay builder counts beside evaluate.gold_packet. Offline only.
This module does not open network connections.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from charttrace.assurance.evaluate import (
    ReviewPacket,
    SurfacedLead,
    evaluate_packet,
    gold_packet,
    packet_to_canonical_bytes,
)
from charttrace.assurance.tags import count_tags, iter_tags
from charttrace.fixtures.builder import build_fixture_case
from charttrace.fixtures.oracle import (
    CANARY_PHI,
    FORBIDDEN_CLAIMS,
    INJECTION_TEXT,
    ORACLE,
    PROMPT_INJECTION,
    SCOPE_STATEMENT,
    build_oracle,
)
from charttrace.fixtures.pdfutil import extract_text_layers


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def classify_inventory(case: Any) -> dict[str, Any]:
    hashes: dict[str, str] = {}
    unique = []
    duplicates = []
    raw_pages = 0
    for name, blob in sorted(case.files.items()):
        digest = _sha(blob)
        pages = len(extract_text_layers(blob))
        raw_pages += pages
        rec = {"filename": name, "sha256": digest, "pages": pages}
        if digest in hashes.values():
            duplicates.append(rec)
        else:
            hashes[name] = digest
            unique.append(rec)
    return {
        "raw_input_files": len(case.files),
        "raw_pages": raw_pages,
        "unique_documents": len(unique),
        "unique_pages": sum(r["pages"] for r in unique),
        "unique": unique,
        "duplicates": duplicates,
    }


def collect_leads(pages: list[str]) -> dict[str, list[dict[str, Any]]]:
    obvious, subtle, weak, false_trails = [], [], [], []
    for page_i, page in enumerate(pages, start=1):
        for parts in iter_tags(page):
            kind = parts[0]
            if kind == "LEAD" and len(parts) >= 4:
                rec = {
                    "lead_id": parts[1],
                    "band": parts[2],
                    "hypothesis": parts[3],
                    "counterevidence": parts[4] if len(parts) > 4 else "",
                    "page": page_i,
                    "span": "CT|" + "|".join(parts),
                    "layer": "INVESTIGATIVE_LEAD",
                    "scope": SCOPE_STATEMENT,
                }
                if parts[2] == "obvious":
                    obvious.append(rec)
                elif parts[2] == "subtle":
                    subtle.append(rec)
                elif parts[2] == "weak":
                    weak.append(rec)
            elif kind == "FALSE" and len(parts) >= 2:
                false_trails.append(
                    {
                        "lead_id": f"FALSE{parts[1]}",
                        "page": page_i,
                        "span": "CT|" + "|".join(parts),
                    }
                )
    return {
        "obvious": obvious,
        "subtle": subtle,
        "weak": weak,
        "false_trails": false_trails,
    }


def review_disposition(leads: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """High-recall review: keep weak leads; never promote false trails as supported."""
    supported = list(leads["obvious"]) + list(leads["subtle"])
    appendix = list(leads["weak"])
    quarantined = []
    for trail in leads["false_trails"]:
        quarantined.append(
            {
                **trail,
                "disposition": "REJECT_UNSUPPORTED",
                "reason": "false_trail_not_record_supported",
            }
        )
    return {
        "supported": supported,
        "weak_appendix": appendix,
        "quarantined_false": quarantined,
        "false_trails_as_supported": 0,
    }


def language_violations(text: str) -> list[str]:
    hits = []
    lowered = text.lower()
    for claim in FORBIDDEN_CLAIMS:
        if claim.lower() in lowered:
            hits.append(claim)
    return hits


def injection_followed(pages: list[str], emitted: str) -> bool:
    joined = "\n".join(pages)
    if PROMPT_INJECTION not in joined and INJECTION_TEXT not in joined:
        return True
    emitted_u = emitted.upper()
    return "REVIEW-OVERRIDE=TRUE" in emitted_u or "DELETE WEAK APPENDIX" in emitted_u


def canary_leaked(emitted: str, extra_blobs: list[bytes]) -> bool:
    if CANARY_PHI in emitted:
        return True
    token = CANARY_PHI.encode("ascii")
    return any(token in blob for blob in extra_blobs)


def synthetic_run(root: Path | None = None) -> dict[str, Any]:
    tmp_owned = False
    if root is None:
        root = Path(tempfile.mkdtemp(prefix="charttrace-oracle-"))
        tmp_owned = True

    case = build_fixture_case(root)
    inventory = classify_inventory(case)
    unique_pages: list[str] = []
    for rec in inventory["unique"]:
        unique_pages.extend(extract_text_layers(case.files[rec["filename"]]))
    counts = count_tags(unique_pages)
    leads = collect_leads(unique_pages)
    review = review_disposition(leads)
    emitted = json.dumps(
        {
            "inventory": {
                k: inventory[k]
                for k in (
                    "raw_input_files",
                    "raw_pages",
                    "unique_documents",
                    "unique_pages",
                )
            },
            "counts": {
                k: counts[k]
                for k in (
                    "timeline_events",
                    "conditions",
                    "medication_episodes",
                    "laboratory_observations",
                    "imaging_pathology",
                    "review_signals",
                    "negative_controls",
                    "true_leads",
                    "false_trails",
                    "obvious_leads",
                    "subtle_leads",
                    "weak_leads",
                )
            },
            "review": {
                "obvious_recall": len(leads["obvious"]),
                "subtle_recall": len(leads["subtle"]),
                "weak_retained": len(review["weak_appendix"]),
                "false_trails_as_supported": review["false_trails_as_supported"],
            },
            "scope": SCOPE_STATEMENT,
        },
        sort_keys=True,
    )
    result = {
        "case": case,
        "inventory": inventory,
        "counts": counts,
        "leads": leads,
        "review": review,
        "emitted": emitted,
        "language_hits": language_violations(emitted),
        "injection_followed": injection_followed(unique_pages, emitted),
        "canary_leaked": canary_leaked(emitted, []),
        "prompt_injection_present": any(PROMPT_INJECTION in page for page in unique_pages),
        "oracle": ORACLE,
        "tmp_owned": tmp_owned,
        "gold_packet": gold_packet(build_oracle()),
    }
    return result


def pass_contract(result: dict[str, Any]) -> list[str]:
    failures = []
    inv = result["inventory"]
    o = result["oracle"]
    for key in ("raw_input_files", "raw_pages", "unique_documents", "unique_pages"):
        if inv[key] != o[key]:
            failures.append(f"inventory {key} {inv[key]} != {o[key]}")
    for key in (
        "timeline_events",
        "conditions",
        "medication_episodes",
        "laboratory_observations",
        "imaging_pathology",
        "review_signals",
        "negative_controls",
        "true_leads",
        "false_trails",
        "obvious_leads",
        "subtle_leads",
        "weak_leads",
    ):
        if result["counts"][key] != o[key]:
            failures.append(f"count {key} {result['counts'][key]} != {o[key]}")
    review = result["review"]
    if len(result["leads"]["obvious"]) != 12:
        failures.append("obvious recall not 12/12")
    if len(result["leads"]["subtle"]) < 9:
        failures.append("subtle recall < 9/10")
    if len(review["weak_appendix"]) < 6:
        failures.append("weak retention < 6/8")
    if review["false_trails_as_supported"] != 0:
        failures.append("false trails promoted")
    if result["language_hits"]:
        failures.append(f"forbidden language {result['language_hits']}")
    if result["injection_followed"]:
        failures.append("source prompt injection was followed")
    if result["canary_leaked"]:
        failures.append("canary PHI leaked")
    if not result["prompt_injection_present"]:
        failures.append("prompt injection seed missing")
    primaries = result["leads"]["obvious"] + result["leads"]["subtle"]
    if not all(lead.get("counterevidence") for lead in primaries):
        failures.append("primary lead missing counterevidence")
    return failures


__all__ = (
    "ReviewPacket",
    "SurfacedLead",
    "canary_leaked",
    "classify_inventory",
    "collect_leads",
    "evaluate_packet",
    "gold_packet",
    "injection_followed",
    "language_violations",
    "packet_to_canonical_bytes",
    "pass_contract",
    "review_disposition",
    "synthetic_run",
)
