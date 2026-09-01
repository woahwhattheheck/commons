"""Eight-stage ChartTrace internal review pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

from charttrace.review.dispositions import Disposition, DispositionRecord
from charttrace.review.pipeline_stages import (
    PACKET_SECTION_ORDER,
    STAGE_NAMES,
    StageResult,
    stage_break_the_packet,
    stage_clinical_seriousness,
    stage_discovery_input,
    stage_hostile_audit,
    stage_named_human_release,
    stage_preflight,
    stage_privacy_format_lint,
    stage_synthesis_dedup,
)

STAGE_RUNNERS: Dict[str, Callable[[Dict[str, Any]], StageResult]] = {
    "preflight": stage_preflight,
    "discovery_input": stage_discovery_input,
    "synthesis_dedup": stage_synthesis_dedup,
    "hostile_audit": stage_hostile_audit,
    "clinical_seriousness": stage_clinical_seriousness,
    "break_the_packet": stage_break_the_packet,
    "privacy_format_lint": stage_privacy_format_lint,
    "named_human_release": stage_named_human_release,
}


@dataclass
class ReviewResult:
    ok: bool
    stages: List[StageResult]
    dispositions: List[DispositionRecord]
    release_blocked: bool
    quarantine_ids: List[str]
    appendix_ids: List[str]
    packet_sections: Dict[str, List[Dict[str, Any]]]
    schema_version: str = "charttrace.review.v1"
    grounding_version: str = "charttrace.review.grounding.v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "release_blocked": self.release_blocked,
            "schema_version": self.schema_version,
            "grounding_version": self.grounding_version,
            "stages": [s.to_dict() for s in self.stages],
            "dispositions": [d.to_dict() for d in self.dispositions],
            "quarantine_ids": list(self.quarantine_ids),
            "appendix_ids": list(self.appendix_ids),
            "packet_sections": {k: list(v) for k, v in self.packet_sections.items()},
        }


class ReviewPipeline:
    """Deterministic eight-stage internal review pipeline."""

    def __init__(self, stages: Optional[Sequence[str]] = None) -> None:
        self.stages = list(stages or STAGE_NAMES)

    def run(self, packet: Dict[str, Any]) -> ReviewResult:
        stage_results: List[StageResult] = []
        all_dispositions: List[DispositionRecord] = []

        for name in self.stages:
            result = STAGE_RUNNERS[name](packet)
            stage_results.append(result)
            all_dispositions.extend(result.dispositions)

        quarantine_ids = sorted(
            {
                d.item_id
                for d in all_dispositions
                if d.disposition == Disposition.REJECT_UNSUPPORTED
                and not d.leaves_packet
            }
        )
        appendix_ids = sorted(
            {
                d.item_id
                for d in all_dispositions
                if d.disposition == Disposition.WEAK_APPENDIX
            }
        )
        merge_map = {
            d.item_id: d.merge_target_id
            for d in all_dispositions
            if d.disposition == Disposition.MERGE_DUPLICATE
        }
        hold_or_repair = any(
            d.disposition in (Disposition.HOLD, Disposition.REPAIR)
            for d in all_dispositions
        )
        gate_names = {
            "preflight",
            "discovery_input",
            "break_the_packet",
            "privacy_format_lint",
            "named_human_release",
        }
        gates_ok = all(s.ok for s in stage_results if s.name in gate_names)
        release_blocked = (not gates_ok) or hold_or_repair

        leads = list(packet.get("leads") or [])
        by_id = {str(l.get("lead_id")): l for l in leads}
        surviving = [
            l
            for l in leads
            if str(l.get("lead_id")) not in quarantine_ids
            and str(l.get("lead_id")) not in merge_map
        ]

        strongest = [
            l
            for l in surviving
            if l.get("band") == "primary"
            and str(l.get("lead_id")) not in appendix_ids
            and l.get("evidence_grade") in ("EXPLICIT", "CORROBORATED", "SUPPORTED")
        ]
        secondary = [
            l
            for l in surviving
            if l.get("band") == "secondary" and str(l.get("lead_id")) not in appendix_ids
        ]
        weak_appendix = [
            l
            for l in surviving
            if str(l.get("lead_id")) in appendix_ids or l.get("band") == "weak"
        ]
        for aid in appendix_ids:
            if (
                aid in by_id
                and by_id[aid] not in weak_appendix
                and aid not in quarantine_ids
            ):
                weak_appendix.append(by_id[aid])

        counter = list(packet.get("counterevidence") or [])
        for l in surviving:
            for c in l.get("counterevidence") or []:
                if isinstance(c, dict):
                    counter.append(c)
                else:
                    counter.append({"lead_id": l.get("lead_id"), "text": c})
        missing = list(packet.get("missing_record_requests") or [])
        for l in surviving:
            missing.extend(l.get("missing_records") or [])
        chronology = list(packet.get("chronology") or [])
        citation_index = list(packet.get("citation_index") or [])

        sections = {
            "strongest_grounded_patterns": strongest,
            "secondary_findings": secondary,
            "weak_lead_appendix": weak_appendix,
            "counterevidence_alternatives": counter,
            "missing_record_requests": missing,
            "chronology_citation_index": chronology + citation_index,
        }
        assert list(sections.keys()) == list(PACKET_SECTION_ORDER)

        ok = gates_ok and not release_blocked
        return ReviewResult(
            ok=ok,
            stages=stage_results,
            dispositions=all_dispositions,
            release_blocked=release_blocked,
            quarantine_ids=quarantine_ids,
            appendix_ids=appendix_ids,
            packet_sections=sections,
        )
