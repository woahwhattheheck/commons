"""GitHub/Slack provider IO used by command-center collection.

Kept separate from CombinedCatalog so collectors do not close over CommandCenter
source catalogs or other kitchen-sink shared equipment.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from commons_publication_policy import require_publication


class EquipmentError(RuntimeError):
    def __init__(self, message, *, code="equipment_error", uncertain=False, http_status=None,
                 retry_after=None, rate_limit_remaining=None, rate_limit_reset=None):
        super().__init__(message)
        self.code = code
        self.uncertain = uncertain
        self.http_status = http_status
        self.retry_after = retry_after
        self.rate_limit_remaining = rate_limit_remaining
        self.rate_limit_reset = rate_limit_reset


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

_SECRET_KEYS = re.compile(r"^(authorization|cookie|set-cookie|password|access_token|refresh_token|bot_token|app_token|client_secret|private_key)$", re.I)
_SECRET_VALUES = re.compile(r"(?:xox[baprs]-[A-Za-z0-9-]+|xapp-[A-Za-z0-9-]+|gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|AIza[0-9A-Za-z_-]{30,})")


def redacted(value: Any) -> Any:
    """Keep credential-bearing provider fields out of model replies/journals."""
    if isinstance(value, dict):
        return {str(k): "[REDACTED]" if _SECRET_KEYS.fullmatch(str(k)) else redacted(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redacted(v) for v in value]
    if isinstance(value, str):
        return _SECRET_VALUES.sub("[REDACTED]", value)
    return value

def _slack_publication_text(payload: dict) -> str:
    """Collect displayed Slack prose, including blocks-only message edits."""
    parts: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key in {"text", "title", "pretext", "fallback", "alt_text", "value"} and isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, (dict, list)):
                    collect(item)

    collect({key: payload[key] for key in ("text", "blocks", "attachments") if key in payload})
    return "\n".join(parts)

def _github_headers(stdout):
    """Extract only retry evidence from gh --include; never expose raw headers."""
    match = re.match(r"^HTTP/[^\s]+[ \t]+([0-9]{3})(?:[^\r\n]*)\r?\n", stdout)
    if not match:
        return stdout, None, {}
    separator = re.search(r"\r?\n\r?\n", stdout)
    if separator is None:
        raise EquipmentError("GitHub returned incomplete response headers",
                             code="github_response_invalid", http_status=int(match.group(1)))
    headers = {}
    for line in stdout[match.end():separator.start()].splitlines():
        key, colon, value = line.partition(":")
        if colon and key.lower() in {"retry-after", "x-ratelimit-remaining", "x-ratelimit-reset"}:
            headers[key.lower()] = value.strip()
    return stdout[separator.end():], int(match.group(1)), headers


def _header_integer(headers, name):
    value = headers.get(name)
    return int(value) if isinstance(value, str) and re.fullmatch(r"[0-9]{1,12}", value) else None

class GitHubSlackEquipment:
    def __init__(self, *, gh: str = "gh", slack_token_loader=None, gh_runner=None, opener=None):
        self.gh = gh
        self.slack_token_loader = slack_token_loader or self._load_slack_token
        self.gh_runner = gh_runner or subprocess.run
        self.opener = opener or urllib.request.build_opener(_NoRedirect()).open

    @staticmethod
    def _load_slack_token() -> str:
        # Consume the current encrypted store in memory. Never inject into model
        # prompts, environment, another vault, or a Gemini provider profile.
        try:
            from integrations.grok_slack.handoff import default_vault_path, read_vault
            return read_vault(default_vault_path())["bot_token"]
        except Exception as exc:
            raise EquipmentError("existing Slack vault unavailable; inspect the existing Grok Slack custody route") from exc


    def slack(self, method: str, payload: dict) -> dict:
        if method in {"chat.postMessage", "chat.update", "chat.postEphemeral", "chat.scheduleMessage"}:
            require_publication(_slack_publication_text(payload))
        token = self.slack_token_loader()
        # Slack read methods accept query/form arguments, not consistently JSON.
        read_method = method in {"conversations.history", "conversations.replies", "chat.getPermalink", "auth.test"}
        url = "https://slack.com/api/" + method
        if read_method:
            url += "?" + urllib.parse.urlencode(payload)
        request = urllib.request.Request(url,
            data=None if read_method else json.dumps(payload).encode("utf-8"),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=utf-8"},
            method="GET" if read_method else "POST")
        try:
            with self.opener(request, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            status = exc.code
            retry_after = exc.headers.get("Retry-After") if exc.headers is not None else None
            exc.close()
            return {"ok": False, "error": "slack_http_error", "status": status,
                    "retry_after": retry_after,
                    "uncertain": not read_method and status not in (401, 403, 429)}
        except Exception:
            raise EquipmentError("Slack response unavailable; retain the operation ID before another write",
                                 code="slack_transport_failed", uncertain=not read_method) from None
        if not isinstance(result, dict):
            raise EquipmentError("Slack returned no result object",
                                 code="slack_response_invalid", uncertain=not read_method)
        # Slack documents these errors as possibly occurring after an effect.
        if not read_method and result.get("error") in ("internal_error", "fatal_error"):
            result["uncertain"] = True
        return redacted(result)

    def github(self, endpoint: str, *, method: str = "GET", payload: dict | None = None) -> Any:
        command = [self.gh, "api", "--hostname", "github.com", "--method", method, endpoint]
        if method == "GET":
            # After `api`, never immediately before endpoint: callers parse
            # endpoint as the token after --method.
            command.insert(2, "--include")
        if payload is not None:
            command += ["--input", "-"]
        try:
            result = self.gh_runner(command, input=json.dumps(payload) if payload is not None else None,
                text=True, encoding="utf-8", capture_output=True, timeout=90,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EquipmentError("existing gh transport unavailable; retain the operation ID before another write",
                                 code="github_transport_failed", uncertain=method != "GET") from None
        body, status, headers = _github_headers(result.stdout) if method == "GET" else (result.stdout, None, {})
        if result.returncode or status is not None and status >= 400:
            # Preserve response rate evidence, never stderr, command or raw headers.
            try:
                error = json.loads(body)
                message = redacted(error.get("message", "GitHub request failed")) if isinstance(error, dict) else "GitHub request failed"
            except (ValueError, TypeError):
                message = "GitHub request failed through existing gh account"
            remaining = _header_integer(headers, "x-ratelimit-remaining")
            reset = _header_integer(headers, "x-ratelimit-reset")
            secondary = status == 403 and any(term in str(message).lower()
                for term in ("secondary rate limit", "abuse detection mechanism"))
            limited = status == 429 or status == 403 and (remaining == 0 or secondary)
            raise EquipmentError(str(message),
                code="github_rate_limited" if limited else "github_request_failed",
                uncertain=method != "GET", http_status=status,
                retry_after=headers.get("retry-after") if limited else None,
                rate_limit_remaining=remaining, rate_limit_reset=reset)
        if not body.strip():
            return {}
        try:
            return redacted(json.loads(body))
        except (ValueError, TypeError):
            raise EquipmentError("GitHub returned an invalid response", code="github_response_invalid",
                                 uncertain=method != "GET") from None
