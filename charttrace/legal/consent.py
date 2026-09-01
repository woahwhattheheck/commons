"""Affirmative legal acceptance and recipient-transfer authorization."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional

from .instruments import (
    INSTRUMENTS,
    TRUST_CENTER_VERSION,
    instrument_suite_hash,
    instrument_versions,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LegalState(str, Enum):
    NOT_ACCEPTED = "NOT_ACCEPTED"
    ACCEPTED_VN = "ACCEPTED_vN"
    REACCEPT_REQUIRED = "REACCEPT_REQUIRED"
    AUTHORITY_HOLD = "AUTHORITY_HOLD"
    TRANSFER_NOT_AUTHORIZED = "TRANSFER_NOT_AUTHORIZED"
    TRANSFER_AUTHORIZED = "TRANSFER_AUTHORIZED"


class ConsentError(ValueError):
    """Raised when an affirmative legal action is incomplete or invalid."""


@dataclass
class TransferAuthorization:
    recipient: Optional[str] = None
    recipient_role: Optional[str] = None
    authorized_by: Optional[str] = None
    authorized_at: Optional[str] = None
    authorization_version: Optional[str] = None

    @property
    def state(self) -> LegalState:
        if self.recipient and self.authorized_at:
            return LegalState.TRANSFER_AUTHORIZED
        return LegalState.TRANSFER_NOT_AUTHORIZED

    def revoke(self) -> None:
        self.authorized_by = None
        self.authorized_at = None
        self.authorization_version = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "recipient": self.recipient,
            "recipient_role": self.recipient_role,
            "authorized_by": self.authorized_by,
            "authorized_at": self.authorized_at,
            "authorization_version": self.authorization_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TransferAuthorization":
        return cls(
            recipient=value.get("recipient"),
            recipient_role=value.get("recipient_role"),
            authorized_by=value.get("authorized_by"),
            authorized_at=value.get("authorized_at"),
            authorization_version=value.get("authorization_version"),
        )


@dataclass
class ConsentLedger:
    accepted_suite_version: Optional[str] = None
    accepted_suite_hash: Optional[str] = None
    accepted_instruments: Dict[str, str] = field(default_factory=dict)
    accepted_by: Optional[str] = None
    accepted_at: Optional[str] = None
    authority_hold_reason: Optional[str] = None
    transfer: TransferAuthorization = field(default_factory=TransferAuthorization)

    @staticmethod
    def blank_acknowledgements() -> Dict[str, bool]:
        """Return unchecked controls for every instrument."""
        return {instrument.instrument_id: False for instrument in INSTRUMENTS}

    @property
    def acceptance_state(self) -> LegalState:
        if self.authority_hold_reason:
            return LegalState.AUTHORITY_HOLD
        if not self.accepted_at:
            return LegalState.NOT_ACCEPTED
        if (
            self.accepted_suite_version != TRUST_CENTER_VERSION
            or self.accepted_suite_hash != instrument_suite_hash()
            or self.accepted_instruments != instrument_versions()
        ):
            return LegalState.REACCEPT_REQUIRED
        return LegalState.ACCEPTED_VN

    @property
    def transfer_state(self) -> LegalState:
        return self.transfer.state

    @property
    def current_and_authorized(self) -> bool:
        return self.acceptance_state is LegalState.ACCEPTED_VN

    def accept(
        self,
        acknowledgements: Mapping[str, bool],
        accepted_by: str,
    ) -> None:
        expected = set(instrument_versions())
        supplied = set(acknowledgements)
        if supplied != expected:
            missing = sorted(expected - supplied)
            unknown = sorted(supplied - expected)
            raise ConsentError(
                "Acknowledgements must exactly match current instruments "
                f"(missing={missing}, unknown={unknown})."
            )
        unchecked = sorted(
            instrument_id
            for instrument_id, checked in acknowledgements.items()
            if checked is not True
        )
        if unchecked:
            raise ConsentError(
                "Every instrument requires a separate affirmative "
                f"acknowledgement: {', '.join(unchecked)}."
            )
        if not accepted_by.strip():
            raise ConsentError("The attesting operator name is required.")

        self.accepted_suite_version = TRUST_CENTER_VERSION
        self.accepted_suite_hash = instrument_suite_hash()
        self.accepted_instruments = instrument_versions()
        self.accepted_by = accepted_by.strip()
        self.accepted_at = _now()
        self.authority_hold_reason = None

    def require_reacceptance(self) -> None:
        """Invalidate the recorded suite version without fabricating a new one."""
        if self.accepted_at:
            self.accepted_suite_version = f"superseded:{self.accepted_suite_version}"

    def place_authority_hold(self, reason: str) -> None:
        if not reason.strip():
            raise ConsentError("An authority-hold reason is required.")
        self.authority_hold_reason = reason.strip()

    def clear_authority_hold(self) -> None:
        """Require fresh acceptance after an authority dispute."""
        self.authority_hold_reason = None
        self.require_reacceptance()

    def set_recipient(self, recipient: str, role: str = "recipient") -> None:
        recipient = recipient.strip()
        role = role.strip()
        if not recipient:
            raise ConsentError("A named recipient is required.")
        if not role:
            raise ConsentError("A recipient role is required.")
        changed = (
            recipient != self.transfer.recipient
            or role != self.transfer.recipient_role
        )
        self.transfer.recipient = recipient
        self.transfer.recipient_role = role
        if changed:
            self.transfer.revoke()

    def authorize_transfer(
        self,
        affirmative_authorization: bool,
        authorized_by: str,
    ) -> None:
        if not self.current_and_authorized:
            raise ConsentError("Current terms and authority are required.")
        if not self.transfer.recipient:
            raise ConsentError("Set a named recipient before authorizing transfer.")
        if affirmative_authorization is not True:
            raise ConsentError("Recipient transfer must be affirmatively authorized.")
        if not authorized_by.strip():
            raise ConsentError("The transfer authorizer name is required.")
        self.transfer.authorized_by = authorized_by.strip()
        self.transfer.authorized_at = _now()
        self.transfer.authorization_version = TRUST_CENTER_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accepted_suite_version": self.accepted_suite_version,
            "accepted_suite_hash": self.accepted_suite_hash,
            "accepted_instruments": dict(self.accepted_instruments),
            "accepted_by": self.accepted_by,
            "accepted_at": self.accepted_at,
            "authority_hold_reason": self.authority_hold_reason,
            "transfer": self.transfer.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConsentLedger":
        return cls(
            accepted_suite_version=value.get("accepted_suite_version"),
            accepted_suite_hash=value.get("accepted_suite_hash"),
            accepted_instruments=dict(value.get("accepted_instruments", {})),
            accepted_by=value.get("accepted_by"),
            accepted_at=value.get("accepted_at"),
            authority_hold_reason=value.get("authority_hold_reason"),
            transfer=TransferAuthorization.from_dict(value.get("transfer", {})),
        )
