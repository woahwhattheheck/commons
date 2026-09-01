"""Auditable review dispositions for ChartTrace Lane D."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Disposition(str, Enum):
    PASS = "PASS"
    REPAIR = "REPAIR"
    DOWNGRADE = "DOWNGRADE"
    WEAK_APPENDIX = "WEAK_APPENDIX"
    MERGE_DUPLICATE = "MERGE_DUPLICATE"
    REJECT_UNSUPPORTED = "REJECT_UNSUPPORTED"
    HOLD = "HOLD"


FORBIDDEN_SOLE_REJECTION_REASONS = frozenset(
    {
        "not actionable",
        "unlikely",
        "too aggressive",
        "a lawyer might dislike it",
        "lawyer might dislike it",
    }
)


@dataclass(frozen=True)
class DispositionRecord:
    item_id: str
    disposition: Disposition
    stage: str
    reason: str
    defect_codes: List[str] = field(default_factory=list)
    preserves_in_appendix: bool = False
    leaves_packet: bool = True
    merge_target_id: Optional[str] = None
    audit_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["disposition"] = self.disposition.value
        return data


def validate_rejection_reason(reason: str, disposition: Disposition) -> Optional[str]:
    if disposition != Disposition.REJECT_UNSUPPORTED:
        return None
    normalized = " ".join(reason.lower().strip().split())
    if normalized in FORBIDDEN_SOLE_REJECTION_REASONS:
        return (
            "Rejection requires a concrete defect; cannot reject solely as "
            f"'{reason}'."
        )
    for forbidden in FORBIDDEN_SOLE_REJECTION_REASONS:
        if normalized == forbidden or normalized.startswith(forbidden + "."):
            return (
                "Rejection requires a concrete defect; cannot reject solely as "
                f"'{reason}'."
            )
    return None


def apply_disposition(
    item_id: str,
    disposition: Disposition,
    stage: str,
    reason: str,
    *,
    defect_codes: Optional[List[str]] = None,
    merge_target_id: Optional[str] = None,
    audit_notes: str = "",
) -> DispositionRecord:
    err = validate_rejection_reason(reason, disposition)
    if err:
        raise ValueError(err)

    preserves = disposition in (Disposition.WEAK_APPENDIX, Disposition.DOWNGRADE)
    leaves = disposition not in (
        Disposition.REJECT_UNSUPPORTED,
        Disposition.HOLD,
        Disposition.REPAIR,
    )
    if disposition == Disposition.WEAK_APPENDIX:
        leaves = True
        preserves = True
    if disposition == Disposition.MERGE_DUPLICATE and not merge_target_id:
        raise ValueError("MERGE_DUPLICATE requires merge_target_id")

    return DispositionRecord(
        item_id=item_id,
        disposition=disposition,
        stage=stage,
        reason=reason,
        defect_codes=list(defect_codes or []),
        preserves_in_appendix=preserves,
        leaves_packet=leaves,
        merge_target_id=merge_target_id,
        audit_notes=audit_notes,
    )
