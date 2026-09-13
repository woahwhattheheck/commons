"""Bounded read-only public-network transport."""
from __future__ import annotations

import ipaddress
import math
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from constants import AUTO_RESOLVE_SOURCE_HOSTS, MAX_HTTP_BYTES, USER_AGENT
from errors import EvidenceError, PreflightInputError
from models import Response


def _host_in_suffix(host: str, suffix: str) -> bool:
    normalized = host.rstrip(".").lower()
    return normalized == suffix or normalized.endswith(f".{suffix}")


def _trusted_source_suffix(host: str) -> str | None:
    for suffix in AUTO_RESOLVE_SOURCE_HOSTS:
        if _host_in_suffix(host, suffix):
            return suffix
    return None


def validate_public_destination(url: str) -> None:
    """Reject credentials and non-public network destinations before each GET/redirect."""

    try:
        parsed = urlsplit(url)
        port_number = parsed.port
    except ValueError as exc:
        raise EvidenceError("unsafe_destination", f"invalid destination port: {url}") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise EvidenceError("unsafe_destination", f"unsupported destination URL: {url}")
    if parsed.username or parsed.password:
        raise EvidenceError("unsafe_destination", "destination URL must not contain credentials")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise EvidenceError("unsafe_destination", f"non-public hostname rejected: {host}")
    port = port_number or (443 if parsed.scheme.lower() == "https" else 80)
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise EvidenceError("network_unavailable", f"DNS resolution failed for {host}: {exc}") from exc
    if not addresses:
        raise EvidenceError("network_unavailable", f"DNS resolution returned no addresses for {host}")
    for row in addresses:
        address = ipaddress.ip_address(row[4][0])
        if not address.is_global:
            raise EvidenceError("unsafe_destination", f"non-public address rejected for {host}: {address}")


def validate_redirect_destination(source_url: str, target_url: str) -> None:
    """Require redirects to remain inside the source's trusted hostname scope."""

    validate_public_destination(target_url)
    source_host = (urlsplit(source_url).hostname or "").rstrip(".").lower()
    target_host = (urlsplit(target_url).hostname or "").rstrip(".").lower()
    sponsor_suffix = _trusted_source_suffix(source_host)
    if sponsor_suffix:
        if not _host_in_suffix(target_host, sponsor_suffix):
            raise EvidenceError(
                "unsafe_redirect",
                f"redirect left trusted source domain {sponsor_suffix}: {target_host}",
            )
        return
    if target_host != source_host:
        raise EvidenceError(
            "unsafe_redirect",
            f"cross-host redirect rejected: {source_host} -> {target_host}",
        )


class _PublicOnlyRedirectHandler(HTTPRedirectHandler):
    def __init__(self, source_url: str):
        super().__init__()
        self.source_url = source_url

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        validate_redirect_destination(self.source_url, newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_bounded(handle: Any) -> bytes:
    body = handle.read(MAX_HTTP_BYTES + 1)
    if len(body) > MAX_HTTP_BYTES:
        raise EvidenceError("response_too_large", f"response exceeded {MAX_HTTP_BYTES} bytes")
    return body


class UrlLibTransport:
    """Public-network HTTP reader with optional GitHub token authentication."""

    def __init__(self, *, timeout: float = 15.0, github_token: str | None = None):
        if not math.isfinite(timeout) or timeout <= 0:
            raise PreflightInputError("timeout must be a positive finite number")
        self.timeout = timeout
        self.github_token = github_token

    def fetch(self, url: str, *, accept: str) -> Response:
        validate_public_destination(url)
        headers = {"Accept": accept, "User-Agent": USER_AGENT}
        if self.github_token and urlsplit(url).hostname == "api.github.com":
            headers["Authorization"] = f"Bearer {self.github_token}"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        request = Request(url, headers=headers, method="GET")
        opener = build_opener(_PublicOnlyRedirectHandler(url))
        try:
            with opener.open(request, timeout=self.timeout) as handle:
                final_url = handle.geturl()
                validate_redirect_destination(url, final_url)
                return Response(
                    url=final_url,
                    status=int(handle.status),
                    headers={str(k).lower(): str(v) for k, v in handle.headers.items()},
                    body=read_bounded(handle),
                )
        except HTTPError as exc:
            final_url = exc.geturl() or url
            validate_redirect_destination(url, final_url)
            return Response(
                url=final_url,
                status=int(exc.code),
                headers={str(k).lower(): str(v) for k, v in exc.headers.items()},
                body=read_bounded(exc),
            )
        except EvidenceError:
            raise
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            raise EvidenceError("network_unavailable", f"read failed for {url}: {exc}") from exc
