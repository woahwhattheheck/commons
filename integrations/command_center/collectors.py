"""Bounded read-only provider collection for the existing command center.

Configuration belongs in the private state directory. No account, channel, or
private observation is bundled here. Connector-fed sources enter WorkstreamStore
through ingest; this module does not imitate Gmail/Airtable/native connectors.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from time import monotonic
from urllib.parse import quote, urlencode

REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
HOUSEKEEPING = {"channel_join", "channel_leave", "channel_topic", "channel_purpose",
                "channel_name", "channel_archive", "channel_unarchive"}
UTC = timezone.utc


def now():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def timestamp(value):
    if value is None or value == "":
        return None
    try:
        if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", str(value)):
            return datetime.fromtimestamp(float(value), UTC).isoformat().replace("+00:00", "Z")
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z") if parsed.tzinfo else None
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def latest(items):
    values = [timestamp(item.get("updated_at")) for item in items]
    return max((value for value in values if value),
               key=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")), default=None)


def text(value, limit=4000):
    return str(value or "")[:limit]


def link(url):
    return [{"kind": "open", "label": "Open original", "url": url}] if url else []


class SourceFailure(RuntimeError):
    def __init__(self, code):
        self.code = re.sub(r"[^A-Za-z0-9_.:-]", "_", str(code))[:120]
        super().__init__(self.code)


class LiveCollectors:
    """Read providers through existing shared equipment and ingest source batches."""

    def __init__(self, store, config=None, equipment=None, clock=now, cancel_event=None):
        self.store, self.config, self.clock = store, config or {}, clock
        if not isinstance(self.config, dict):
            raise ValueError("Collector config must be an object.")
        self.github_config = self.config.get("github", {})
        self.slack_config = self.config.get("slack", {})
        self.documents = self.config.get("documents", [])
        if not isinstance(self.github_config, dict) or not isinstance(self.slack_config, dict):
            raise ValueError("github/slack config must be objects.")
        if not isinstance(self.documents, list):
            raise ValueError("documents config must be a list.")
        self.page_size = self._bound(self.config.get("page_size", 30), 1, 100)
        self.max_pages = self._bound(self.config.get("max_pages", 2), 1, 10)
        self.max_workers = self._bound(self.config.get("max_workers", 4), 1, 4)
        self.refresh_deadline_seconds = self._bound(self.config.get("refresh_deadline_seconds", 180), 1, 600)
        self.cancel_event, self.deadline = cancel_event, None
        self.lookback_days = self._bound(self.github_config.get("lookback_days", 14), 1, 90)
        if equipment is None:
            from integrations.shared_equipment.services import ServiceEquipment
            timeout = self._bound(self.config.get("request_timeout_seconds", 25), 1, 30)
            def bounded_runner(command, **kwargs):
                kwargs["timeout"] = min(timeout, kwargs.get("timeout", timeout))
                return subprocess.run(command, **kwargs)
            equipment = ServiceEquipment(gh_runner=bounded_runner)
        self.equipment = equipment

    @staticmethod
    def _bound(value, low, high):
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError("Collector bound must be an integer from %s to %s." % (low, high))
        return value

    def _source(self, source_id, provider, label, scope):
        return {"id": source_id, "provider": provider, "label": label,
                "sync_mode": "direct", "scope": scope, "stale_after_seconds": 900}

    def _batch(self, source, items, complete=True, notes=None, error=None):
        observed = self.clock()
        source = {**source, "observed_at": observed, "activity_as_of": latest(items),
                  "status": "error" if error and not items else ("degraded" if error else "live"),
                  "error": error, "coverage": {"complete": bool(complete and not error),
                  "pagination_remaining": not complete, "notes": notes or []}}
        payload = {"source": source, "items": items}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        return {"operation_id": "collect:" + digest, **payload}

    def _check_deadline(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise SourceFailure("refresh_cancelled")
        if self.deadline is not None and monotonic() >= self.deadline:
            raise SourceFailure("refresh_deadline_reached")

    def _safe(self, source, reader):
        try:
            self._check_deadline()
            return reader()
        except Exception as exc:
            # Provider messages may contain private request data; retain fixed codes.
            return self._batch(source, [], complete=False,
                               error=getattr(exc, "code", type(exc).__name__),
                               notes=["Read failed; retain previous source items and last good activity."])

    def _github(self, endpoint):
        self._check_deadline()
        return self.equipment.github(endpoint, method="GET")

    def _pages(self, endpoint, key=None):
        result, total, incomplete = [], None, False
        for page in range(1, self.max_pages + 1):
            suffix = "&" if "?" in endpoint else "?"
            response = self._github(endpoint + suffix + urlencode({"per_page": self.page_size, "page": page}))
            rows = response.get(key) if key and isinstance(response, dict) else response
            if not isinstance(rows, list):
                raise SourceFailure("github_response_shape")
            result.extend(rows)
            if isinstance(response, dict):
                if "total_count" in response:
                    total = response["total_count"]
                    if type(total) is not int or total < 0:
                        raise SourceFailure("github_pagination_shape")
                if ("incomplete_results" in response
                        and type(response["incomplete_results"]) is not bool):
                    raise SourceFailure("github_pagination_shape")
                incomplete = incomplete or bool(response.get("incomplete_results"))
            if len(rows) < self.page_size:
                # A short page cannot overrule an explicit larger result count.
                return result, not incomplete and (total is None or len(result) >= total)
        return result, not incomplete and isinstance(total, int) and len(result) >= total

    @staticmethod
    def _repository(value):
        if not isinstance(value, str) or not REPO.fullmatch(value):
            raise ValueError("Repository must be owner/name.")
        return value

    def _repository_batch(self, login):
        source = self._source("github:repositories", "GitHub", "Owned repositories", {"owner": login})
        rows, complete = self._pages("user/repos?affiliation=owner&sort=pushed&direction=desc")
        items = []
        for row in {row["full_name"]: row for row in rows}.values():
            repo = self._repository(row.get("full_name"))
            url = row.get("html_url", "https://github.com/" + repo)
            items.append({"id": "github:repo:" + repo, "kind": "repository",
                "title": repo, "status": "archived" if row.get("archived") else "active",
                "owner": row.get("owner", {}).get("login"), "project": repo,
                "updated_at": timestamp(row.get("pushed_at")),
                "activity_observed_at": timestamp(row.get("pushed_at")), "url": url,
                "summary": text(row.get("description")), "next_action": None,
                "refs": {"repository": repo, "default_branch": row.get("default_branch"),
                         "private": row.get("private"), "open_issues_count": row.get("open_issues_count")},
                "actions": link(url)})
        return self._batch(source, items, complete,
                           ["Repository catalog; active means not archived, not an executing job."])

    def _pull_requests(self, login):
        source = self._source("github:prs", "GitHub", "Open and recently updated pull requests",
                              {"author_or_owner": login})
        since = (datetime.now(UTC) - timedelta(days=self.lookback_days)).date().isoformat()
        rows, complete = {}, True
        for qualifier in ("author:" + login, "user:" + login):
            for window in ("is:open", "updated:>=" + since):
                found, page_complete = self._pages("search/issues?" + urlencode({
                    "q": "is:pr " + qualifier + " " + window, "sort": "updated", "order": "desc"}), "items")
                complete = complete and page_complete
                for item in found:
                    rows[str(item.get("id", item.get("html_url")))] = item
        items = []
        for row in rows.values():
            repo = str(row.get("repository_url", "")).removeprefix("https://api.github.com/repos/")
            self._repository(repo)
            number, url = row["number"], row.get("html_url")
            status = "merged" if row.get("pull_request", {}).get("merged_at") else row.get("state", "unknown")
            items.append({"id": "github:pr:" + repo + "#" + str(number), "kind": "pull_request",
                "title": text(row.get("title"), 500), "status": status,
                "owner": row.get("user", {}).get("login"), "project": repo,
                "updated_at": timestamp(row.get("updated_at")),
                "activity_observed_at": timestamp(row.get("updated_at")), "url": url,
                "summary": text(row.get("body")), "next_action": None,
                "refs": {"repository": repo, "number": number, "draft": row.get("draft"),
                         "assignees": [x.get("login") for x in row.get("assignees", [])],
                         "labels": [x.get("name") for x in row.get("labels", [])]},
                "actions": link(url)})
        return self._batch(source, items, complete,
                           ["Provider state is preserved; a closed PR without merged_at is not labeled merged."])

    def _actions(self, repo):
        source = self._source("github:actions:" + repo, "GitHub", repo + " builds", {"repository": repo})
        rows, complete = {}, True
        for status in ("in_progress", "queued", None):
            endpoint = "repos/" + repo + "/actions/runs" + ("?status=" + status if status else "")
            found, page_complete = self._pages(endpoint, "workflow_runs")
            complete = complete and page_complete
            for row in found:
                rows[str(row["id"])] = row
        items = []
        for row in rows.values():
            url = row.get("html_url")
            items.append({"id": "github:run:" + repo + ":" + str(row["id"]), "kind": "build",
                "title": text(row.get("display_title") or row.get("name"), 500),
                "status": row.get("conclusion") if row.get("status") == "completed" else row.get("status", "unknown"),
                "owner": row.get("actor", {}).get("login"), "project": repo,
                "updated_at": timestamp(row.get("updated_at")),
                "activity_observed_at": timestamp(row.get("updated_at")), "url": url,
                "summary": text(row.get("name"), 500), "next_action": None,
                "refs": {"run_id": row["id"], "run_attempt": row.get("run_attempt"),
                         "head_sha": row.get("head_sha"), "head_branch": row.get("head_branch"),
                         "provider_status": row.get("status"), "conclusion": row.get("conclusion")},
                "actions": link(url)})
        return self._batch(source, items, complete,
                           ["Active/queued runs plus bounded recent history; pagination caps stay visible."])

    def _slack(self, channel):
        channel_id, label = channel["id"], channel.get("label", channel["id"])
        source = self._source("slack:" + channel_id, "Slack", label, {"channel_id": channel_id})
        rows, cursor, complete = [], "", False
        for _ in range(self.max_pages):
            payload = {"channel": channel_id, "limit": self.page_size}
            if cursor:
                payload["cursor"] = cursor
            self._check_deadline()
            response = self.equipment.slack("conversations.history", payload)
            if not isinstance(response, dict) or response.get("ok") is not True:
                raise SourceFailure(response.get("error", "slack_response_shape") if isinstance(response, dict) else "slack_response_shape")
            # Missing/malformed history is unknown, not a complete empty source.
            # Validate before rows can be omitted and the store replaces old work.
            messages = response.get("messages")
            if (not isinstance(messages, list) or any(
                    not isinstance(row, dict) or not row.get("ts") for row in messages)):
                raise SourceFailure("slack_messages_shape")
            metadata = response.get("response_metadata", {})
            has_more = response.get("has_more", False)
            if (not isinstance(metadata, dict)
                    or not isinstance(metadata.get("next_cursor", ""), str)
                    or type(has_more) is not bool):
                raise SourceFailure("slack_pagination_shape")
            rows.extend(messages)
            cursor = metadata.get("next_cursor", "")
            if not cursor:
                complete = not has_more
                break
        items, threads = [], []
        workspace = self.slack_config.get("workspace_url", "")
        for row in {str(row.get("ts")): row for row in rows if isinstance(row, dict)}.values():
            if row.get("subtype") in HOUSEKEEPING or not row.get("ts"):
                continue
            ts = str(row["ts"])
            body = text(row.get("text"))
            url = workspace.rstrip("/") + "/archives/" + channel_id + "/p" + ts.replace(".", "") if workspace else None
            updated = timestamp(row.get("edited", {}).get("ts") or ts)
            if row.get("reply_count"):
                threads.append({"thread_ts": ts, "reply_count": row["reply_count"],
                                "latest_reply": row.get("latest_reply")})
            items.append({"id": "slack:" + channel_id + ":" + ts, "kind": "slack_thread",
                "title": body.splitlines()[0][:500] if body else "Slack message",
                "status": "posted", "owner": row.get("user") or row.get("bot_id"),
                "project": channel.get("project") or label, "updated_at": updated,
                "activity_observed_at": updated, "url": url, "summary": body,
                "next_action": None, "refs": {"channel_id": channel_id, "message_ts": ts,
                    "thread_ts": row.get("thread_ts") or ts, "reply_count": row.get("reply_count", 0),
                    "latest_reply": row.get("latest_reply")}, "actions": link(url)})
        batch = self._batch(source, items, complete and not threads,
            ["Membership housekeeping omitted from work view; original Slack history remains unchanged.",
             "Thread replies are not imported by channel history; thread references and reply coverage remain explicit."])
        batch["source"]["metadata"] = {"history_complete": complete, "next_cursor": cursor,
                                       "threads_pending": threads[:100],
                                       "threads_pending_count": len(threads)}
        return batch

    def _document(self, spec):
        repo, path = self._repository(spec["repository"]), spec["path"]
        if not isinstance(path, str) or path.startswith("/") or ".." in path.split("/"):
            raise ValueError("Document path must stay inside its repository.")
        source = self._source("github:document:" + repo + ":" + path, "GitHub",
                              spec.get("label", path), {"repository": repo, "path": path})
        ref = spec.get("ref", "main")
        head = self._github("repos/" + repo + "/commits/" + quote(ref, safe=""))
        sha = head.get("sha")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise SourceFailure("github_commit_shape")
        document = self._github("repos/" + repo + "/contents/" + quote(path, safe="/") + "?ref=" + sha)
        if document.get("encoding") != "base64" or not isinstance(document.get("content"), str):
            raise SourceFailure("github_document_encoding")
        data = json.loads(base64.b64decode(document["content"]).decode("utf-8-sig"))
        items = []
        for collection in spec.get("collections", ["features"]):
            if collection not in data:
                raise SourceFailure("document_collection_missing")
            rows = data[collection]
            if not isinstance(rows, list):
                raise SourceFailure("document_collection_shape")
            for row in rows:
                if not isinstance(row, dict):
                    continue
                detail = row.get("data") if isinstance(row.get("data"), dict) else row
                key = row.get("id") or row.get("subject_id") or row.get("record_id")
                if not key:
                    continue
                origin = row.get("source", {})
                origin = origin if isinstance(origin, dict) else {}
                provider = row.get("provider", {})
                provider = provider if isinstance(provider, dict) else {}
                url = "https://github.com/" + repo + "/blob/" + sha + "/" + quote(path, safe="/")
                observed = timestamp(row.get("observed_at"))
                updated = timestamp(row.get("updated_at") or row.get("last_change") or provider.get("event_at"))
                items.append({"id": "document:" + repo + ":" + path + ":" + collection + ":" + str(key),
                    "kind": {"features": "feature", "operations": "task", "artifacts": "artifact",
                             "sessions": "session", "sources": "work"}.get(collection, collection.rstrip("s")),
                    "title": text(row.get("name") or row.get("label") or detail.get("description") or key, 500),
                    "status": next((value for value in (row.get("status"), row.get("rollup"),
                        provider.get("status"), detail.get("reported_status"), detail.get("reported_state"))
                        if isinstance(value, str) and value), "unknown"),
                    "owner": row.get("owner") or row.get("owner_subsystem") or detail.get("owner"),
                    "project": row.get("project") or spec.get("project") or repo,
                    "updated_at": updated, "activity_observed_at": updated,
                    "url": row.get("url") or detail.get("url") or origin.get("ref") if str(row.get("url") or detail.get("url") or origin.get("ref") or "").startswith("https://") else url,
                    "summary": text(row.get("capability") or row.get("objective") or detail.get("description") or row.get("notes")),
                    "next_action": row.get("next_action") or row.get("next_gap") or detail.get("next_action"),
                    "refs": {"canonical_url": url, "collection": collection, "source_id": key,
                             "source_sha": sha, "source_status": row.get("source_status"),
                             "test_status": row.get("test_status"), "live_status": row.get("live_status"),
                             "source_ref": origin.get("ref"), "provider_status": provider.get("status"),
                             "resource_observed_at": observed},
                    "actions": link(url)})
        return self._batch(source, items, True,
                           ["Canonical source assertions retained; fetching a document does not re-measure its work activity."])

    def collect(self):
        # Cooperative deadline: in-flight provider reads finish under their own
        # timeout, and the executor is joined before the caller releases its lock.
        self.deadline = monotonic() + self.refresh_deadline_seconds
        results, tasks = [], []
        if self.github_config.get("enabled", True):
            identity_source = self._source("github:identity", "GitHub", "Existing GitHub account", {})
            try:
                identity = self._github("user")
                login = identity["login"]
                if not re.fullmatch(r"[A-Za-z0-9-]+", login):
                    raise SourceFailure("github_identity_shape")
                results.append(self._batch(identity_source, [], True,
                    ["Authenticated identity observed; this is not a business activity timestamp."]))
                repos = self._safe(self._source("github:repositories", "GitHub", "Owned repositories", {"owner": login}),
                                   lambda: self._repository_batch(login))
                prs = self._safe(self._source("github:prs", "GitHub", "Pull requests", {"author_or_owner": login}),
                                 lambda: self._pull_requests(login))
                results.extend([repos, prs])
                candidates = {}
                cutoff = (datetime.now(UTC) - timedelta(days=self.lookback_days)).isoformat().replace("+00:00", "Z")
                for item in repos["items"] + prs["items"]:
                    if item.get("updated_at") and item["updated_at"] >= cutoff:
                        candidates[item["project"]] = max(candidates.get(item["project"], ""), item["updated_at"])
                explicit = [self._repository(repo) for repo in self.github_config.get("working_repositories", [])]
                selected = list(dict.fromkeys(explicit + sorted(candidates, key=candidates.get, reverse=True)))
                cap = self._bound(self.github_config.get("max_action_repositories", 8), 1, 40)
                for repo in selected[:cap]:
                    source = self._source("github:actions:" + repo, "GitHub", repo + " builds", {"repository": repo})
                    tasks.append((source, lambda repo=repo: self._actions(repo)))
                repos["source"]["metadata"] = {"action_repositories_selected": selected[:cap],
                                                "action_repositories_pending": selected[cap:cap + 100],
                                                "action_repositories_pending_count": max(0, len(selected) - cap)}
                if selected[cap:]:
                    repos["source"]["coverage"]["notes"].append(
                        str(len(selected[cap:])) + " additional working repositories exceed the Actions collection cap.")
            except Exception as exc:
                results.append(self._batch(identity_source, [], False, error=getattr(exc, "code", type(exc).__name__)))
        for channel in self.slack_config.get("channels", []):
            if not isinstance(channel, dict) or not re.fullmatch(r"[CG][A-Z0-9]+", str(channel.get("id", ""))):
                raise ValueError("Slack channels need an existing provider id.")
            source = self._source("slack:" + channel["id"], "Slack", channel.get("label", channel["id"]), {"channel_id": channel["id"]})
            tasks.append((source, lambda channel=channel: self._slack(channel)))
        for spec in self.documents:
            source = self._source("github:document:" + spec["repository"] + ":" + spec["path"], "GitHub",
                                  spec.get("label", spec["path"]), {"repository": spec["repository"], "path": spec["path"]})
            tasks.append((source, lambda spec=spec: self._document(spec)))
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for source, reader in tasks:
                try:
                    self._check_deadline()
                except SourceFailure as exc:
                    results.append(self._batch(source, [], False, error=exc.code,
                        notes=["Collection stopped before dispatch; previous items remain available."]))
                    continue
                futures.append(executor.submit(self._safe, source, reader))
            for future in as_completed(futures):
                results.append(future.result())
        # Serialize writes; provider concurrency never shares a Store transaction.
        for batch in results:
            payload = {key: value for key, value in batch.items() if key != "operation_id"}
            batch["operation_id"] = "collect:" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        receipts = [self.store.ingest(batch) for batch in results]
        return {"observed_at": self.clock(), "sources": [batch["source"] for batch in results],
                "items_observed": sum(len(batch["items"]) for batch in results), "receipts": receipts}
