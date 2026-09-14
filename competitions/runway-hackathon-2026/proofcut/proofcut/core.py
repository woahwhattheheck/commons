from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_TEXT = 4000
MAX_ITEMS = 128
MAX_JSON_BYTES = 1_000_000
PROMPT_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "developer message",
    "reveal your instructions",
    "follow these instructions",
    "override instructions",
)

class ProofCutError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bounded_text(value: Any, field: str, *, allow_empty: bool = False, max_len: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise ProofCutError(f"{field}: expected string")
    if not allow_empty and not value.strip():
        raise ProofCutError(f"{field}: empty")
    if len(value) > max_len:
        raise ProofCutError(f"{field}: exceeds {max_len} chars")
    if "\x00" in value:
        raise ProofCutError(f"{field}: NUL forbidden")
    return value


def _id(value: Any, field: str) -> str:
    value = _bounded_text(value, field, max_len=64)
    if not ID_RE.fullmatch(value):
        raise ProofCutError(f"{field}: invalid id")
    return value


def _https_url(value: Any, field: str) -> str:
    value = _bounded_text(value, field, max_len=2048)
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ProofCutError(f"{field}: must be a credential-free https URL")
    return value


def _unique_by_id(items: Iterable[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ProofCutError(f"{field}[{i}]: expected object")
        item_id = _id(item.get("id"), f"{field}[{i}].id")
        if item_id in seen:
            raise ProofCutError(f"{field}: duplicate id {item_id}")
        seen.add(item_id)
        out.append(item)
    return out


def _safe_local_relative(value: Any, field: str) -> str:
    value = _bounded_text(value, field, max_len=512)
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ProofCutError(f"{field}: must be relative and traversal-free")
    return p.as_posix()


def validate_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise ProofCutError("packet: expected object")
    raw = canonical_json(packet)
    if len(raw) > MAX_JSON_BYTES:
        raise ProofCutError("packet: too large")
    if packet.get("schema") != "proofcut.evidence.v1":
        raise ProofCutError("schema: expected proofcut.evidence.v1")

    project = packet.get("project")
    if not isinstance(project, dict):
        raise ProofCutError("project: expected object")
    normalized_project = {
        "name": _bounded_text(project.get("name"), "project.name", max_len=120),
        "version": _bounded_text(project.get("version"), "project.version", max_len=80),
        "shipped_url": _https_url(project.get("shipped_url"), "project.shipped_url"),
    }

    evidence = packet.get("evidence", [])
    claims = packet.get("claims", [])
    generative = packet.get("generative_slots", [])
    for name, value in (("evidence", evidence), ("claims", claims), ("generative_slots", generative)):
        if not isinstance(value, list):
            raise ProofCutError(f"{name}: expected list")
        if len(value) > MAX_ITEMS:
            raise ProofCutError(f"{name}: too many items")

    normalized_evidence: list[dict[str, Any]] = []
    evidence_ids: set[str] = set()
    for i, item in enumerate(_unique_by_id(evidence, "evidence")):
        eid = _id(item["id"], f"evidence[{i}].id")
        kind = item.get("kind")
        if kind not in {"screenshot", "test_receipt", "source", "document", "metric"}:
            raise ProofCutError(f"evidence[{i}].kind: unsupported")
        digest = _bounded_text(item.get("sha256"), f"evidence[{i}].sha256", max_len=64)
        if not SHA256_RE.fullmatch(digest):
            raise ProofCutError(f"evidence[{i}].sha256: invalid")
        label = _bounded_text(item.get("label"), f"evidence[{i}].label", max_len=240)
        entry: dict[str, Any] = {"id": eid, "kind": kind, "sha256": digest, "label": label}
        if "url" in item:
            entry["url"] = _https_url(item["url"], f"evidence[{i}].url")
        if "path" in item:
            entry["path"] = _safe_local_relative(item["path"], f"evidence[{i}].path")
        if "url" not in entry and "path" not in entry:
            raise ProofCutError(f"evidence[{i}]: url or path required")
        normalized_evidence.append(entry)
        evidence_ids.add(eid)

    normalized_claims: list[dict[str, Any]] = []
    claim_ids: set[str] = set()
    for i, item in enumerate(_unique_by_id(claims, "claims")):
        cid = _id(item["id"], f"claims[{i}].id")
        text = _bounded_text(item.get("text"), f"claims[{i}].text", max_len=500)
        refs = item.get("evidence_ids")
        if not isinstance(refs, list) or not refs:
            raise ProofCutError(f"claims[{i}].evidence_ids: non-empty list required")
        clean_refs: list[str] = []
        seen_refs: set[str] = set()
        for j, ref in enumerate(refs):
            ref = _id(ref, f"claims[{i}].evidence_ids[{j}]")
            if ref in seen_refs:
                raise ProofCutError(f"claims[{i}].evidence_ids: duplicate {ref}")
            if ref not in evidence_ids:
                raise ProofCutError(f"claims[{i}]: missing evidence {ref}")
            seen_refs.add(ref)
            clean_refs.append(ref)
        normalized_claims.append({"id": cid, "text": text, "evidence_ids": sorted(clean_refs)})
        claim_ids.add(cid)

    normalized_slots: list[dict[str, Any]] = []
    for i, item in enumerate(_unique_by_id(generative, "generative_slots")):
        sid = _id(item["id"], f"generative_slots[{i}].id")
        purpose = _bounded_text(item.get("purpose"), f"generative_slots[{i}].purpose", max_len=240)
        prompt = _bounded_text(item.get("prompt"), f"generative_slots[{i}].prompt", max_len=1200)
        lowered = prompt.casefold()
        if any(marker in lowered for marker in PROMPT_INJECTION_MARKERS):
            raise ProofCutError(f"generative_slots[{i}].prompt: instruction-injection marker rejected")
        duration = item.get("duration_seconds")
        if not isinstance(duration, int) or isinstance(duration, bool) or not 2 <= duration <= 30:
            raise ProofCutError(f"generative_slots[{i}].duration_seconds: expected integer 2..30")
        forbidden_claims = item.get("claim_ids", [])
        if forbidden_claims not in ([], None):
            raise ProofCutError(f"generative_slots[{i}].claim_ids: generated media cannot satisfy factual claims")
        normalized_slots.append({
            "id": sid,
            "purpose": purpose,
            "prompt": prompt,
            "duration_seconds": duration,
        })

    return {
        "schema": "proofcut.evidence.v1",
        "project": normalized_project,
        "evidence": sorted(normalized_evidence, key=lambda x: x["id"]),
        "claims": sorted(normalized_claims, key=lambda x: x["id"]),
        "generative_slots": sorted(normalized_slots, key=lambda x: x["id"]),
    }


def verify_local_evidence(packet: dict[str, Any], base_dir: Path) -> list[dict[str, str]]:
    """Verify every local-path evidence item against its declared SHA-256.

    URL evidence is intentionally not fetched: network retrieval is a separate acquisition step.
    Local files, however, fail closed on absence, traversal, size, or digest mismatch.
    """
    p = validate_packet(packet)
    root = base_dir.resolve()
    receipts: list[dict[str, str]] = []
    for item in p["evidence"]:
        rel = item.get("path")
        if rel is None:
            continue
        target = (root / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ProofCutError(f"evidence {item['id']}: resolved path escapes base") from exc
        if not target.is_file():
            raise ProofCutError(f"evidence {item['id']}: local file missing")
        if target.stat().st_size > 32_000_000:
            raise ProofCutError(f"evidence {item['id']}: local file exceeds 32MB")
        actual = sha256_bytes(target.read_bytes())
        if actual != item["sha256"]:
            raise ProofCutError(f"evidence {item['id']}: digest mismatch")
        receipts.append({"id": item["id"], "sha256": actual, "path": rel})
    return receipts


def compile_manifest(packet: dict[str, Any]) -> dict[str, Any]:
    p = validate_packet(packet)
    shots: list[dict[str, Any]] = []
    evidence_by_id = {e["id"]: e for e in p["evidence"]}
    for claim in p["claims"]:
        shots.append({
            "id": f"fact-{claim['id']}",
            "type": "factual",
            "claim_id": claim["id"],
            "caption": claim["text"],
            "evidence": [evidence_by_id[x] for x in claim["evidence_ids"]],
            "provenance": "evidence-bound",
        })
    for slot in p["generative_slots"]:
        shots.append({
            "id": f"gen-{slot['id']}",
            "type": "generated",
            "purpose": slot["purpose"],
            "prompt": slot["prompt"],
            "duration_seconds": slot["duration_seconds"],
            "provenance": "runway-generated-connective-only",
            "status": "HOLD_PROVIDER",
        })
    core = {
        "schema": "proofcut.manifest.v1",
        "project": p["project"],
        "shots": shots,
        "rules": {
            "generated_media_may_satisfy_factual_claims": False,
            "evidence_text_injected_into_generation_prompts": False,
        },
        "source_packet_sha256": sha256_bytes(canonical_json(p)),
    }
    return {**core, "manifest_sha256": sha256_bytes(canonical_json(core))}


def verify_manifest(packet: dict[str, Any], manifest: dict[str, Any]) -> bool:
    return compile_manifest(packet) == manifest
