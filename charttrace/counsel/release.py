"""Named-human release gate. Counsel mode cannot read unreleased cases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReleaseReceipt:
    case_id: str
    recipient_id: str
    actor_id: str
    role: str
    release_id: str
    counsel_approved: bool = False


def named_human_release(
    case_id: str,
    recipient_id: str,
    actor_id: str,
    role: str,
    release_id: str,
) -> ReleaseReceipt:
    if not actor_id.strip():
        raise ValueError("named human actor is required")
    if role not in {"named-human-release-owner", "licensed-counsel", "qualified-clinician"}:
        raise ValueError("release role is outside the named-human set")
    if not recipient_id.strip():
        raise ValueError("recipient must be named; transfer is off by default")
    return ReleaseReceipt(
        case_id=case_id,
        recipient_id=recipient_id,
        actor_id=actor_id,
        role=role,
        release_id=release_id,
        counsel_approved=False,
    )


class CounselAccess:
    """Offline counsel review may open only released packages for that recipient."""

    def __init__(self) -> None:
        self._released: dict[tuple[str, str], ReleaseReceipt] = {}

    def record(self, receipt: ReleaseReceipt) -> None:
        self._released[(receipt.case_id, receipt.recipient_id)] = receipt

    def can_read(self, case_id: str, recipient_id: str, requested_case: str) -> bool:
        if requested_case != case_id:
            return False
        return (case_id, recipient_id) in self._released

    def require_read(self, case_id: str, recipient_id: str, requested_case: str) -> None:
        if not self.can_read(case_id, recipient_id, requested_case):
            raise PermissionError("counsel mode cannot read unreleased or unrelated cases")
