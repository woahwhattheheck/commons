"""Later-stage implementations for ChartTrace Lane D review pipeline."""

from __future__ import annotations

from typing import Any, Dict, List

from charttrace.review.dispositions import (
    Disposition,
    DispositionRecord,
    apply_disposition,
)
from charttrace.review.hard_failures import audit_leads
from charttrace.review.language_lint import lint_packet_texts
from charttrace.review.pipeline_stages_core import StageResult


def stage_hostile_audit(packet: Dict[str, Any]) -> StageResult:
    leads = list(packet.get("leads") or [])
    report = audit_leads(leads, stage="hostile_audit")
    dispositions: List[DispositionRecord] = []
    notes: List[str] = []
    failed_ids = {f.item_id for f in report.failures}
    for fail in report.failures:
        dispositions.append(
            apply_disposition(
                fail.item_id,
                Disposition.REJECT_UNSUPPORTED,
                "hostile_audit",
                fail.detail,
                defect_codes=[fail.code],
                audit_notes="Quarantined internally; must not leave packet",
            )
        )
        notes.append(f"{fail.code}:{fail.item_id}")

    for lead in leads:
        if lead.get("reject_reason_only"):
            reason = str(lead.get("reject_reason_only"))
            try:
                apply_disposition(
                    str(lead.get("lead_id")),
                    Disposition.REJECT_UNSUPPORTED,
                    "hostile_audit",
                    reason,
                )
            except ValueError as exc:
                notes.append(str(exc))
                if lead.get("grounded"):
                    dispositions.append(
                        apply_disposition(
                            str(lead.get("lead_id")),
                            Disposition.WEAK_APPENDIX,
                            "hostile_audit",
                            "Soft rejection blocked; grounded weak lead retained in appendix",
                            defect_codes=["SOFT_REJECTION_BLOCKED"],
                        )
                    )
    return StageResult(
        name="hostile_audit",
        ok=report.ok,
        notes=notes,
        dispositions=dispositions,
        details={"hard_failures": report.to_dict(), "failed_ids": sorted(failed_ids)},
    )


def stage_clinical_seriousness(packet: Dict[str, Any]) -> StageResult:
    notes: List[str] = []
    dispositions: List[DispositionRecord] = []
    ok = True
    for lead in packet.get("leads") or []:
        lid = str(lead.get("lead_id"))
        issues = []
        for key in (
            "anatomy_mismatch",
            "physiology_implausible",
            "dose_route_timing_error",
            "specialty_care_date_misfit",
            "reference_range_error",
        ):
            if lead.get(key):
                issues.append(key)
        if issues:
            ok = False
            dispositions.append(
                apply_disposition(
                    lid,
                    Disposition.REPAIR,
                    "clinical_seriousness",
                    "Clinical seriousness defects require repair",
                    defect_codes=issues,
                )
            )
            notes.append(f"{lid}:{','.join(issues)}")
        elif not lead.get("alternative_explanations"):
            if lead.get("band") in ("primary", "secondary"):
                dispositions.append(
                    apply_disposition(
                        lid,
                        Disposition.DOWNGRADE,
                        "clinical_seriousness",
                        "Missing alternative explanations; downgraded pending enrichment",
                        defect_codes=["MISSING_ALTERNATIVES"],
                    )
                )
                notes.append(f"{lid}:missing_alternatives→DOWNGRADE")
    return StageResult(
        name="clinical_seriousness",
        ok=ok,
        notes=notes,
        dispositions=dispositions,
    )


def stage_break_the_packet(packet: Dict[str, Any]) -> StageResult:
    notes: List[str] = []
    dispositions: List[DispositionRecord] = []
    ok = True
    adversarial = packet.get("adversarial") or {}
    attacks = adversarial.get("attacks") or packet.get("break_attempts") or []
    for attack in attacks:
        kind = attack.get("kind")
        lid = str(attack.get("lead_id") or attack.get("target_id") or "packet")
        if kind == "prompt_injection" and attack.get("followed"):
            ok = False
            dispositions.append(
                apply_disposition(
                    lid,
                    Disposition.REJECT_UNSUPPORTED,
                    "break_the_packet",
                    "Source prompt injection was followed",
                    defect_codes=["SOURCE_PROMPT_INJECTION_FOLLOWED"],
                )
            )
            notes.append(f"prompt_injection_followed:{lid}")
        elif kind == "page_jump" and attack.get("broken"):
            ok = False
            dispositions.append(
                apply_disposition(
                    lid,
                    Disposition.REPAIR,
                    "break_the_packet",
                    "Broken page jump detected under adversarial review",
                    defect_codes=["BROKEN_TABLE_OR_PAGE_JUMP"],
                )
            )
        elif kind == "hash_swap" and attack.get("detected"):
            ok = False
            notes.append("hash_swap detected — HOLD")
            dispositions.append(
                apply_disposition(
                    lid,
                    Disposition.HOLD,
                    "break_the_packet",
                    "Source hash swap detected",
                    defect_codes=["SOURCE_TAMPER"],
                )
            )
        elif kind == "false_trail_as_supported" and attack.get("presented_as_supported"):
            ok = False
            dispositions.append(
                apply_disposition(
                    lid,
                    Disposition.REJECT_UNSUPPORTED,
                    "break_the_packet",
                    "False trail presented as supported conclusion",
                    defect_codes=["UNSUPPORTED_FACT"],
                )
            )
    if not packet.get("counterevidence") and not any(
        (lead.get("counterevidence") for lead in (packet.get("leads") or []))
    ):
        notes.append("No counterevidence channel present on packet/leads")
    return StageResult(
        name="break_the_packet",
        ok=ok,
        notes=notes,
        dispositions=dispositions,
        details={"attack_count": len(attacks)},
    )


def stage_privacy_format_lint(packet: Dict[str, Any]) -> StageResult:
    notes: List[str] = []
    dispositions: List[DispositionRecord] = []
    ok = True
    recipient = packet.get("recipient") or {}
    if not recipient.get("recipient_id"):
        ok = False
        notes.append("Missing recipient_id")
    if recipient.get("authorization_state") not in (
        "TRANSFER_AUTHORIZED",
        "authorized",
        True,
    ):
        ok = False
        notes.append("Recipient transfer not authorized")
    if packet.get("contains_phi_marker"):
        ok = False
        notes.append("PHI marker present — fail closed for synthetic/export lint")
    lang = lint_packet_texts(list(packet.get("leads") or []))
    if not lang.ok:
        ok = False
        for issue in lang.issues:
            dispositions.append(
                apply_disposition(
                    issue.item_id,
                    Disposition.REPAIR,
                    "privacy_format_lint",
                    f"Forbidden/unbounded language: {issue.phrase}",
                    defect_codes=["LANGUAGE_LINT"],
                    audit_notes=issue.suggestion,
                )
            )
        notes.append(f"language_issues={len(lang.issues)}")
    fmt = packet.get("format") or {}
    if fmt.get("broken_table"):
        ok = False
        notes.append("Broken table formatting")
    if (fmt.get("accessibility") or {}).get("missing_alt_text"):
        notes.append("Accessibility: missing alt text on figures")
        dispositions.append(
            apply_disposition(
                "packet",
                Disposition.REPAIR,
                "privacy_format_lint",
                "Accessibility defect: missing alt text",
                defect_codes=["ACCESSIBILITY"],
            )
        )
    return StageResult(
        name="privacy_format_lint",
        ok=ok,
        notes=notes,
        dispositions=dispositions,
        details={"language": lang.to_dict()},
    )


def stage_named_human_release(packet: Dict[str, Any]) -> StageResult:
    notes: List[str] = []
    ok = True
    release = packet.get("release") or {}
    reviewer = release.get("named_human_reviewer") or release.get("reviewer")
    if not reviewer:
        ok = False
        notes.append("Named human reviewer required for release")
    if release.get("auto_released"):
        ok = False
        notes.append("Auto-release forbidden")
    for lead in packet.get("leads") or []:
        legal = lead.get("legal_relevance") or lead.get("legal_viability")
        if legal not in (None, "", {}):
            if not lead.get("counsel_filled"):
                ok = False
                notes.append(
                    f"{lead.get('lead_id')}: legal relevance/viability set without counsel"
                )
    return StageResult(
        name="named_human_release",
        ok=ok,
        notes=notes,
        details={"reviewer": reviewer, "counsel_only_legal_fields": True},
    )
