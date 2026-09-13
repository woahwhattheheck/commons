from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Protocol
from urllib.parse import urlparse


RECEIPT_VERSION = 1


class FreshnessStatus(str, Enum):
    ACTIONABLE = "actionable"
    OCCUPIED = "occupied"
    STALE = "stale"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class Candidate:
    candidate_url: str
    advertised_amount: str
    currency: str
    platform: str
    source_timestamp: str


@dataclass(frozen=True)
class Observation:
    canonical_url: str | None
    canonical_state: str
    assignees: tuple[str, ...] = ()
    visible_claim_count: int | None = None
    active_competing_prs: tuple[str, ...] = ()
    last_substantive_activity: str | None = None
    sponsor_payment_present: bool | None = None
    acceptance_criteria_reachable: bool | None = None
    security_bounty: bool = False
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Check:
    name: str
    outcome: str
    detail: str


@dataclass(frozen=True)
class FreshnessReceipt:
    version: int
    candidate: Candidate
    checked_at: str
    observation: Observation
    checks: tuple[Check, ...]
    freshness_status: FreshnessStatus
    route: str
    receipt_sha256: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["freshness_status"] = self.freshness_status.value
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EvidenceReader(Protocol):
    def inspect(self, candidate: Candidate) -> Observation:
        """Return independent canonical evidence for one candidate without mutating it."""


def _parse_timestamp(value: str, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _normalize_candidate(candidate: Candidate) -> Candidate:
    parsed = urlparse(candidate.candidate_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("candidate_url must be an absolute http(s) URL")
    try:
        amount = Decimal(candidate.advertised_amount)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("advertised_amount must be a finite non-negative decimal") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("advertised_amount must be a finite non-negative decimal")
    currency = candidate.currency.strip().upper()
    platform = candidate.platform.strip()
    if not currency:
        raise ValueError("currency must not be empty")
    if not platform:
        raise ValueError("platform must not be empty")
    _parse_timestamp(candidate.source_timestamp, field="source_timestamp")
    return Candidate(
        candidate_url=candidate.candidate_url.strip(),
        advertised_amount=format(amount, "f"),
        currency=currency,
        platform=platform,
        source_timestamp=candidate.source_timestamp.strip(),
    )


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash_payload(payload: dict) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _open_state(value: str) -> bool:
    return isinstance(value, str) and value.strip().lower() == "open"


def _evaluate(candidate: Candidate, observation: Observation, *, checked_at: str, max_idle_days: int) -> tuple[tuple[Check, ...], FreshnessStatus, str]:
    checks: list[Check] = []

    canonical_url = observation.canonical_url
    if not canonical_url:
        checks.append(Check("canonical_binding", "fail", "no canonical issue/PR URL resolved"))
    else:
        parsed = urlparse(canonical_url)
        good = parsed.scheme in {"http", "https"} and parsed.netloc.lower() == "github.com"
        checks.append(Check("canonical_binding", "pass" if good else "fail", canonical_url))

    canonical_open = _open_state(observation.canonical_state)
    checks.append(
        Check(
            "canonical_state",
            "pass" if canonical_open else "fail",
            f"canonical state={observation.canonical_state!r}",
        )
    )

    occupied_signals = []
    if observation.assignees:
        occupied_signals.append(f"assignees={len(observation.assignees)}")
    if observation.visible_claim_count is not None and observation.visible_claim_count > 0:
        occupied_signals.append(f"visible_claims={observation.visible_claim_count}")
    if observation.active_competing_prs:
        occupied_signals.append(f"active_prs={len(observation.active_competing_prs)}")
    checks.append(
        Check(
            "occupancy",
            "fail" if occupied_signals else "pass",
            ", ".join(occupied_signals) if occupied_signals else "no visible occupancy signal",
        )
    )

    if observation.sponsor_payment_present is True:
        payment_outcome = "pass"
        payment_detail = "sponsor/payment mechanism observed"
    elif observation.sponsor_payment_present is False:
        payment_outcome = "fail"
        payment_detail = "sponsor/payment mechanism no longer observed"
    else:
        payment_outcome = "unknown"
        payment_detail = "sponsor/payment mechanism not independently resolved"
    checks.append(Check("payment_mechanism", payment_outcome, payment_detail))

    if observation.acceptance_criteria_reachable is True:
        acceptance_outcome = "pass"
        acceptance_detail = "acceptance criteria remain reachable"
    elif observation.acceptance_criteria_reachable is False:
        acceptance_outcome = "fail"
        acceptance_detail = "acceptance criteria are no longer reachable"
    else:
        acceptance_outcome = "unknown"
        acceptance_detail = "acceptance criteria not independently resolved"
    checks.append(Check("acceptance_criteria", acceptance_outcome, acceptance_detail))

    activity_outcome = "unknown"
    activity_detail = "last substantive activity not independently resolved"
    if observation.last_substantive_activity:
        try:
            activity = _parse_timestamp(observation.last_substantive_activity, field="last_substantive_activity")
            checked = _parse_timestamp(checked_at, field="checked_at")
            if activity > checked:
                activity_outcome = "fail"
                activity_detail = "last substantive activity is in the future"
            else:
                idle_days = (checked - activity).total_seconds() / 86400
                if idle_days > max_idle_days:
                    activity_outcome = "unknown"
                    activity_detail = f"last substantive activity is {idle_days:.1f} days old"
                else:
                    activity_outcome = "pass"
                    activity_detail = f"last substantive activity is {idle_days:.1f} days old"
        except ValueError as exc:
            activity_outcome = "fail"
            activity_detail = str(exc)
    checks.append(Check("activity_freshness", activity_outcome, activity_detail))

    if observation.security_bounty:
        checks.append(Check("security_routing", "fail", "security bounty must route to research-only inventory"))
        return tuple(checks), FreshnessStatus.AMBIGUOUS, "research_only"
    checks.append(Check("security_routing", "pass", "ordinary funded-work candidate"))

    if not canonical_open or not canonical_url:
        return tuple(checks), FreshnessStatus.STALE, "reject"
    if observation.sponsor_payment_present is False or observation.acceptance_criteria_reachable is False:
        return tuple(checks), FreshnessStatus.STALE, "reject"
    if occupied_signals:
        return tuple(checks), FreshnessStatus.OCCUPIED, "hold"
    if any(check.outcome in {"unknown", "fail"} for check in checks):
        return tuple(checks), FreshnessStatus.AMBIGUOUS, "hold"
    return tuple(checks), FreshnessStatus.ACTIONABLE, "work_feed"


def validate_candidate(
    candidate: Candidate,
    reader: EvidenceReader,
    *,
    checked_at: str | None = None,
    max_idle_days: int = 90,
) -> FreshnessReceipt:
    """Validate a funded-work lead without claiming, commenting, paying, or mutating it."""
    if max_idle_days < 1:
        raise ValueError("max_idle_days must be >= 1")
    normalized = _normalize_candidate(candidate)
    checked = checked_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    checked_dt = _parse_timestamp(checked, field="checked_at")
    source_dt = _parse_timestamp(normalized.source_timestamp, field="source_timestamp")
    if source_dt > checked_dt:
        raise ValueError("source_timestamp must not be in the future relative to checked_at")

    observation = reader.inspect(normalized)
    if not isinstance(observation, Observation):
        raise TypeError("reader.inspect() must return Observation")
    checks, status, route = _evaluate(
        normalized,
        observation,
        checked_at=checked,
        max_idle_days=max_idle_days,
    )
    unsigned = {
        "version": RECEIPT_VERSION,
        "candidate": asdict(normalized),
        "checked_at": checked,
        "observation": asdict(observation),
        "checks": [asdict(check) for check in checks],
        "freshness_status": status.value,
        "route": route,
    }
    digest = _hash_payload(unsigned)
    return FreshnessReceipt(
        version=RECEIPT_VERSION,
        candidate=normalized,
        checked_at=checked,
        observation=observation,
        checks=checks,
        freshness_status=status,
        route=route,
        receipt_sha256=digest,
    )


def verify_receipt(receipt: FreshnessReceipt) -> bool:
    payload = receipt.to_dict()
    supplied = payload.pop("receipt_sha256")
    return _hash_payload(payload) == supplied
