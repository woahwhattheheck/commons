#!/usr/bin/env python3
"""Collision-safe lead claim fence backed by a GitHub repository.

The durable key is a SHA-256 fingerprint of a canonical lead identity. Raw lead
identifiers are never written to the public ledger. A sender MUST successfully
acquire a claim before contacting a lead, and MUST mark it sent afterwards.

Exit codes:
  0  requested operation succeeded / claim acquired
  3  claim denied because another live or sent claim exists
  4  transport / GitHub API failure
  5  invalid arguments or invalid ledger record
"""
from __future__ import annotations

import argparse
import base64
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Protocol, Tuple

UTC = dt.timezone.utc
SCHEMA = "commons.lead-fence/v1"
ACTIVE = "ACTIVE"
SENT = "SENT"
RELEASED = "RELEASED"


class ConflictError(RuntimeError):
    pass


class TransportError(RuntimeError):
    pass


class InvalidRecord(RuntimeError):
    pass


def utcnow() -> dt.datetime:
    return dt.datetime.now(tz=UTC)


def isoformat_z(value: dt.datetime) -> str:
    value = value.astimezone(UTC).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> dt.datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_identity(raw: str) -> str:
    """Canonicalize an identity without retaining display-only variation.

    Recommended inputs are an email address, `mailto:` URI, bare domain, or URL.
    This normalization is intentionally conservative: peers must use the same
    actual recipient identity rather than fuzzy company-name matching.
    """
    value = unicodedata.normalize("NFKC", raw).strip()
    if not value:
        raise ValueError("identity must not be blank")

    if value.lower().startswith("mailto:"):
        value = value[7:]

    # Email identity: strip surrounding whitespace and case-fold. Gmail-style
    # dot/plus rewriting is deliberately NOT performed because it is provider-
    # specific and can merge distinct addresses on other domains.
    if "@" in value and not re.match(r"^[a-z][a-z0-9+.-]*://", value, re.I):
        local, domain = value.rsplit("@", 1)
        local = local.strip().casefold()
        domain = domain.strip().rstrip(".").casefold()
        if not local or not domain:
            raise ValueError("invalid email identity")
        return f"email:{local}@{domain}"

    candidate = value
    if re.match(r"^[a-z][a-z0-9+.-]*://", candidate, re.I):
        parsed = urllib.parse.urlsplit(candidate)
        host = parsed.hostname
        if not host:
            raise ValueError("URL identity has no hostname")
        candidate = host
    elif candidate.lower().startswith("domain:"):
        candidate = candidate.split(":", 1)[1]
    else:
        # A path makes a bare value ambiguous; callers should supply a URL.
        candidate = candidate.split("/", 1)[0]

    domain = candidate.strip().rstrip(".").casefold()
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain or any(ch.isspace() for ch in domain):
        raise ValueError("invalid domain identity")
    return f"domain:{domain}"


def fingerprint(identity: str) -> str:
    canonical = normalize_identity(identity)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def claim_path(identity: str, prefix: str = "revenue/lead_fence/claims") -> str:
    digest = fingerprint(identity)
    return f"{prefix.rstrip('/')}/{digest[:2]}/{digest}.json"


class LedgerClient(Protocol):
    def read_json(self, path: str) -> Optional[Tuple[Dict[str, Any], str]]: ...
    def create_json(self, path: str, payload: Dict[str, Any], message: str) -> str: ...
    def update_json(self, path: str, payload: Dict[str, Any], sha: str, message: str) -> str: ...


class GitHubContentsClient:
    def __init__(self, repo: str, token: str, branch: str = "main", api_base: str = "https://api.github.com"):
        if "/" not in repo:
            raise ValueError("repo must be owner/name")
        self.repo = repo
        self.token = token
        self.branch = branch
        self.api_base = api_base.rstrip("/")

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.api_base}/repos/{self.repo}/contents/{urllib.parse.quote(path, safe='/')}"
        if method == "GET":
            url += "?" + urllib.parse.urlencode({"ref": self.branch})
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "commons-lead-fence/1",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", "replace")
            if exc.code == 404 and method == "GET":
                return None
            if exc.code in (409, 422):
                raise ConflictError(f"GitHub conflict ({exc.code}): {text[:500]}") from exc
            raise TransportError(f"GitHub HTTP {exc.code}: {text[:500]}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise TransportError(f"GitHub request failed: {exc}") from exc

    def read_json(self, path: str) -> Optional[Tuple[Dict[str, Any], str]]:
        result = self._request("GET", path)
        if result is None:
            return None
        try:
            content = base64.b64decode(result["content"]).decode("utf-8")
            payload = json.loads(content)
            sha = result["sha"]
        except Exception as exc:
            raise InvalidRecord(f"malformed ledger file at {path}: {exc}") from exc
        return payload, sha

    def _write_json(self, path: str, payload: Dict[str, Any], message: str, sha: Optional[str]) -> str:
        encoded = base64.b64encode((json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")).decode("ascii")
        body: Dict[str, Any] = {"message": message, "content": encoded, "branch": self.branch}
        if sha:
            body["sha"] = sha
        result = self._request("PUT", path, body)
        try:
            return result["commit"]["sha"]
        except Exception as exc:
            raise TransportError(f"GitHub write returned no commit sha: {result!r}") from exc

    def create_json(self, path: str, payload: Dict[str, Any], message: str) -> str:
        return self._write_json(path, payload, message, None)

    def update_json(self, path: str, payload: Dict[str, Any], sha: str, message: str) -> str:
        return self._write_json(path, payload, message, sha)


@dataclasses.dataclass(frozen=True)
class Result:
    ok: bool
    outcome: str
    path: str
    record: Dict[str, Any]
    commit_sha: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "outcome": self.outcome,
            "path": self.path,
            "commit_sha": self.commit_sha,
            "record": self.record,
        }


class LeadFence:
    def __init__(self, client: LedgerClient, prefix: str = "revenue/lead_fence/claims", now_fn=utcnow):
        self.client = client
        self.prefix = prefix.rstrip("/")
        self.now_fn = now_fn

    def _path(self, identity: str) -> str:
        return claim_path(identity, self.prefix)

    @staticmethod
    def _validate(record: Dict[str, Any]) -> None:
        if record.get("schema") != SCHEMA:
            raise InvalidRecord(f"unsupported schema: {record.get('schema')!r}")
        if record.get("state") not in {ACTIVE, SENT, RELEASED}:
            raise InvalidRecord(f"invalid state: {record.get('state')!r}")
        if not record.get("fingerprint"):
            raise InvalidRecord("missing fingerprint")

    def _is_blocking(self, record: Dict[str, Any], now: dt.datetime) -> bool:
        self._validate(record)
        if record["state"] == SENT:
            return True
        if record["state"] == RELEASED:
            return False
        expires = parse_time(record["expires_at"])
        return expires > now

    def _new_active(self, identity: str, actor: str, campaign: str, ttl_minutes: int, source: str, previous: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = self.now_fn()
        canonical = normalize_identity(identity)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        record: Dict[str, Any] = {
            "schema": SCHEMA,
            "fingerprint": digest,
            "state": ACTIVE,
            "actor": actor,
            "campaign": campaign,
            "source": source,
            "acquired_at": isoformat_z(now),
            "expires_at": isoformat_z(now + dt.timedelta(minutes=ttl_minutes)),
            "sent_at": None,
            "released_at": None,
            "generation": int((previous or {}).get("generation", 0)) + 1,
        }
        # Intentionally omit raw/canonical identity to avoid public PII leakage.
        return record

    def claim(self, identity: str, actor: str, campaign: str, ttl_minutes: int = 30, source: str = "manual") -> Result:
        if not actor.strip():
            raise ValueError("actor must not be blank")
        if ttl_minutes <= 0:
            raise ValueError("ttl_minutes must be positive")
        path = self._path(identity)
        now = self.now_fn()

        current = self.client.read_json(path)
        if current is None:
            record = self._new_active(identity, actor, campaign, ttl_minutes, source)
            try:
                commit = self.client.create_json(path, record, f"lead-fence: claim {record['fingerprint'][:12]} by {actor}")
                return Result(True, "ACQUIRED", path, record, commit)
            except ConflictError:
                # Another sender won the create race. Re-read authoritative state.
                current = self.client.read_json(path)
                if current is None:
                    raise TransportError("claim create conflicted but authoritative record is missing")

        record, sha = current
        self._validate(record)
        if self._is_blocking(record, now):
            return Result(False, "COLLISION", path, record)

        replacement = self._new_active(identity, actor, campaign, ttl_minutes, source, previous=record)
        try:
            commit = self.client.update_json(path, replacement, sha, f"lead-fence: reacquire {replacement['fingerprint'][:12]} by {actor}")
            return Result(True, "REACQUIRED", path, replacement, commit)
        except ConflictError:
            latest = self.client.read_json(path)
            if latest is None:
                raise TransportError("reclaim conflicted but authoritative record is missing")
            latest_record, _ = latest
            self._validate(latest_record)
            return Result(False, "COLLISION", path, latest_record)

    def status(self, identity: str) -> Result:
        path = self._path(identity)
        current = self.client.read_json(path)
        if current is None:
            return Result(True, "UNCLAIMED", path, {})
        record, _ = current
        self._validate(record)
        if record["state"] == ACTIVE and not self._is_blocking(record, self.now_fn()):
            return Result(True, "EXPIRED", path, record)
        return Result(True, record["state"], path, record)

    def transition(self, identity: str, actor: str, new_state: str) -> Result:
        if new_state not in {SENT, RELEASED}:
            raise ValueError("new_state must be SENT or RELEASED")
        path = self._path(identity)
        current = self.client.read_json(path)
        if current is None:
            return Result(False, "NOT_FOUND", path, {})
        record, sha = current
        self._validate(record)
        if record.get("actor") != actor:
            return Result(False, "NOT_OWNER", path, record)
        if record["state"] == SENT:
            # SENT is terminal: never reopen an already-contacted lead via release.
            return Result(new_state == SENT, "SENT", path, record)
        if record["state"] == RELEASED:
            return Result(new_state == RELEASED, "RELEASED", path, record)

        changed = dict(record)
        now = self.now_fn()
        changed["state"] = new_state
        if new_state == SENT:
            changed["sent_at"] = isoformat_z(now)
        else:
            changed["released_at"] = isoformat_z(now)
        try:
            commit = self.client.update_json(path, changed, sha, f"lead-fence: {new_state.lower()} {changed['fingerprint'][:12]} by {actor}")
            return Result(True, new_state, path, changed, commit)
        except ConflictError:
            latest = self.client.read_json(path)
            if latest is None:
                raise TransportError("transition conflicted but authoritative record is missing")
            latest_record, _ = latest
            self._validate(latest_record)
            return Result(False, "COLLISION", path, latest_record)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collision-safe lead outreach claim fence")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "woahwhattheheck/commons"), help="GitHub owner/name")
    parser.add_argument("--branch", default=os.getenv("LEAD_FENCE_BRANCH", "main"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token (prefer GITHUB_TOKEN env)")
    parser.add_argument("--prefix", default=os.getenv("LEAD_FENCE_PREFIX", "revenue/lead_fence/claims"))
    sub = parser.add_subparsers(dest="command", required=True)

    claim_p = sub.add_parser("claim", help="Acquire the right to contact a lead")
    claim_p.add_argument("identity", help="email, mailto URI, URL, or domain")
    claim_p.add_argument("--actor", required=True)
    claim_p.add_argument("--campaign", default="unspecified")
    claim_p.add_argument("--source", default="manual")
    claim_p.add_argument("--ttl-minutes", type=int, default=30)

    for name in ("status", "sent", "release"):
        p = sub.add_parser(name)
        p.add_argument("identity")
        if name != "status":
            p.add_argument("--actor", required=True)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.token:
        print(json.dumps({"ok": False, "error": "GITHUB_TOKEN is required"}), file=sys.stderr)
        return 5
    try:
        fence = LeadFence(GitHubContentsClient(args.repo, args.token, args.branch), prefix=args.prefix)
        if args.command == "claim":
            result = fence.claim(args.identity, args.actor, args.campaign, args.ttl_minutes, args.source)
            code = 0 if result.ok else 3
        elif args.command == "status":
            result = fence.status(args.identity)
            code = 0
        elif args.command == "sent":
            result = fence.transition(args.identity, args.actor, SENT)
            code = 0 if result.ok else 3
        else:
            result = fence.transition(args.identity, args.actor, RELEASED)
            code = 0 if result.ok else 3
        print(json.dumps(result.as_dict(), sort_keys=True))
        return code
    except (ValueError, InvalidRecord) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 5
    except (TransportError, ConflictError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
