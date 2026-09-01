"""Early-stage implementations for ChartTrace Lane D review pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from charttrace.review.dispositions import (
    Disposition,
    DispositionRecord,
    apply_disposition,
)
from charttrace.review.hard_failures import audit_leads
from charttrace.review.language_lint import lint_packet_texts

STAGE_NAMES: Tuple[str, ...] = (
    "preflight",
    "discovery_input",
    "synthesis_dedup",
    "hostile_audit",
    "clinical_seriousness",
    "break_the_packet",
    "privacy_format_lint",
    "named_human_release",
)

PACKET_SECTION_ORDER: Tuple[str, ...] = (
    "strongest_grounded_patterns",
    "secondary_findings",
    "weak_lead_appendix",
    "counterevidence_alternatives",
    "missing_record_requests",
    "chronology_citation_index",
)


@dataclass
class StageResult:
    name: str
    ok: bool
    notes: List[str] = field(default_factory=list)
    dispositions: List[DispositionRecord] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "notes": list(self.notes),
            "dispositions": [d.to_dict() for d in self.dispositions],
            "details": dict(self.details),
        }


def stage_preflight(packet: Dict[str, Any]) -> StageResult:
    notes: List[str] = []
    ok = True
    sources = packet.get("sources") or []
    if not sources:
        ok = False
        notes.append("No sources in packet")
    for src in sources:
        sid = src.get("source_id") or src.get("id") or "?"
        digest = src.get("sha256") or src.get("hash")
        if not digest or len(str(digest)) < 32:
            ok = False
            notes.append(f"Missing/short hash for source {sid}")
        if src.get("tampered"):
            ok = False
            notes.append(f"Tamper flag on source {sid}")
        pages = src.get("pages")
        if pages is not None and int(pages) <= 0:
            ok = False
            notes.append(f"Invalid page count for source {sid}")
        ocr = src.get("ocr")
        if isinstance(ocr, dict) and ocr.get("status") == "failed":
            ok = False
            notes.append(f"OCR failed for source {sid}")
        if src.get("provenance_incomplete"):
            ok = False
            notes.append(f"Incomplete provenance for source {sid}")
    return StageResult(
        name="preflight", ok=ok, notes=notes, details={"source_count": len(sources)}
    )


def stage_discovery_input(packet: Dict[str, Any]) -> StageResult:
    notes: List[str] = []
    ok = True
    discovery = packet.get("discovery") or {}
    peer_runs = discovery.get("peer_runs") or packet.get("peer_runs") or []
    if len(peer_runs) < 1:
        ok = False
        notes.append("No independent peer discovery runs present")
    forbidden_keys = {"price", "destination_firm", "affiliate_id", "compensation"}
    for run in peer_runs:
        inputs = set((run.get("inputs") or {}).keys())
        leaked = inputs & forbidden_keys
        if leaked:
            ok = False
            notes.append(
                f"Peer run {run.get('peer_id')} has forbidden inputs: {sorted(leaked)}"
            )
        if run.get("anchored_to_peer"):
            notes.append(
                f"Peer {run.get('peer_id')} anchored to another peer — independence weakened"
            )
    leads = packet.get("leads") or []
    if not leads:
        notes.append("Discovery produced zero leads (allowed but unusual)")
    return StageResult(
        name="discovery_input",
        ok=ok,
        notes=notes,
        details={"peer_run_count": len(peer_runs), "lead_count": len(leads)},
    )


def stage_synthesis_dedup(packet: Dict[str, Any]) -> StageResult:
    notes: List[str] = []
    dispositions: List[DispositionRecord] = []
    leads: List[Dict[str, Any]] = list(packet.get("leads") or [])
    by_fingerprint: Dict[str, List[Dict[str, Any]]] = {}
    for lead in leads:
        fp = str(
            lead.get("dedup_key")
            or lead.get("fingerprint")
            or (
                (lead.get("title") or "").strip().lower()
                + "|"
                + (lead.get("domain") or "").strip().lower()
            )
        )
        by_fingerprint.setdefault(fp, []).append(lead)

    dissent_preserved = 0
    for _fp, group in by_fingerprint.items():
        if len(group) < 2:
            continue
        primary = group[0]
        for other in group[1:]:
            if other.get("hypothesis") and other.get("hypothesis") != primary.get(
                "hypothesis"
            ):
                dissent_preserved += 1
                notes.append(
                    f"Preserved dissent from {other.get('lead_id')} vs {primary.get('lead_id')}"
                )
                dispositions.append(
                    apply_disposition(
                        str(other.get("lead_id")),
                        Disposition.WEAK_APPENDIX,
                        "synthesis_dedup",
                        "Deduped peer dissent retained as labeled weak/alternate lead",
                        defect_codes=["DEDUP_DISSENT"],
                    )
                )
            else:
                dispositions.append(
                    apply_disposition(
                        str(other.get("lead_id")),
                        Disposition.MERGE_DUPLICATE,
                        "synthesis_dedup",
                        "Merged duplicate lead",
                        merge_target_id=str(primary.get("lead_id")),
                    )
                )
    return StageResult(
        name="synthesis_dedup",
        ok=True,
        notes=notes,
        dispositions=dispositions,
        details={
            "dissent_preserved": dissent_preserved,
            "group_count": len(by_fingerprint),
        },
    )
