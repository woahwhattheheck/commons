"""Optional standard-library Slack Web API READ adapter. No writes or retries.

Use installation metadata from your existing trusted adapter for app/workspace.
Credentials are held only in this object, not in the shared request or database.
The native ChatGPT Slack connector is not transparently replaced by this module.
"""
from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from .core import InvalidInput, Page, ProviderFailure, RateLimited, ReadRequest, strict_loads

# These are the implemented read operations, not a generic arbitrary-method proxy.
READ_METHODS = {
    "conversations.list": {"cursor", "limit", "types", "exclude_archived", "team_id"},
    "conversations.history": {"channel", "cursor", "limit", "oldest", "latest", "inclusive", "include_all_metadata"},
    "conversations.replies": {"channel", "ts", "cursor", "limit", "oldest", "latest", "inclusive", "include_all_metadata"},
    "conversations.info": {"channel", "include_locale", "include_num_members"},
    "users.info": {"user", "include_locale"},
    "users.list": {"cursor", "limit", "include_locale", "team_id"},
}
LISTS = {"conversations.list": "channels", "conversations.history": "messages",
         "conversations.replies": "messages", "users.list": "members"}


def retry_after_ms(raw: Any, *, fallback_ms: int = 60_000) -> tuple[int, bool]:
    """Slack documents integer seconds. Malformed/missing hints stay explicit.

    The fallback is client policy, not a claim about the provider's actual reset.
    A valid delay is never capped down to the client's preferred wait duration.
    """
    if type(fallback_ms) is not int or not 1 <= fallback_ms <= 86_400_000:
        raise InvalidInput("invalid fallback cooldown")
    if type(raw) is str and re.fullmatch(r"[0-9]+", raw.strip()):
        normalized = raw.strip().lstrip("0") or "0"
        if len(normalized) <= 12:
            return int(normalized) * 1000, True
        # Never turn an out-of-range, but numeric, provider delay into a shorter
        # ordinary fallback. This embargo exceeds the broker's supported clock
        # range, so it cannot silently expire within that range.
        return 9_000_000_000_000_000, False
    return fallback_ms, False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Keep bearer credentials from following redirects to another origin."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SlackReader:
    def __init__(self, *, token: str, app: str, workspace: str,
                 visibility_epoch: str, timeout_s: int = 10,
                 max_response_bytes: int = 1_000_000,
                 transport: Callable[..., Any] | None = None) -> None:
        if type(token) is not str or not token or any(c in token for c in "\r\n"):
            raise InvalidInput("nonempty adapter credential required")
        if type(timeout_s) is not int or not 1 <= timeout_s <= 120:
            raise InvalidInput("invalid read timeout")
        if type(max_response_bytes) is not int or not 128 <= max_response_bytes <= 16_000_000:
            raise InvalidInput("invalid response size limit")
        if type(visibility_epoch) is not str or not visibility_epoch or len(visibility_epoch) > 256:
            raise InvalidInput("visibility_epoch is required")
        self._token, self.app, self.workspace = token, app, workspace
        # Rotating credentials or adapter-observed permission epochs separate cache
        # entries, even when an upstream caller supplies identical request params.
        self._scope = hashlib.sha256((token + "\0" + visibility_epoch).encode()).hexdigest()
        self.timeout_s, self.max_response_bytes = timeout_s, max_response_bytes
        self.transport = transport or urllib.request.build_opener(NoRedirect()).open
        self.request("conversations.list", {})  # Validate routing metadata now.

    def request(self, method: str, params: dict[str, Any]) -> ReadRequest:
        if method not in READ_METHODS:
            raise InvalidInput("Slack read operation is not implemented")
        if type(params) is not dict or set(params) - READ_METHODS[method]:
            raise InvalidInput("unsupported Slack read parameters")
        if method in ("conversations.history", "conversations.replies", "conversations.info") and not params.get("channel"):
            raise InvalidInput("channel is required")
        if method == "conversations.replies" and not params.get("ts"):
            raise InvalidInput("thread timestamp is required")
        if method == "users.info" and not params.get("user"):
            raise InvalidInput("user is required")
        for key, value in params.items():
            if type(value) not in (str, int, bool):
                raise InvalidInput("Slack query parameters must be scalar")
            if key == "limit" and (type(value) is not int or not 1 <= value <= 1000):
                raise InvalidInput("limit must be an integer from 1 to 1000")
            if key in {"oldest", "latest", "ts"} and (type(value) is not str or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,6})?", value)):
                raise InvalidInput("Slack timestamps must remain decimal strings")
            if key in {"channel", "user", "team_id"} and (type(value) is not str or not re.fullmatch(r"[A-Z][A-Z0-9]{1,64}", value)):
                raise InvalidInput("invalid Slack identifier")
            if key in {"inclusive", "exclude_archived", "include_all_metadata", "include_locale", "include_num_members"} and type(value) is not bool:
                raise InvalidInput("Slack boolean parameter must be a bool")
        return ReadRequest.make(provider="slack-web-api", app=self.app,
            workspace=self.workspace, method=method, access_scope=self._scope, params=params)

    def __call__(self, request: ReadRequest) -> Page:
        # Fail before opening a connection if a caller transplants another token's
        # request or changes a method/parameter outside the implemented reader.
        own = self.request(request.method, request.params)
        if own != request:
            raise InvalidInput("request does not belong to this adapter installation/scope")
        params = {key: ("true" if value else "false") if type(value) is bool else str(value)
                  for key, value in request.params.items()}
        url = "https://slack.com/api/" + request.method + "?" + urllib.parse.urlencode(params)
        outgoing = urllib.request.Request(url, headers={"Authorization": "Bearer " + self._token,
            "Accept": "application/json", "User-Agent": "Commons-Read-Coalescer/1"}, method="GET")
        try:
            with self.transport(outgoing, timeout=self.timeout_s) as response:
                # Never follow successful-looking non-Slack bodies into cache.
                status = response.status
                headers = response.headers
                raw = response.read(self.max_response_bytes + 1)
        except urllib.error.HTTPError as exc:
            # Do not retain the URL, response body, or raw credential-bearing errors.
            try:
                if exc.code == 429:
                    delay, known = retry_after_ms(exc.headers.get("Retry-After"))
                    error = RateLimited(delay)
                    if not known:
                        error.code = "RATE_LIMITED_RETRY_AFTER_UNKNOWN"
                    raise error from None
                raise ProviderFailure("HTTP_ERROR") from None
            finally:
                exc.close()
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ProviderFailure("READ_TRANSPORT_ERROR") from None
        if status == 429:
            delay, known = retry_after_ms(headers.get("Retry-After"))
            error = RateLimited(delay)
            if not known:
                error.code = "RATE_LIMITED_RETRY_AFTER_UNKNOWN"
            raise error
        if status != 200:
            raise ProviderFailure("HTTP_ERROR")
        if len(raw) > self.max_response_bytes:
            raise ProviderFailure("RESPONSE_TOO_LARGE")
        try:
            body = strict_loads(raw, self.max_response_bytes)
        except InvalidInput:
            raise ProviderFailure("INVALID_PROVIDER_JSON") from None
        if type(body) is not dict or type(body.get("ok")) is not bool:
            raise ProviderFailure("INVALID_PROVIDER_RESPONSE")
        if body["ok"] is False:
            if body.get("error") in ("ratelimited", "rate_limited"):
                delay, known = retry_after_ms(headers.get("Retry-After"))
                error = RateLimited(delay)
                if not known:
                    error.code = "RATE_LIMITED_RETRY_AFTER_UNKNOWN"
                raise error
            raise ProviderFailure("SLACK_API_ERROR")
        if request.method not in LISTS:
            field = "user" if request.method == "users.info" else "channel"
            if type(body.get(field)) is not dict:
                raise ProviderFailure("INVALID_PROVIDER_RESPONSE")
            return Page(body, collection_end=None)
        if type(body.get(LISTS[request.method])) is not list:
            raise ProviderFailure("INVALID_PROVIDER_RESPONSE")
        metadata = body.get("response_metadata")
        if metadata is not None and type(metadata) is not dict:
            raise ProviderFailure("INVALID_PROVIDER_RESPONSE")
        raw_cursor = metadata.get("next_cursor") if metadata is not None else None
        if raw_cursor is not None and type(raw_cursor) is not str:
            raise ProviderFailure("INVALID_PROVIDER_RESPONSE")
        # Cursors are opaque: forward every nonempty value byte-for-byte.
        cursor = raw_cursor if raw_cursor else None
        has_more = body.get("has_more")
        if has_more is not None and type(has_more) is not bool:
            raise ProviderFailure("INVALID_PROVIDER_RESPONSE")
        if cursor:
            # has_more can describe time-window pagination independently. A real
            # next_cursor is authoritative that another cursor page is available.
            return Page(body, collection_end=False, next_cursor=cursor)
        if has_more is True:
            # Some methods permit timestamp pagination. Do not invent its continuation.
            return Page(body, collection_end=False)
        if has_more is False or raw_cursor == "":
            return Page(body, collection_end=True)
        return Page(body, collection_end=None)
