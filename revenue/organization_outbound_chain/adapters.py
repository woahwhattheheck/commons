"""Supported provider entrypoints for the mandatory organization-aware chain.

These are intentionally thin.  Adapter-specific code derives the exact provider
request bytes/private route identity and passes the actual external mutation as
``provider_callback``; no adapter calls that callback itself.
"""
from __future__ import annotations

from typing import Any

from .chain import execute_guarded_initial_outreach


def _run(provider: str, *args: Any, **kwargs: Any):
    if "provider" in kwargs:
        raise TypeError("provider is fixed by the registered adapter")
    return execute_guarded_initial_outreach(*args, provider=provider, **kwargs)


def gmail_initial_outreach(*args: Any, **kwargs: Any):
    return _run("gmail", *args, **kwargs)


def slack_dm_initial_outreach(*args: Any, **kwargs: Any):
    return _run("slack_dm", *args, **kwargs)


def discord_initial_outreach(*args: Any, **kwargs: Any):
    return _run("discord", *args, **kwargs)


def webhook_mail_initial_outreach(*args: Any, **kwargs: Any):
    return _run("webhook_mail", *args, **kwargs)
