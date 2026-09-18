"""Concrete provider entrypoints for the mandatory organization-aware chain.

Each adapter fixes one provider and one transport protocol. Callers cannot pass a
provider name or arbitrary provider callback through this surface.

Production dependencies are captured once at module load. Rebinding exported helper,
boundary-class, or chain names later cannot redirect a saved adapter entrypoint.
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


def _build_first_load_adapters(
    _execute=execute_guarded_initial_outreach,
    _gmail_boundary=GmailBoundary,
    _slack_boundary=SlackDmBoundary,
    _discord_boundary=DiscordBoundary,
    _webhook_boundary=WebhookMailBoundary,
):
    def run_impl(boundary: object, *args: Any, **kwargs: Any):
        forbidden = {"provider", "provider_callback", "provider_boundary"} & set(kwargs)
        if forbidden:
            raise TypeError(
                "provider identity and mutation boundary are fixed by the registered adapter"
            )
        return _execute(
            *args,
            provider_boundary=boundary,
            **kwargs,
        )

    def gmail_initial_outreach(*args: Any, transport: GmailTransport, **kwargs: Any):
        return run_impl(_gmail_boundary(transport), *args, **kwargs)

    def slack_dm_initial_outreach(*args: Any, transport: SlackDmTransport, **kwargs: Any):
        return run_impl(_slack_boundary(transport), *args, **kwargs)

    def discord_initial_outreach(*args: Any, transport: DiscordTransport, **kwargs: Any):
        return run_impl(_discord_boundary(transport), *args, **kwargs)

    def webhook_mail_initial_outreach(*args: Any, transport: WebhookMailTransport, **kwargs: Any):
        return run_impl(_webhook_boundary(transport), *args, **kwargs)

    return (
        run_impl,
        gmail_initial_outreach,
        slack_dm_initial_outreach,
        discord_initial_outreach,
        webhook_mail_initial_outreach,
    )


(
    _run,
    gmail_initial_outreach,
    slack_dm_initial_outreach,
    discord_initial_outreach,
    webhook_mail_initial_outreach,
) = _build_first_load_adapters()
del _build_first_load_adapters
