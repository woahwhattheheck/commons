"""Concrete provider entrypoints for the mandatory organization-aware chain.

Each adapter fixes one provider and one transport protocol.  Callers cannot pass a
provider name or arbitrary provider callback through this surface.
"""
from __future__ import annotations

from typing import Any

from .chain import execute_guarded_initial_outreach
from .provider_boundary import (
    DiscordBoundary,
    DiscordTransport,
    GmailBoundary,
    GmailTransport,
    SlackDmBoundary,
    SlackDmTransport,
    WebhookMailBoundary,
    WebhookMailTransport,
)


def _run(boundary: object, *args: Any, **kwargs: Any):
    forbidden = {"provider", "provider_callback", "provider_boundary"} & set(kwargs)
    if forbidden:
        raise TypeError(
            "provider identity and mutation boundary are fixed by the registered adapter"
        )
    return execute_guarded_initial_outreach(
        *args,
        provider_boundary=boundary,
        **kwargs,
    )


def gmail_initial_outreach(*args: Any, transport: GmailTransport, **kwargs: Any):
    return _run(GmailBoundary(transport), *args, **kwargs)


def slack_dm_initial_outreach(*args: Any, transport: SlackDmTransport, **kwargs: Any):
    return _run(SlackDmBoundary(transport), *args, **kwargs)


def discord_initial_outreach(*args: Any, transport: DiscordTransport, **kwargs: Any):
    return _run(DiscordBoundary(transport), *args, **kwargs)


def webhook_mail_initial_outreach(*args: Any, transport: WebhookMailTransport, **kwargs: Any):
    return _run(WebhookMailBoundary(transport), *args, **kwargs)
