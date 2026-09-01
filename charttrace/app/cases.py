"""Case lifecycle records and guarded transitions."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4

from charttrace.legal import LegalState, TransferAuthorization


DEADLINE_BANNER = (
    "DEADLINE_COUNSEL_REVIEW_REQUIRED — Do not rely on ChartTrace for "
    "limitation or repose deadlines. Confirm all deadlines with qualified counsel."
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CaseLifecycle(str, Enum):
    DRAFT = "DRAFT"
    HOLD_TERMS_OR_AUTHORITY = "HOLD_TERMS_OR_AUTHORITY"
    READY_TO_INGEST = "READY_TO_INGEST"
    INGESTED_SEALED = "INGESTED_SEALED"
    PEER_ANALYSIS = "PEER_ANALYSIS"
    INTERNAL_QA = "INTERNAL_QA"
    HUMAN_RELEASE_REVIEW = "HUMAN_RELEASE_REVIEW"
    READY_TO_RELEASE = "READY_TO_RELEASE"
    RELEASED_TO_NAMED_RECIPIENT = "RELEASED_TO_NAMED_RECIPIENT"
    RETENTION_HOLD = "RETENTION_HOLD"
    DELETED_WITH_RECEIPT = "DELETED_WITH_RECEIPT"


class LifecycleError(RuntimeError):
    pass


_ALLOWED_TRANSITIONS = {
    CaseLifecycle.DRAFT: {
        CaseLifecycle.HOLD_TERMS_OR_AUTHORITY,
        CaseLifecycle.READY_TO_INGEST,
    },
    CaseLifecycle.HOLD_TERMS_OR_AUTHORITY: {CaseLifecycle.READY_TO_INGEST},
    CaseLifecycle.READY_TO_INGEST: {CaseLifecycle.INGESTED_SEALED},
    CaseLifecycle.INGESTED_SEALED: {CaseLifecycle.PEER_ANALYSIS},
    CaseLifecycle.PEER_ANALYSIS: {CaseLifecycle.INTERNAL_QA},
    CaseLifecycle.INTERNAL_QA: {CaseLifecycle.HUMAN_RELEASE_REVIEW},
    CaseLifecycle.HUMAN_RELEASE_REVIEW: {CaseLifecycle.READY_TO_RELEASE},
    CaseLifecycle.READY_TO_RELEASE: {
        CaseLifecycle.RELEASED_TO_NAMED_RECIPIENT
    },
    CaseLifecycle.RELEASED_TO_NAMED_RECIPIENT: {
        CaseLifecycle.RETENTION_HOLD,
        CaseLifecycle.DELETED_WITH_RECEIPT,
    },
    CaseLifecycle.RETENTION_HOLD: {CaseLifecycle.DELETED_WITH_RECEIPT},
    CaseLifecycle.DELETED_WITH_RECEIPT: set(),
}


@dataclass
class SourceSeal:
    display_name: str
    sha256: str
    size_bytes: int
    sealed_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display_name": self.display_name,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "sealed_at": self.sealed_at,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceSeal":
        return cls(
            display_name=str(value["display_name"]),
            sha256=str(value["sha256"]),
            size_bytes=int(value["size_bytes"]),
            sealed_at=str(value["sealed_at"]),
        )


@dataclass
class AuditReceipt:
    sequence: int
    event: str
    detail: str
    created_at: str
    previous_hash: str
    receipt_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event": self.event,
            "detail": self.detail,
            "created_at": self.created_at,
            "previous_hash": self.previous_hash,
            "receipt_hash": self.receipt_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuditReceipt":
        return cls(
            sequence=int(value["sequence"]),
            event=str(value["event"]),
            detail=str(value["detail"]),
            created_at=str(value["created_at"]),
            previous_hash=str(value["previous_hash"]),
            receipt_hash=str(value["receipt_hash"]),
        )


@dataclass
class CaseRecord:
    name: str
    case_id: str = field(default_factory=lambda: str(uuid4()))
    lifecycle: CaseLifecycle = CaseLifecycle.DRAFT
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    sources: List[SourceSeal] = field(default_factory=list)
    peer_outputs: List[Dict[str, Any]] = field(default_factory=list)
    human_reviewed_by: Optional[str] = None
    recipient: TransferAuthorization = field(default_factory=TransferAuthorization)
    receipts: List[AuditReceipt] = field(default_factory=list)
    retention_hold_reason: Optional[str] = None
    deleted_at: Optional[str] = None

    def transition(self, target: CaseLifecycle) -> None:
        allowed = _ALLOWED_TRANSITIONS[self.lifecycle]
        if target not in allowed:
            raise LifecycleError(
                f"Invalid lifecycle transition {self.lifecycle.value} -> {target.value}."
            )
        self.lifecycle = target
        self.updated_at = utc_now()

    def set_recipient(self, recipient: str, role: str = "recipient") -> None:
        recipient = recipient.strip()
        role = role.strip()
        if not recipient or not role:
            raise ValueError("A named recipient and role are required.")
        changed = (
            recipient != self.recipient.recipient
            or role != self.recipient.recipient_role
        )
        self.recipient.recipient = recipient
        self.recipient.recipient_role = role
        if changed:
            self.recipient.revoke()
        self.updated_at = utc_now()

    def authorize_transfer(
        self,
        legal_state: LegalState,
        affirmative_authorization: bool,
        authorized_by: str,
        legal_version: str,
    ) -> None:
        if legal_state is not LegalState.ACCEPTED_VN:
            raise LifecycleError("Current terms and authority are required.")
        if not self.recipient.recipient:
            raise LifecycleError("Set a named recipient before transfer authorization.")
        if affirmative_authorization is not True:
            raise LifecycleError("Transfer authorization must be affirmative.")
        if not authorized_by.strip():
            raise LifecycleError("The authorizer name is required.")
        self.recipient.authorized_by = authorized_by.strip()
        self.recipient.authorized_at = utc_now()
        self.recipient.authorization_version = legal_version
        self.updated_at = utc_now()

    @property
    def transfer_state(self) -> LegalState:
        return self.recipient.state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "case_id": self.case_id,
            "lifecycle": self.lifecycle.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sources": [source.to_dict() for source in self.sources],
            "peer_outputs": list(self.peer_outputs),
            "human_reviewed_by": self.human_reviewed_by,
            "recipient": self.recipient.to_dict(),
            "receipts": [receipt.to_dict() for receipt in self.receipts],
            "retention_hold_reason": self.retention_hold_reason,
            "deleted_at": self.deleted_at,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CaseRecord":
        return cls(
            name=str(value["name"]),
            case_id=str(value["case_id"]),
            lifecycle=CaseLifecycle(str(value["lifecycle"])),
            created_at=str(value["created_at"]),
            updated_at=str(value["updated_at"]),
            sources=[
                SourceSeal.from_dict(item) for item in value.get("sources", [])
            ],
            peer_outputs=list(value.get("peer_outputs", [])),
            human_reviewed_by=value.get("human_reviewed_by"),
            recipient=TransferAuthorization.from_dict(value.get("recipient", {})),
            receipts=[
                AuditReceipt.from_dict(item)
                for item in value.get("receipts", [])
            ],
            retention_hold_reason=value.get("retention_hold_reason"),
            deleted_at=value.get("deleted_at"),
        )
