"""Bounded read-only public-network transport."""
from __future__ import annotations

import ipaddress
import math
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from constants import MAX_HTTP_BYTES, USER_AGENT
from errors import EvidenceError, PreflightInputError
from models import Response


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


class _PublicOnlyRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        validate_public_destination(newurl)
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
        self.opener = build_opener(_PublicOnlyRedirectHandler())

    def fetch(self, url: str, *, accept: str) -> Response:
        validate_public_destination(url)
        headers = {"Accept": accept, "User-Agent": USER_AGENT}
        if self.github_token and urlsplit(url).hostname == "api.github.com":
            headers["Authorization"] = f"Bearer {self.github_token}"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        request = Request(url, headers=headers, method="GET")
        try:
            with self.opener.open(request, timeout=self.timeout) as handle:
                final_url = handle.geturl()
                validate_public_destination(final_url)
                return Response(
                    url=final_url,
                    status=int(handle.status),
                    headers={str(k).lower(): str(v) for k, v in handle.headers.items()},
                    body=read_bounded(handle),
                )
        except HTTPError as exc:
            final_url = exc.geturl() or url
            validate_public_destination(final_url)
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
