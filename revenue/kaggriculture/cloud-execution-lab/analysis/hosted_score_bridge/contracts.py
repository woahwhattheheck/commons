"""Evidence contracts and fail-closed configuration."""

from __future__ import annotations

from dataclasses import dataclass


SCHEMA_VERSION = "titan.hosted-score-bridge.v1"
EXCLUDED_HOSTED_SOURCES = {
    "validation",
    "internal_validation",
    "selfplay",
    "self_play",
    "self-play",
    "local",
    "local_simulation",
}


class IntegrityError(ValueError):
    """Raised when evidence cannot be compared without inventing provenance."""


@dataclass(frozen=True)
class BridgeConfig:
    archive_sha256: str
    submission_id: str
    min_active_local_cells: int = 8
    min_hosted_episodes: int = 8
    min_active_share: float = 0.50

    def __post_init__(self) -> None:
        archive = self.archive_sha256.lower()
        if len(archive) != 64 or any(c not in "0123456789abcdef" for c in archive):
            raise IntegrityError("archive_sha256 must be exactly 64 hexadecimal characters")
        if not str(self.submission_id).strip():
            raise IntegrityError("submission_id must be non-empty")
        if self.min_active_local_cells < 1:
            raise IntegrityError("min_active_local_cells must be >= 1")
        if self.min_hosted_episodes < 1:
            raise IntegrityError("min_hosted_episodes must be >= 1")
        if not 0.0 <= self.min_active_share <= 1.0:
            raise IntegrityError("min_active_share must be between 0 and 1")


@dataclass(frozen=True)
class LocalCell:
    run_id: str
    archive_sha256: str
    submission_id: str
    opponent_id: str
    opponent_class: str
    seed: str
    seat: str
    market_regime: str
    margin: float
    behavior_state: str
    coverage_tags: tuple[str, ...]


@dataclass(frozen=True)
class HostedEpisode:
    episode_id: str
    archive_sha256: str
    submission_id: str
    opponent_id: str
    opponent_class: str
    seat: str
    market_regime: str
    margin: float
    signatures: tuple[str, ...]
    source: str
