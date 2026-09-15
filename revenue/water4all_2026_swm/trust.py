"""Repository-pinned trust roots for live Water4All readiness decisions.

Caller-supplied values are observations only.  CURRENT authority may only use
records that match these committed registries exactly.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Set, Tuple
from urllib.parse import unquote, urlsplit, urlunsplit

from .common import (
    ReadinessError,
    _HEX40,
    _HEX64,
    _expect_dict,
    _expect_hex,
    _expect_id,
    _expect_int,
    _expect_list,
    _expect_str,
    source_fact_commitment,
    strict_json_loads,
)

_HERE = Path(__file__).resolve().parent
_PARTNER_PATH = re.compile(r"^/water4all/2026/partner-search-entry/[1-9][0-9]*$")
_CONTACT_TOKEN = re.compile(
    r"(?i)(?:mailto:|tel:|sms:|whatsapp:|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})"
)
_PARTNER_KEYS = {
    "profile_id",
    "organization_label",
    "country_code",
    "topic_ids",
    "public_profile_url",
    "public_fit_summary",
    "status",
}


def _load_repo_json(name: str) -> Any:
    path = _HERE / name
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReadinessError("trusted registry unavailable: %s" % name) from exc
    return strict_json_loads(raw)


def trusted_source_registry() -> Dict[str, Dict[str, Any]]:
    rows = _expect_list(_load_repo_json("official_sources.json"), "trusted official source registry")
    out: Dict[str, Dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        path = "trusted official source registry[%d]" % index
        row = _expect_dict(raw, path)
        source_id = _expect_id(row.get("source_id"), path + ".source_id")
        if source_id in out:
            raise ReadinessError("duplicate trusted source_id: %s" % source_id)
        commitment = _expect_hex(row.get("fact_commitment"), path + ".fact_commitment", _HEX64)
        if commitment != source_fact_commitment(row):
            raise ReadinessError("trusted source fact commitment mismatch: %s" % source_id)
        out[source_id] = dict(row)
    if not out:
        raise ReadinessError("trusted official source registry must not be empty")
    return out


def technical_descriptor_key(item: Mapping[str, Any]) -> Tuple[Any, ...]:
    return (
        item["repo_full_name"],
        item["commit_sha"],
        item["path"],
        item["content_sha256"],
        item["publicability"],
        tuple(item["capability_tags"]),
    )


def trusted_technical_descriptor_keys() -> Set[Tuple[Any, ...]]:
    rows = _expect_list(_load_repo_json("trusted_technical_evidence.json"), "trusted technical evidence registry")
    out: Set[Tuple[Any, ...]] = set()
    for index, raw in enumerate(rows):
        path = "trusted technical evidence registry[%d]" % index
        row = _expect_dict(raw, path)
        normalized = {
            "repo_full_name": _expect_str(row.get("repo_full_name"), path + ".repo_full_name"),
            "commit_sha": _expect_hex(row.get("commit_sha"), path + ".commit_sha", _HEX40),
            "path": _expect_str(row.get("path"), path + ".path"),
            "content_sha256": _expect_hex(row.get("content_sha256"), path + ".content_sha256", _HEX64),
            "publicability": _expect_str(row.get("publicability"), path + ".publicability"),
            "capability_tags": sorted(set(_expect_id(v, path + ".capability_tags") for v in _expect_list(row.get("capability_tags"), path + ".capability_tags"))),
        }
        out.add(technical_descriptor_key(normalized))
    return out


def _canonical_https_url(value: Any, path: str) -> str:
    text = _expect_str(value, path)
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in text):
        raise ReadinessError("%s contains a control character" % path)
    try:
        parts = urlsplit(text)
        port = parts.port
    except ValueError as exc:
        raise ReadinessError("%s is not a canonical HTTPS URL" % path) from exc
    if parts.scheme != "https" or not parts.hostname:
        raise ReadinessError("%s must be HTTPS" % path)
    if parts.username is not None or parts.password is not None or port is not None:
        raise ReadinessError("%s must not contain userinfo or an explicit port" % path)
    if parts.query or parts.fragment:
        raise ReadinessError("%s must not contain query or fragment data" % path)
    if unquote(parts.path) != parts.path or "\\" in parts.path:
        raise ReadinessError("%s must not contain encoded or backslash path tricks" % path)
    host = parts.hostname.lower()
    if parts.netloc != host:
        raise ReadinessError("%s host must be canonical lowercase form" % path)
    rebuilt = urlunsplit(("https", host, parts.path, "", ""))
    if rebuilt != text:
        raise ReadinessError("%s is not canonical" % path)
    return text


def trusted_coordinator_pi_evidence() -> List[Dict[str, Any]]:
    rows = _expect_list(_load_repo_json("trusted_coordinator_pi_evidence.json"), "trusted coordinator PI evidence registry")
    out: List[Dict[str, Any]] = []
    for index, raw in enumerate(rows):
        path = "trusted coordinator PI evidence registry[%d]" % index
        row = _expect_dict(raw, path)
        out.append(
            {
                "evidence_id": _expect_id(row.get("evidence_id"), path + ".evidence_id"),
                "coordinator_partner_id": _expect_id(row.get("coordinator_partner_id"), path + ".coordinator_partner_id"),
                "pi_id": _expect_id(row.get("pi_id"), path + ".pi_id"),
                "other_coordinating_proposal_count": _expect_int(row.get("other_coordinating_proposal_count"), path + ".other_coordinating_proposal_count", 0),
                "source_url": _canonical_https_url(row.get("source_url"), path + ".source_url"),
                "content_sha256": _expect_hex(row.get("content_sha256"), path + ".content_sha256", _HEX64),
                "observed_at": _expect_str(row.get("observed_at"), path + ".observed_at"),
            }
        )
    return out


def normalize_coordinator_pi_evidence(raw: Any, path: str) -> Dict[str, Any]:
    row = _expect_dict(raw, path)
    return {
        "evidence_id": _expect_id(row.get("evidence_id"), path + ".evidence_id"),
        "coordinator_partner_id": _expect_id(row.get("coordinator_partner_id"), path + ".coordinator_partner_id"),
        "pi_id": _expect_id(row.get("pi_id"), path + ".pi_id"),
        "other_coordinating_proposal_count": _expect_int(row.get("other_coordinating_proposal_count"), path + ".other_coordinating_proposal_count", 0),
        "source_url": _canonical_https_url(row.get("source_url"), path + ".source_url"),
        "content_sha256": _expect_hex(row.get("content_sha256"), path + ".content_sha256", _HEX64),
        "observed_at": _expect_str(row.get("observed_at"), path + ".observed_at"),
    }


def canonical_partner_profile_url(value: Any, path: str) -> str:
    text = _canonical_https_url(value, path)
    parts = urlsplit(text)
    if parts.hostname != "proposals.etag.ee":
        raise ReadinessError("%s must use proposals.etag.ee" % path)
    if not _PARTNER_PATH.fullmatch(parts.path):
        raise ReadinessError("%s must be a canonical Water4All official partner-profile URL" % path)
    return text


def enforce_partner_research_shape(item: Mapping[str, Any], path: str) -> None:
    extras = sorted(set(item.keys()) - _PARTNER_KEYS)
    missing = sorted(_PARTNER_KEYS - set(item.keys()))
    if extras:
        raise ReadinessError("%s contains forbidden contact/outreach or unsupported keys: %s" % (path, ", ".join(extras)))
    if missing:
        raise ReadinessError("%s is missing required research-only keys: %s" % (path, ", ".join(missing)))
    for key in ("organization_label", "public_fit_summary"):
        value = item.get(key)
        if isinstance(value, str) and _CONTACT_TOKEN.search(value):
            raise ReadinessError("%s.%s contains contact-route semantics" % (path, key))
