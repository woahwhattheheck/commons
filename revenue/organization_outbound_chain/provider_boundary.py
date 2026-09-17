"""Typed outbound mutation boundary for the mandatory organization chain.

The chain must never accept an arbitrary per-invocation callback.  Instead a host
supplies one exact provider transport object and the provider-specific adapter
constructs one of the frozen boundary objects below.  The terminal consumer calls
`invoke_provider_boundary` once with its content-addressed idempotency key.

The transport implementation is the process/connector integration seam.  Repository
CI can prove that repository code reaches it only through this module; it cannot
intercept an out-of-process connector invocation that ignores the repository
entirely.  Those host mutation identities are enumerated in registry.py so that
operator/runtime policy can bind the same closed provider set.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, Union, runtime_checkable


class ProviderBoundaryError(TypeError):
    """Fail-closed provider boundary shape error."""


@runtime_checkable
class GmailTransport(Protocol):
    def gmail_send_message(self, *, idempotency_key: str, request_bytes: bytes) -> Any: ...


@runtime_checkable
class SlackDmTransport(Protocol):
    def slack_send_dm(self, *, idempotency_key: str, request_bytes: bytes) -> Any: ...


@runtime_checkable
class DiscordTransport(Protocol):
    def discord_send_message(self, *, idempotency_key: str, request_bytes: bytes) -> Any: ...


@runtime_checkable
class WebhookMailTransport(Protocol):
    def webhook_mail_send(self, *, idempotency_key: str, request_bytes: bytes) -> Any: ...


@dataclass(frozen=True, slots=True)
class GmailBoundary:
    transport: GmailTransport
    provider: ClassVar[str] = "gmail"
    transport_method: ClassVar[str] = "gmail_send_message"
    host_mutation_identities: ClassVar[tuple[str, ...]] = (
        "mcp__Gmail__send_email",
        "mcp__Gmail__send_draft",
        "mcp__Gmail__forward_emails",
    )


@dataclass(frozen=True, slots=True)
class SlackDmBoundary:
    transport: SlackDmTransport
    provider: ClassVar[str] = "slack_dm"
    transport_method: ClassVar[str] = "slack_send_dm"
    host_mutation_identities: ClassVar[tuple[str, ...]] = (
        "mcp__Slack__slack_send_message",
        "mcp__Slack__slack_schedule_message",
    )


@dataclass(frozen=True, slots=True)
class DiscordBoundary:
    transport: DiscordTransport
    provider: ClassVar[str] = "discord"
    transport_method: ClassVar[str] = "discord_send_message"
    host_mutation_identities: ClassVar[tuple[str, ...]] = (
        "discord.Webhook.send",
        "discord.webhook.execute",
    )


@dataclass(frozen=True, slots=True)
class WebhookMailBoundary:
    transport: WebhookMailTransport
    provider: ClassVar[str] = "webhook_mail"
    transport_method: ClassVar[str] = "webhook_mail_send"
    host_mutation_identities: ClassVar[tuple[str, ...]] = (
        "http.webhook_mail.post",
    )


ProviderBoundary = Union[
    GmailBoundary,
    SlackDmBoundary,
    DiscordBoundary,
    WebhookMailBoundary,
]

_BOUNDARY_TYPES = (
    GmailBoundary,
    SlackDmBoundary,
    DiscordBoundary,
    WebhookMailBoundary,
)
_BOUNDARY_BY_PROVIDER = {boundary.provider: boundary for boundary in _BOUNDARY_TYPES}


def provider_name(boundary: ProviderBoundary) -> str:
    """Return the provider only for one exact registered boundary generation."""
    if type(boundary) not in _BOUNDARY_TYPES:
        raise ProviderBoundaryError("exact registered provider boundary required")
    return type(boundary).provider


def registered_boundary_types() -> tuple[type, ...]:
    return _BOUNDARY_TYPES


def boundary_for_provider(provider: str) -> type:
    try:
        return _BOUNDARY_BY_PROVIDER[provider]
    except KeyError as exc:
        raise ProviderBoundaryError("provider is not registered") from exc


def invoke_provider_boundary(
    boundary: ProviderBoundary,
    *,
    idempotency_key: str,
    request_bytes: bytes,
) -> Any:
    """Invoke the exact provider transport method for one registered boundary.

    No callback/function is accepted here.  Exact class identity prevents a caller
    from substituting a subclass with an overridden invocation path.
    """
    if type(boundary) not in _BOUNDARY_TYPES:
        raise ProviderBoundaryError("exact registered provider boundary required")
    if not isinstance(idempotency_key, str) or not idempotency_key:
        raise ProviderBoundaryError("idempotency_key required")
    if type(request_bytes) is not bytes:
        raise ProviderBoundaryError("request_bytes must be exact bytes")
    method_name = type(boundary).transport_method
    method = getattr(boundary.transport, method_name, None)
    if not callable(method):
        raise ProviderBoundaryError(
            f"{type(boundary).provider} transport must implement {method_name}"
        )
    return method(idempotency_key=idempotency_key, request_bytes=request_bytes)
