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

class EquipmentError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        code="equipment_error",
        uncertain=False,
        http_status=None,
        retry_after=None,
        rate_limit_remaining=None,
        rate_limit_reset=None,
        rate_limit_resource=None,
        rate_limit_kind=None,
        incident=None,
        delivered=None,
        matched_fields=None,
        matched_terms=None,
        private_instruction=None,
    ):
        super().__init__(message)
        self.code = code
        self.uncertain = uncertain
        self.http_status = http_status
        self.retry_after = retry_after
        self.rate_limit_remaining = rate_limit_remaining
        self.rate_limit_reset = rate_limit_reset
        self.rate_limit_resource = rate_limit_resource
        self.rate_limit_kind = rate_limit_kind
        self.incident = incident
        self.delivered = delivered
        self.matched_fields = tuple(matched_fields or ())
        self.matched_terms = tuple(matched_terms or ())
        self.private_instruction = private_instruction


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

def _slack_publication_fields(payload: dict) -> dict[str, str]:
    """Select only final Slack-visible text, never IDs or action values."""
    fields: dict[str, str] = {}
    block_visible = {"text", "title", "alt_text", "label", "description", "initial_value"}
    attachment_visible = {
        "text", "title", "pretext", "fallback", "alt_text", "label",
        "description", "footer", "author_name",
    }

    def collect(value: Any, path: str, visible: set[str], parent: str) -> None:
        if isinstance(value, list):
            for index, item in enumerate(value):
                collect(item, f"{path}[{index}]", visible, parent)
            return
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if isinstance(item, str):
                if key in visible or (key == "value" and parent == "fields"):
                    fields[child] = item
            elif isinstance(item, (dict, list)):
                collect(item, child, visible, key)

    for key in ("text", "username"):
        if isinstance(payload.get(key), str):
            fields[key] = payload[key]
    if isinstance(payload.get("blocks"), (dict, list)):
        collect(payload["blocks"], "blocks", block_visible, "blocks")
    if isinstance(payload.get("attachments"), (dict, list)):
        collect(payload["attachments"], "attachments", attachment_visible, "attachments")
    return fields


def _slack_publication_text(payload: dict) -> str:
    return "\n".join(_slack_publication_fields(payload).values())


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
        if colon and key.lower() in {"retry-after", "x-ratelimit-remaining", "x-ratelimit-reset", "x-ratelimit-resource"}:
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

    def _slack_write_route_verified(self) -> bool:
        """Production remains read-only until sender identity/footer are verified."""
        return False

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
        read_method = method in {
            "conversations.history",
            "conversations.replies",
            "conversations.info",
            "files.info",
            "chat.getPermalink",
            "auth.test",
        }
        write_fields = {
            "chat.postMessage": {"channel", "text", "thread_ts", "unfurl_links", "unfurl_media", "parse"},
            "files.getUploadURLExternal": {"filename", "length"},
            "files.completeUploadExternal": {"files", "channel_id", "thread_ts", "initial_comment"},
        }
        if not read_method:
            allowed_fields = write_fields.get(method)
            if (allowed_fields is None or not isinstance(payload, dict)
                    or set(payload) - allowed_fields or any(
                        key in payload for key in ("username", "icon_emoji", "icon_url", "as_user", "user_name")
                    )):
                raise EquipmentError("Slack mutation has no exact internal field mapping",
                                     code="outbound_field_mapping_missing", uncertain=False,
                                     incident=False, delivered=False)
            verifier = getattr(self, "_slack_write_route_verified", None)
            destination = payload.get("channel_id") or payload.get("channel")
            # A caller that already applied the fixture verifier or destination
            # check records that once. Do not call the provider again for it.
            if getattr(self, "_slack_route_preverified", None) != destination:
                if not callable(verifier) or not verifier(destination):
                    raise EquipmentError(
                        "Slack write not delivered. The installed sender identity/footer "
                        "does not match the fixed authenticated internal workspace account.",
                        code="outbound_sender_identity_unverified",
                        uncertain=False,
                        incident=False,
                        delivered=False,
                        matched_fields=(),
                        matched_terms=(),
                        private_instruction="Read back the internal Slack sender and visible message fields before retrying.",
                    )
            # Internal TJLabs Slack is explicitly exempt from the public
            # Commons/GitHub publication classifier. Fixed account + exact
            # API fields control the transport; the handoff route validates
            # internal channel metadata and reads back the actual result.
        token = self.slack_token_loader()
        # Slack read methods accept query/form arguments, not consistently JSON.
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

    def slack_upload_bytes(self, upload_url: str, body: bytes) -> dict:
        """POST exact patch bytes to Slack's single-use signed upload URL."""
        parsed = urllib.parse.urlsplit(upload_url)
        if parsed.scheme != "https" or parsed.hostname != "files.slack.com" or parsed.username or parsed.password:
            raise EquipmentError("Slack returned an unsupported file upload host", code="slack_upload_url_invalid")
        request = urllib.request.Request(upload_url, data=body,
            headers={"Content-Type": "application/octet-stream", "Content-Length": str(len(body))}, method="POST")
        try:
            with self.opener(request, timeout=90) as response:
                status = int(response.status)
                response.read(256)
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            return {"ok": False, "error": "slack_upload_http_error", "status": status,
                    "uncertain": status not in (400, 401, 403, 404, 413, 429)}
        except Exception:
            raise EquipmentError("Slack file upload response unavailable; reconcile before retry",
                                 code="slack_upload_unconfirmed", uncertain=True) from None
        if status < 200 or status >= 300:
            return {"ok": False, "error": "slack_upload_http_error", "status": status,
                    "uncertain": status >= 500}
        return {"ok": True, "http_status": status, "bytes_uploaded": len(body)}

    def slack_download_file(self, file_info: dict, *, max_bytes: int = 10 * 1024 * 1024) -> bytes:
        """Read a shared Slack file in memory using the existing encrypted token."""
        url = file_info.get("url_private_download") or file_info.get("url_private")
        parsed = urllib.parse.urlsplit(url or "")
        if parsed.scheme != "https" or parsed.hostname not in {"files.slack.com", "slack-files.com"}:
            raise EquipmentError("Slack file has no supported private download URL", code="slack_file_url_invalid")
        token = self.slack_token_loader()
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token}, method="GET")
        try:
            with self.opener(request, timeout=45) as response:
                data = response.read(max_bytes + 1)
        except Exception:
            raise EquipmentError("Slack file readback unavailable", code="slack_file_read_failed") from None
        if len(data) > max_bytes:
            raise EquipmentError("Slack file exceeds the 10 MiB peer-read limit", code="slack_file_too_large")
        return data

    def github(self, endpoint: str, *, method: str = "GET", payload: dict | None = None) -> Any:
        # Writes need the same HTTP/cooldown evidence as reads. Keep --include
        # after `api` so existing --method/endpoint argument parsing stays valid.
        command = [self.gh, "api", "--include", "--hostname", "github.com", "--method", method, endpoint]
        if payload is not None:
            command += ["--input", "-"]
        try:
            result = self.gh_runner(command, input=json.dumps(payload) if payload is not None else None,
                text=True, encoding="utf-8", capture_output=True, timeout=90,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EquipmentError("existing gh transport unavailable; retain the operation ID before another write",
                                 code="github_transport_failed", uncertain=method != "GET") from None
        try:
            body, status, headers = _github_headers(result.stdout)
        except EquipmentError as exc:
            # An incomplete write response cannot establish whether it landed.
            exc.uncertain = method != "GET"
            raise
        if result.returncode or status is not None and status >= 400:
            # Preserve response rate evidence, never stderr, command or raw headers.
            error = None
            try:
                error = json.loads(body)
                message = redacted(error.get("message", "GitHub request failed")) if isinstance(error, dict) else "GitHub request failed"
            except (ValueError, TypeError):
                message = "GitHub request failed through existing gh account"
            if status is None and isinstance(error, dict) and error.get("message") == "Not Found":
                status = 404
            remaining = _header_integer(headers, "x-ratelimit-remaining")
            reset = _header_integer(headers, "x-ratelimit-reset")
            resource = headers.get("x-ratelimit-resource")
            if not isinstance(resource, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", resource):
                resource = None
            secondary = status in (403, 429) and any(term in str(message).lower()
                for term in ("secondary rate limit", "abuse detection mechanism"))
            # A 403 may carry Retry-After without quota exhaustion or the
            # standard secondary-limit prose. Preserve that provider deadline.
            limited = status == 429 or status == 403 and (
                remaining == 0 or secondary or bool(headers.get("retry-after")))
            kind = ("secondary" if secondary else "primary" if remaining == 0 else "unknown") if limited else None
            raise EquipmentError(str(message),
                code="github_rate_limited" if limited else "github_request_failed",
                uncertain=method != "GET", http_status=status,
                retry_after=headers.get("retry-after") if limited else None,
                rate_limit_remaining=remaining, rate_limit_reset=reset,
                rate_limit_resource=resource, rate_limit_kind=kind)
        if not body.strip():
            return {}
        try:
            return redacted(json.loads(body))
        except (ValueError, TypeError):
            raise EquipmentError("GitHub returned an invalid response", code="github_response_invalid",
                                 uncertain=method != "GET") from None
