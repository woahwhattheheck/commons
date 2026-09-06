"""Private Slack/GitHub tools shared by model and shell harnesses.

No server or provider credentials are created here. Slack uses the existing
encrypted Grok Slack vault reader, and GitHub uses gh's existing keyring.
The catalog is composed into the existing local Gemini tool gateway only.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from threading import BoundedSemaphore, Thread
from time import monotonic
from typing import Any

from commons_publication_policy import require_publication


class EquipmentError(RuntimeError):
    pass


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


def _string(args: dict, key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EquipmentError(f"{key} must be a nonempty string")
    return value


def _repo(args: dict) -> str:
    repo = _string(args, "repository")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise EquipmentError("repository must be owner/name")
    return repo


def _quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


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


def _schema(name: str, description: str, required: dict[str, str], optional: dict[str, Any] | None = None) -> dict:
    properties = {k: {"type": v} for k, v in required.items()}
    for k, v in (optional or {}).items():
        properties[k] = {"type": v} if isinstance(v, str) else v
    return {"name": name, "description": description, "inputSchema": {"type": "object", "properties": properties, "required": list(required)}}


_TOKEN_POOL_PROVIDERS = ("grokbot", "cursor", "claude", "codex", "gemini_code_assist", "antigravity")
_TOKEN_POOL_BATCH_WAIT_SECONDS = 45.0
_TOKEN_POOL_BATCH_SLOTS = BoundedSemaphore(4)


def _token_pool_status_tool() -> dict:
    tool = _schema(
        "token_pool_status",
        "Read provider quota without starting model work or spending/resetting capacity. "
        "Use provider for one pool or providers for a batch of 1-4 distinct names. "
        "Batches preserve requested order and each outcome, wait at most 45 seconds, "
        "and share four active reader slots per process. Missing values stay null. "
        "Antigravity polling renews its existing grant only when expired and synchronizes shared custody. "
        "Omit both selectors for the original GrokBot result shape.",
        {},
        {"provider": {"type": "string", "enum": list(_TOKEN_POOL_PROVIDERS)},
         "providers": {"type": "array", "minItems": 1, "maxItems": 4, "uniqueItems": True,
                       "items": {"type": "string", "enum": list(_TOKEN_POOL_PROVIDERS)}}},
    )
    tool["inputSchema"]["not"] = {"required": ["provider", "providers"]}
    return tool


TOOLS = [
    _token_pool_status_tool(),
    _schema("credential_references", "Discover credential references, configured sources, and populated/empty Claude MCP entries. Returns metadata only, equally for newcomers.", {}),
    _schema("credential_retrieve_sealed", "Retrieve an actual credential encrypted to the requester's ephemeral public key. Keep the private key in the requesting runtime; only ciphertext enters this road.", {"credential_ref": "string", "recipient_public_key": "string", "transfer_id": "string", "request_id": "string", "call_id": "string"}),
    _schema("slack_read_channel", "Read a Slack channel using existing workspace access. Follow next_cursor for remaining pages.", {"channel_id": "string"}, {"oldest": "string", "latest": "string", "cursor": "string", "limit": "integer"}),
    _schema("slack_read_thread", "Read a Slack thread. Follow next_cursor for remaining replies.", {"channel_id": "string", "thread_ts": "string"}, {"cursor": "string", "limit": "integer"}),
    _schema("slack_post_message", "Post a message through the existing workspace app. Return its timestamp and permalink. Preserve explicit model/role attribution in text.", {"channel_id": "string", "text": "string"}, {"thread_ts": "string"}),
    _schema("github_read_file", "Read a UTF-8 source file and resolved blob SHA through the existing gh account. Set ref to pin a version.", {"repository": "string", "path": "string"}, {"ref": "string"}),
    _schema("github_read_issue", "Read a GitHub issue and one comment page; use comment_page for further pages.", {"repository": "string", "issue_number": "integer"}, {"comment_page": "integer"}),
    _schema("github_read_pull_request", "Read PR state, head/base SHAs, changed files and checks. Use page for further file pages.", {"repository": "string", "pull_number": "integer"}, {"page": "integer"}),
    _schema("github_create_branch", "Create a branch from base_ref (default main), resolving its commit internally. base_sha remains a compatible override and also accepts a ref. Returns an existing branch only when its head matches the resolved base; never moves an existing branch.", {"repository": "string", "branch": "string"}, {"base_ref": {"type": "string", "default": "main", "description": "Source branch, tag, ref, or commit; resolved internally. Defaults to main."}, "base_sha": {"type": "string", "description": "Compatibility override for base_ref: an existing commit SHA or ref."}}),
    _schema("github_commit_files", "Commit UTF-8 files to an existing branch, comparing expected_head first. Supply full file contents. Returns commit SHA; never force-updates a ref.", {"repository": "string", "branch": "string", "expected_head": "string", "message": "string"}, {"files": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}}),
    _schema("github_create_pull_request", "Open a useful PR for existing task work. Returns an existing open PR for the same head/base on retry.", {"repository": "string", "head": "string", "base": "string", "title": "string", "body": "string"}, {"draft": "boolean"}),
    _schema("github_merge_pull_request", "Merge an authorized reviewed PR with expected head SHA. GitHub enforces branch rules. Returns provider result, not an assumed success.", {"repository": "string", "pull_number": "integer", "expected_head": "string"}, {"merge_method": "string"}),
]


class ServiceEquipment:
    def __init__(self, *, gh: str = "gh", slack_token_loader=None, gh_runner=None, opener=None, credential_sources=None):
        self.gh = gh
        self.slack_token_loader = slack_token_loader or self._load_slack_token
        self.gh_runner = gh_runner or subprocess.run
        self.opener = opener or urllib.request.urlopen
        self.credential_sources = credential_sources

    @staticmethod
    def _load_slack_token() -> str:
        # Consume the current encrypted store in memory. Never inject into model
        # prompts, environment, another vault, or a Gemini provider profile.
        try:
            from integrations.grok_slack.handoff import default_vault_path, read_vault
            return read_vault(default_vault_path())["bot_token"]
        except Exception as exc:
            raise EquipmentError("existing Slack vault unavailable; inspect the existing Grok Slack custody route") from exc

    def tools(self, **_kwargs) -> list[dict]:
        return TOOLS.copy()

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
            return {"ok": False, "error": "slack_http_error", "status": exc.code, "retry_after": exc.headers.get("Retry-After")}
        except Exception as exc:
            raise EquipmentError("Slack transport failed; effect may be unknown for writes") from exc
        return redacted(result)

    def github(self, endpoint: str, *, method: str = "GET", payload: dict | None = None) -> Any:
        command = [self.gh, "api", "--hostname", "github.com", "--method", method, endpoint]
        if payload is not None:
            command += ["--input", "-"]
        try:
            result = self.gh_runner(command, input=json.dumps(payload) if payload is not None else None,
                text=True, encoding="utf-8", capture_output=True, timeout=90,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EquipmentError("existing gh transport unavailable; write effect may be unknown") from exc
        if result.returncode:
            # Provider errors can echo submitted data; return only structured
            # status/message after redaction, never command/environment details.
            try:
                error = json.loads(result.stdout)
                message = redacted(error.get("message", "GitHub request failed"))
            except (ValueError, TypeError):
                message = "GitHub request failed through existing gh account"
            raise EquipmentError(str(message))
        if not result.stdout.strip():
            return {}
        return redacted(json.loads(result.stdout))

    def call(self, name: str, arguments: dict) -> dict:
        try:
            result = self._call(name, arguments)
            return {"isError": isinstance(result, dict) and result.get("ok") is False, "result": redacted(result)}
        except Exception as exc:
            return {"isError": True, "error": type(exc).__name__, "message": redacted(str(exc))}

    def _token_pool_batch(self, selected: list[str]) -> dict:
        observed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        deadline = monotonic() + _TOKEN_POOL_BATCH_WAIT_SECONDS
        results: list[dict | None] = [None] * len(selected)
        completed: Queue = Queue()
        pending: set[int] = set()

        def failure(provider: str, status: str, error_class: str, **fields) -> dict:
            return {"schema": "commons.token_pool_status.v1", "provider": provider,
                    "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "ok": False, "status": status, "pools": [],
                    "error": {"class": error_class, "code": "token_pool_status_" + status},
                    **fields}

        def read_one(index: int, provider: str) -> None:
            try:
                outcome = self._call("token_pool_status", {"provider": provider})
                if not isinstance(outcome, dict):
                    outcome = failure(provider, "error", "UnexpectedPayloadType")
            except Exception as exc:
                outcome = failure(provider, "error", type(exc).__name__)
            finally:
                # A caller timeout does not cancel the reader or release its slot.
                _TOKEN_POOL_BATCH_SLOTS.release()
            completed.put((index, outcome))

        for index, provider in enumerate(selected):
            if not _TOKEN_POOL_BATCH_SLOTS.acquire(blocking=False):
                results[index] = failure(provider, "busy", "BatchReadersBusy", read_started=False)
                continue
            pending.add(index)
            try:
                Thread(target=read_one, args=(index, provider), daemon=True).start()
            except Exception as exc:
                _TOKEN_POOL_BATCH_SLOTS.release()
                pending.remove(index)
                results[index] = failure(provider, "error", type(exc).__name__, read_started=False)

        while pending:
            try:
                # Once the deadline passes, still drain already-queued outcomes.
                index, outcome = completed.get(timeout=max(0.0, deadline - monotonic()))
            except Empty:
                break
            results[index] = outcome
            pending.remove(index)
        for index in pending:
            results[index] = failure(selected[index], "timeout", "TimeoutError",
                                     read_started=True, reader_may_still_be_running=True)

        return {"schema": "commons.token_pool_status_batch.v1", "observed_at": observed_at,
                "ok": all(isinstance(result, dict) and result.get("ok") is True for result in results),
                "results": results}

    def _call(self, name: str, a: dict) -> dict:
        if name == "token_pool_status":
            if "provider" in a and "providers" in a:
                raise EquipmentError("Use provider or providers, not both")
            if "providers" in a:
                selected = a["providers"]
                if (not isinstance(selected, list) or not 1 <= len(selected) <= 4
                        or any(not isinstance(provider, str) or provider not in _TOKEN_POOL_PROVIDERS
                               for provider in selected)
                        or len(set(selected)) != len(selected)):
                    raise EquipmentError("providers must contain 1-4 distinct supported names")
                return self._token_pool_batch(list(selected))
            provider = a.get("provider", "grokbot")
            if provider == "codex":
                from .codex_pool import poll_codex_pool
                return poll_codex_pool()
            from .token_pools import poll_token_pools, poll_cursor_pool, poll_claude_pool
            from .gemini_code_assist import poll_gemini_code_assist_pool
            from .antigravity_pool import poll_antigravity_pool
            readers = {"grokbot": poll_token_pools, "cursor": poll_cursor_pool,
                       "claude": poll_claude_pool, "gemini_code_assist": poll_gemini_code_assist_pool,
                       "antigravity": poll_antigravity_pool}
            if not isinstance(provider, str) or provider not in readers:
                raise EquipmentError("provider must be grokbot, cursor, claude, codex, gemini_code_assist or antigravity")
            from .credential_transfer import CredentialSources
            sources = self.credential_sources or CredentialSources(gh=self.gh, gh_runner=self.gh_runner)
            recovery = None
            if provider == "antigravity":
                try:
                    from .antigravity_grant import ensure_antigravity_grant
                    recovery = ensure_antigravity_grant(sources=sources)
                except Exception:
                    recovery = {
                        "provider": "antigravity", "operation": "existing_grant_renewal",
                        "ok": False, "status": "unavailable", "refreshed": False,
                        "primary_custody_updated": None, "shared_custody_updated": None,
                        "expires_at": None,
                        "error": {"code": "existing_grant_recovery_failed", "http_status": None},
                    }
            outcome = readers[provider](credential_reader=sources.read)
            # Custody maintenance must not hide a usable primary quota result.
            if recovery and (not recovery.get("ok") or recovery.get("refreshed")
                             or recovery.get("shared_custody_updated")):
                outcome["credential_recovery"] = recovery
            return outcome
        if name == "credential_references":
            from .credential_transfer import credential_references
            return credential_references(self.credential_sources)
        if name == "credential_retrieve_sealed":
            from .credential_transfer import CredentialSources
            sources = self.credential_sources or CredentialSources(gh=self.gh, gh_runner=self.gh_runner)
            return sources.retrieve_sealed(a)
        if name == "slack_read_channel":
            p = {"channel": _string(a, "channel_id"), "limit": min(100, max(1, int(a.get("limit", 50))))}
            p.update({k: a[k] for k in ("oldest", "latest", "cursor") if a.get(k)})
            return self.slack("conversations.history", p)
        if name == "slack_read_thread":
            p = {"channel": _string(a, "channel_id"), "ts": _string(a, "thread_ts"), "limit": min(100, max(1, int(a.get("limit", 50))))}
            if a.get("cursor"):
                p["cursor"] = a["cursor"]
            return self.slack("conversations.replies", p)
        if name == "slack_post_message":
            p = {"channel": _string(a, "channel_id"), "text": _string(a, "text"), "unfurl_links": False, "unfurl_media": False, "parse": "none"}
            if a.get("thread_ts"):
                p["thread_ts"] = a["thread_ts"]
            result = self.slack("chat.postMessage", p)
            if result.get("ok"):
                link = self.slack("chat.getPermalink", {"channel": result["channel"], "message_ts": result["ts"]})
                return {"ok": True, "channel": result["channel"], "ts": result["ts"], "permalink": link.get("permalink"), "text": result.get("message", {}).get("text")}
            return result
        repo = _repo(a)
        root = "repos/" + repo
        if name == "github_read_file":
            path = "/".join(_quote(part) for part in _string(a, "path").split("/"))
            endpoint = root + "/contents/" + path
            if a.get("ref"):
                endpoint += "?ref=" + _quote(a["ref"])
            value = self.github(endpoint)
            if not isinstance(value, dict) or value.get("type") != "file":
                raise EquipmentError("path is not a file; supply an exact source path")
            content = base64.b64decode(value.get("content", "")).decode("utf-8")
            return {"repository": repo, "path": value["path"], "sha": value["sha"], "url": value["html_url"], "content": redacted(content), "size": value.get("size")}
        if name == "github_read_issue":
            number = int(a["issue_number"])
            page = max(1, int(a.get("comment_page", 1)))
            issue = self.github(f"{root}/issues/{number}")
            comments = self.github(f"{root}/issues/{number}/comments?per_page=100&page={page}")
            return {"issue": issue, "comments": comments, "comment_page": page, "may_have_more_comments": len(comments) == 100}
        if name == "github_read_pull_request":
            number = int(a["pull_number"])
            page = max(1, int(a.get("page", 1)))
            pr = self.github(f"{root}/pulls/{number}")
            files = self.github(f"{root}/pulls/{number}/files?per_page=100&page={page}")
            sha = pr["head"]["sha"]
            return {"pull_request": pr, "files": files, "may_have_more_files": len(files) == 100,
                "checks": self.github(f"{root}/commits/{sha}/check-runs"),
                "status": self.github(f"{root}/commits/{sha}/status")}
        if name == "github_create_branch":
            branch = _string(a, "branch")
            # A caller names the source; GitHub resolves it. Keep explicit
            # commit callers compatible, including their existing call shape,
            # and accept legacy base_sha='main' without an extra peer round trip.
            if "base_sha" in a:
                base = _string(a, "base_sha").strip()
            elif "base_ref" in a:
                base = _string(a, "base_ref").strip()
            else:
                base = "main"
            if re.fullmatch(r"[0-9a-fA-F]{40}", base):
                sha = base.lower()
            else:
                # The commits endpoint documents heads/... and tags/...;
                # retain that namespace when given a fully qualified Git ref.
                if base.startswith(("refs/heads/", "refs/tags/")):
                    base = base[5:]
                resolved = self.github(root + "/commits/" + _quote(base))
                sha = resolved.get("sha") if isinstance(resolved, dict) else None
                if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
                    raise EquipmentError("GitHub did not resolve the source ref to a commit")
            try:
                found = self.github(root + "/git/ref/heads/" + _quote(branch))
            except EquipmentError:
                found = None
            if found:
                if found["object"]["sha"] != sha:
                    raise EquipmentError("existing branch has a different head")
                return {"created": False, **found}
            return self.github(root + "/git/refs", method="POST", payload={"ref": "refs/heads/" + branch, "sha": sha})
        if name == "github_commit_files":
            branch, expected = _string(a, "branch"), _string(a, "expected_head")
            ref = self.github(root + "/git/ref/heads/" + _quote(branch))
            if ref["object"]["sha"] != expected:
                raise EquipmentError("branch head changed; read current head and reconcile files")
            parent = self.github(root + "/git/commits/" + _quote(expected))
            files = a.get("files")
            if not isinstance(files, list) or not files:
                raise EquipmentError("files must contain the useful task changes")
            tree = [{"path": _string(f, "path"), "mode": "100644", "type": "blob", "content": _string(f, "content")} for f in files]
            made_tree = self.github(root + "/git/trees", method="POST", payload={"base_tree": parent["tree"]["sha"], "tree": tree})
            commit = self.github(root + "/git/commits", method="POST", payload={"message": _string(a, "message"), "tree": made_tree["sha"], "parents": [expected]})
            updated = self.github(root + "/git/refs/heads/" + _quote(branch), method="PATCH", payload={"sha": commit["sha"], "force": False})
            return {"commit_sha": commit["sha"], "branch": branch, "ref": updated, "url": commit.get("html_url")}
        if name == "github_create_pull_request":
            owner = repo.split("/")[0]
            head, base = _string(a, "head"), _string(a, "base")
            query = urllib.parse.urlencode({"state": "open", "head": head if ":" in head else owner + ":" + head, "base": base})
            existing = self.github(root + "/pulls?" + query)
            if existing:
                return {"created": False, "pull_request": existing[0]}
            return self.github(root + "/pulls", method="POST", payload={"head": head, "base": base, "title": _string(a, "title"), "body": _string(a, "body"), "draft": bool(a.get("draft", False))})
        if name == "github_merge_pull_request":
            return self.github(f"{root}/pulls/{int(a['pull_number'])}/merge", method="PUT", payload={"sha": _string(a, "expected_head"), "merge_method": a.get("merge_method", "squash")})
        raise EquipmentError("unknown equipment tool: " + name)


class CombinedCatalog:
    """Add private local equipment without publishing it to the public MCP."""
    def __init__(self, commons, services=None):
        self.commons = commons
        self.services = services or ServiceEquipment()
        self.extensions = []

    def tools(self, **kwargs):
        return self.commons.tools(**kwargs) + self.services.tools() + [tool for extension in self.extensions for tool in extension.tools()]

    def call(self, name, arguments):
        for extension in self.extensions:
            if name in {tool["name"] for tool in extension.tools()}:
                return extension.call(name, arguments)
        if name in {tool["name"] for tool in self.services.tools()}:
            return self.services.call(name, arguments)
        return self.commons.call(name, arguments)


class _EmptyCommonsCatalog:
    """CLI has no public Commons MCP sidecar; keep CombinedCatalog shape."""

    def tools(self, **_kwargs):
        return []

    def call(self, name, arguments):
        raise EquipmentError("unknown equipment tool: " + str(name))


def build_cli_catalog(*, grokbot_base_url: str | None = None, claude_headless_root: str | None = None):
    """Slack/GitHub services + GrokBot lifecycle (G2) + headless Claude (C1), no public MCP tools."""
    from integrations.shared_equipment.peers import ClaudeHeadlessEquipment, GrokBotEquipment

    catalog = CombinedCatalog(_EmptyCommonsCatalog())
    if grokbot_base_url:
        catalog.extensions.append(GrokBotEquipment(grokbot_base_url))
    else:
        catalog.extensions.append(GrokBotEquipment())
    catalog.extensions.append(ClaudeHeadlessEquipment(claude_headless_root))
    return catalog


# Non-secret harness inventory. Same for every peer; not an allowlist.
HARNESS_ROADS = [
    {
        "road_id": "owner_pc_shared_equipment",
        "kind": "loopback_http",
        "base_url": "http://127.0.0.1:8878",
        "discover": "GET /v1/tools",
        "call": "POST /v1/tools/call",
        "note": "Stable request_id + call_id. Service custody stays in existing host stores.",
    },
    {
        "road_id": "owner_pc_grokbot_control",
        "kind": "grokbot_control",
        "base_url": "http://127.0.0.1:8881",
        "discover": "python -m integrations.shared_equipment.services manifest",
        "call": "grokbot_* tools via catalog/call",
        "note": "GrokBot pools only. Occupant field is optional metadata on the pool run, not role_id.",
    },
    {
        "road_id": "workspace_shared_equipment",
        "kind": "slack_request_return",
        "channel_id": "C0BU51F1PL3",
        "thread_ts": "1788567066.179399",
        "discover": "equipment_capability_manifest envelope",
        "call": "commons_equipment_request / commons_equipment_result",
        "note": "Same operation schemas over the workspace connector. No secret material in envelopes.",
    },
]

CREDENTIAL_CUSTODY = [
    {
        "service": "slack",
        "custody": "existing_encrypted_vault",
        "loader": "integrations.grok_slack.handoff.read_vault",
        "bytes_in_model_context": False,
    },
    {
        "service": "github",
        "custody": "existing_gh_os_keyring",
        "transport": "gh api --hostname github.com",
        "bytes_in_model_context": False,
    },
    {
        "service": "grokbot",
        "custody": "loopback_control",
        "base_url_default": "http://127.0.0.1:8881",
        "bytes_in_model_context": False,
    },
]


def build_capability_manifest(*, catalog=None, peer: str | None = None) -> dict:
    """Inventory callable operations + roads without secret bytes.

    ``peer`` is accepted and ignored so newcomers and legacy peers share one
    discovery surface. Transferable roles describe responsibility only; they
    never gate this manifest.
    """
    del peer  # parity: label never changes the inventory
    equipment = catalog or build_cli_catalog()
    operations = []
    for tool in equipment.tools():
        name = tool["name"]
        operations.append(
            {
                "operation_id": name,
                "name": name,
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {"type": "object"}),
            }
        )
    operations.sort(key=lambda row: row["operation_id"])
    return {
        "schema": "commons.shared_equipment.capability_manifest.v1",
        "same_operations_for_every_peer": True,
        "peer_label_does_not_change_inventory": True,
        "credential_bytes_in_manifest": False,
        "peer_argument_ignored": True,
        "credential_custody": list(CREDENTIAL_CUSTODY),
        "roads": [dict(road) for road in HARNESS_ROADS],
        "operations": operations,
        "operation_count": len(operations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("catalog", "call", "manifest"))
    parser.add_argument(
        "--grokbot-control",
        default=None,
        help="Override GrokBot control base URL (default http://127.0.0.1:8881)",
    )
    parser.add_argument(
        "--claude-headless-root",
        default=None,
        help="Runs root for headless Claude (default ~/.claude/commons_headless or CLAUDE_HEADLESS_ROOT)",
    )
    args = parser.parse_args()
    equipment = build_cli_catalog(
        grokbot_base_url=args.grokbot_control,
        claude_headless_root=args.claude_headless_root,
    )
    if args.operation == "manifest":
        result = build_capability_manifest(catalog=equipment)
    elif args.operation == "catalog":
        result = {"tools": equipment.tools()}
    else:
        request = json.load(sys.stdin)
        result = equipment.call(request["name"], request.get("arguments", {}))
    print(json.dumps(redacted(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


