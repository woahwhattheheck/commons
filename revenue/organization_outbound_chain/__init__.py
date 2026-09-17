"""Mandatory organization-aware provider-bound outbound chain."""
from .adapters import (
    discord_initial_outreach,
    gmail_initial_outreach,
    slack_dm_initial_outreach,
    webhook_mail_initial_outreach,
)
from .chain import (
    ChainError,
    execute_guarded_initial_outreach,
    opportunity_commitment,
    prospect_fingerprint,
    route_commitment,
)
from .registry import ADAPTERS, find_bypasses, registered_provider_names

__all__ = [
    "ChainError",
    "execute_guarded_initial_outreach",
    "prospect_fingerprint",
    "route_commitment",
    "opportunity_commitment",
    "gmail_initial_outreach",
    "slack_dm_initial_outreach",
    "discord_initial_outreach",
    "webhook_mail_initial_outreach",
    "ADAPTERS",
    "find_bypasses",
    "registered_provider_names",
]
