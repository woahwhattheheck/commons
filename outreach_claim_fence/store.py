"""GitHub Contents compare-and-swap claim store."""

from __future__ import annotations

import base64
import datetime as dt
import json
import urllib.parse
from typing import Any, Dict, Mapping, Optional, Tuple

from .core import (
    API_VERSION, DEFAULT_BRANCH, DEFAULT_ROOT, MAX_LEASE_SECONDS, MAX_COOLDOWN_SECONDS, SCHEMA,
    MAX_RETRIES, MIN_LEASE_SECONDS, MIN_COOLDOWN_SECONDS, ClaimConflict, ClaimNotFound,
    ClaimReceipt, HttpResponse, OwnershipError, ProtocolError, RemoteError, StoredClaim,
    TargetIdentity, UrllibTransport, ValidationError, _CasConflict, _HEX_64, _canonical_json_bytes, _clean_text,
    _format_timestamp, _has_concrete_compensation_signal, _parse_timestamp, _safe_label,
    _safe_message_digest, _safe_owner, _seal_record, _server_time, _sha256_hex,
    _validate_duration, _validate_record, normalize_target,
)

class GitHubContentsClaimStore:
    """Compare-and-swap claim store using one deterministic file per contact."""

    def __init__(
        self,
        *,
        repository: str,
        token: str,
        branch: str = DEFAULT_BRANCH,
        root: str = DEFAULT_ROOT,
        api_url: str = "https://api.github.com",
        transport: Optional[Any] = None,
    ) -> None:
        if repository.count("/") != 1:
            raise ValidationError("repository must be in owner/name form")
        owner, repo = repository.split("/", 1)
        self.owner = _safe_owner(owner, field="repository owner")
        self.repo = _safe_owner(repo, field="repository name")
        self.repository = f"{self.owner}/{self.repo}"
        self.branch = _clean_text(branch, field="branch", max_length=240)
        self.root = _clean_text(root.strip("/"), field="root", max_length=400)
        if ".." in self.root.split("/"):
            raise ValidationError("root must not contain ..")
        if not token:
            raise ValidationError("GitHub token is required")
        self._token = token
        self.api_url = api_url.rstrip("/")
        self.transport = transport or UrllibTransport()

    def path_for(self, claim_key: str) -> str:
        if not _HEX_64.fullmatch(claim_key):
            raise ValidationError("claim key must be 64 lowercase hexadecimal characters")
        return f"{self.root}/{claim_key[:2]}/{claim_key}.json"

    def _url(self, path: str) -> str:
        encoded_path = urllib.parse.quote(path, safe="/")
        return f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{encoded_path}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "outreach-claim-fence-v1",
        }

    def _decode_json(self, response: HttpResponse, *, context: str) -> Mapping[str, Any]:
        try:
            value = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtocolError(f"GitHub returned malformed JSON while {context}") from exc
        if not isinstance(value, dict):
            raise ProtocolError(f"GitHub returned a non-object while {context}")
        return value

    def _read(self, identity: TargetIdentity) -> Tuple[Optional[StoredClaim], dt.datetime]:
        path = self.path_for(identity.claim_key)
        query = urllib.parse.urlencode({"ref": self.branch})
        response = self.transport.request("GET", f"{self._url(path)}?{query}", self._headers())
        server_now = _server_time(response.headers)
        if response.status == 404:
            return None, server_now
        if response.status != 200:
            raise RemoteError(
                "GitHub refused the claim read",
                details={"status": response.status, "repository": self.repository},
            )
        payload = self._decode_json(response, context="reading a claim")
        if payload.get("type") != "file" or not isinstance(payload.get("sha"), str):
            raise ProtocolError("GitHub claim path is not a file")
        if payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
            raise ProtocolError("GitHub claim content is not base64")
        try:
            encoded = "".join(payload["content"].split())
            raw = base64.b64decode(encoded, validate=True)
            record_value = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProtocolError("stored claim content is not valid canonical JSON") from exc
        record = _validate_record(record_value, expected_claim_key=identity.claim_key)
        return StoredClaim(record=record, blob_sha=payload["sha"], server_now=server_now), server_now

    def _write(
        self,
        *,
        identity: TargetIdentity,
        record: Mapping[str, Any],
        previous_blob_sha: Optional[str],
        message: str,
    ) -> Tuple[str, str, dt.datetime]:
        body: Dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(_canonical_json_bytes(record) + b"\n").decode("ascii"),
            "branch": self.branch,
        }
        if previous_blob_sha is not None:
            body["sha"] = previous_blob_sha
        response = self.transport.request(
            "PUT",
            self._url(self.path_for(identity.claim_key)),
            {**self._headers(), "Content-Type": "application/json"},
            _canonical_json_bytes(body),
        )
        server_now = _server_time(response.headers)
        if response.status in {409, 422}:
            raise _CasConflict()
        if response.status not in {200, 201}:
            raise RemoteError(
                "GitHub refused the claim write",
                details={"status": response.status, "repository": self.repository},
            )
        payload = self._decode_json(response, context="writing a claim")
        content = payload.get("content")
        commit = payload.get("commit")
        if not isinstance(content, dict) or not isinstance(content.get("sha"), str):
            raise ProtocolError("GitHub write response omitted the content SHA")
        if not isinstance(commit, dict) or not isinstance(commit.get("sha"), str):
            raise ProtocolError("GitHub write response omitted the commit SHA")
        return content["sha"], commit["sha"], server_now

    @staticmethod
    def _is_live(record: Mapping[str, Any], now: dt.datetime) -> bool:
        if record["state"] == "RELEASED":
            return False
        return _parse_timestamp(record["lease_expires_at"], field="lease_expires_at") > now

    @staticmethod
    def _owned_by(record: Mapping[str, Any], agent_id: str, operation_id: str) -> bool:
        return record["agent_id"] == agent_id and record["operation_id"] == operation_id

    def _receipt(
        self,
        action: str,
        identity: TargetIdentity,
        record: Mapping[str, Any],
        *,
        blob_sha: Optional[str],
        commit_sha: Optional[str],
    ) -> ClaimReceipt:
        return ClaimReceipt(
            action=action,
            claim_key=identity.claim_key,
            state=str(record["state"]),
            revision=int(record["revision"]),
            agent_id=str(record["agent_id"]),
            operation_id=str(record["operation_id"]),
            lease_expires_at=str(record["lease_expires_at"]),
            record_digest=str(record["record_digest"]),
            path=self.path_for(identity.claim_key),
            blob_sha=blob_sha,
            commit_sha=commit_sha,
        )

    def _conflict(self, record: Mapping[str, Any]) -> ClaimConflict:
        return ClaimConflict(
            "contact is already protected by a live claim",
            details={
                "state": record["state"],
                "agent_id": record["agent_id"],
                "operation_id": record["operation_id"],
                "opportunity_label": record["opportunity_label"],
                "lease_expires_at": record["lease_expires_at"],
                "target_hint": record["target_hint"],
                "revision": record["revision"],
            },
        )

    def acquire(
        self,
        *,
        target_kind: str,
        contact: str,
        opportunity: str,
        agent_id: str,
        operation_id: str,
        lease_seconds: int,
    ) -> ClaimReceipt:
        identity = normalize_target(target_kind, contact)
        opportunity_label = _safe_label(opportunity, field="opportunity", max_length=200)
        opportunity_digest = _sha256_hex(opportunity_label.casefold().encode("utf-8"))
        agent_id = _safe_owner(agent_id, field="agent id")
        operation_id = _safe_owner(operation_id, field="operation id")
        lease_seconds = _validate_duration(
            lease_seconds,
            field="lease",
            minimum=MIN_LEASE_SECONDS,
            maximum=MAX_LEASE_SECONDS,
        )

        for _attempt in range(MAX_RETRIES):
            stored, now = self._read(identity)
            if stored is not None:
                current = stored.record
                if self._is_live(current, now):
                    if self._owned_by(current, agent_id, operation_id):
                        return self._receipt(
                            "ALREADY_OWNED",
                            identity,
                            current,
                            blob_sha=stored.blob_sha,
                            commit_sha=None,
                        )
                    raise self._conflict(current)
                revision = int(current["revision"]) + 1
                prior_digest = str(current["record_digest"])
                previous_blob_sha = stored.blob_sha
                prior_contact_count = int(current["contact_count"])
                prior_last_contacted_at = current.get("last_contacted_at")
                prior_last_message_digest = current.get("last_message_digest")
                prior_last_channel = current.get("last_channel")
                prior_compensation_path = current.get("compensation_path")
            else:
                revision = 1
                prior_digest = None
                previous_blob_sha = None
                prior_contact_count = 0
                prior_last_contacted_at = None
                prior_last_message_digest = None
                prior_last_channel = None
                prior_compensation_path = None

            timestamp = _format_timestamp(now)
            record = _seal_record(
                {
                    "schema": SCHEMA,
                    "claim_key": identity.claim_key,
                    "target_kind": identity.kind,
                    "target_hint": identity.hint,
                    "state": "ACTIVE",
                    "revision": revision,
                    "agent_id": agent_id,
                    "operation_id": operation_id,
                    "opportunity_label": opportunity_label,
                    "opportunity_digest": opportunity_digest,
                    "claimed_at": timestamp,
                    "last_action_at": timestamp,
                    "lease_expires_at": _format_timestamp(
                        now + dt.timedelta(seconds=lease_seconds)
                    ),
                    "prior_record_digest": prior_digest,
                    "record_digest": "",
                    "contact_count": prior_contact_count,
                    "last_contacted_at": prior_last_contacted_at,
                    "last_message_digest": prior_last_message_digest,
                    "last_channel": prior_last_channel,
                    "compensation_path": prior_compensation_path,
                    "release_reason": None,
                }
            )
            try:
                blob_sha, commit_sha, _ = self._write(
                    identity=identity,
                    record=record,
                    previous_blob_sha=previous_blob_sha,
                    message=f"claim(outreach): reserve {identity.claim_key[:12]} for {agent_id}",
                )
            except _CasConflict:
                continue
            return self._receipt(
                "ACQUIRED",
                identity,
                record,
                blob_sha=blob_sha,
                commit_sha=commit_sha,
            )
        stored, now = self._read(identity)
        if stored is not None and self._is_live(stored.record, now):
            if self._owned_by(stored.record, agent_id, operation_id):
                return self._receipt(
                    "ALREADY_OWNED",
                    identity,
                    stored.record,
                    blob_sha=stored.blob_sha,
                    commit_sha=None,
                )
            raise self._conflict(stored.record)
        raise RemoteError("claim compare-and-swap did not converge")

    def inspect(self, *, target_kind: str, contact: str) -> Mapping[str, Any]:
        identity = normalize_target(target_kind, contact)
        stored, now = self._read(identity)
        if stored is None:
            raise ClaimNotFound("no claim exists for this contact")
        record = dict(stored.record)
        record["live"] = self._is_live(record, now)
        record["server_now"] = _format_timestamp(now)
        record["path"] = self.path_for(identity.claim_key)
        record["blob_sha"] = stored.blob_sha
        return record

    def _owned_record(
        self,
        *,
        identity: TargetIdentity,
        agent_id: str,
        operation_id: str,
        require_live: bool,
    ) -> Tuple[StoredClaim, dt.datetime]:
        stored, now = self._read(identity)
        if stored is None:
            raise ClaimNotFound("no claim exists for this contact")
        if not self._owned_by(stored.record, agent_id, operation_id):
            raise OwnershipError(
                "claim is owned by another operation",
                details={
                    "agent_id": stored.record["agent_id"],
                    "operation_id": stored.record["operation_id"],
                    "lease_expires_at": stored.record["lease_expires_at"],
                },
            )
        if require_live and not self._is_live(stored.record, now):
            raise OwnershipError("claim lease is no longer live; reacquire before mutation")
        return stored, now

    def _update_owned(
        self,
        *,
        identity: TargetIdentity,
        agent_id: str,
        operation_id: str,
        mutate: Any,
        commit_message: str,
        idempotent_match: Optional[Any] = None,
    ) -> ClaimReceipt:
        for _attempt in range(MAX_RETRIES):
            stored, now = self._owned_record(
                identity=identity,
                agent_id=agent_id,
                operation_id=operation_id,
                require_live=False,
            )
            if idempotent_match is not None and idempotent_match(stored.record):
                return self._receipt(
                    "ALREADY_RECORDED",
                    identity,
                    stored.record,
                    blob_sha=stored.blob_sha,
                    commit_sha=None,
                )
            if not self._is_live(stored.record, now):
                raise OwnershipError("claim lease is no longer live; reacquire before mutation")
            next_record = mutate(dict(stored.record), now)
            next_record["revision"] = int(stored.record["revision"]) + 1
            next_record["prior_record_digest"] = stored.record["record_digest"]
            next_record["last_action_at"] = _format_timestamp(now)
            next_record = _seal_record(next_record)
            try:
                blob_sha, commit_sha, _ = self._write(
                    identity=identity,
                    record=next_record,
                    previous_blob_sha=stored.blob_sha,
                    message=commit_message,
                )
            except _CasConflict:
                continue
            return self._receipt(
                "UPDATED",
                identity,
                next_record,
                blob_sha=blob_sha,
                commit_sha=commit_sha,
            )
        raise RemoteError("claim compare-and-swap did not converge")

    def renew(
        self,
        *,
        target_kind: str,
        contact: str,
        agent_id: str,
        operation_id: str,
        lease_seconds: int,
    ) -> ClaimReceipt:
        identity = normalize_target(target_kind, contact)
        agent_id = _safe_owner(agent_id, field="agent id")
        operation_id = _safe_owner(operation_id, field="operation id")
        lease_seconds = _validate_duration(
            lease_seconds,
            field="lease",
            minimum=MIN_LEASE_SECONDS,
            maximum=MAX_LEASE_SECONDS,
        )

        def mutate(record: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
            record["lease_expires_at"] = _format_timestamp(
                now + dt.timedelta(seconds=lease_seconds)
            )
            return record

        return self._update_owned(
            identity=identity,
            agent_id=agent_id,
            operation_id=operation_id,
            mutate=mutate,
            commit_message=f"claim(outreach): renew {identity.claim_key[:12]} for {agent_id}",
        )

    def mark_contacted(
        self,
        *,
        target_kind: str,
        contact: str,
        agent_id: str,
        operation_id: str,
        message_digest: str,
        channel: str,
        compensation_path: str,
        cooldown_seconds: int,
    ) -> ClaimReceipt:
        identity = normalize_target(target_kind, contact)
        agent_id = _safe_owner(agent_id, field="agent id")
        operation_id = _safe_owner(operation_id, field="operation id")
        message_digest = _safe_message_digest(message_digest)
        channel = _safe_label(channel, field="channel", max_length=80)
        compensation_path = _safe_label(
            compensation_path, field="compensation path", max_length=240
        )
        if not _has_concrete_compensation_signal(compensation_path):
            raise ValidationError(
                "compensation path must name a concrete paid path, amount, proposal, or bounty"
            )
        cooldown_seconds = _validate_duration(
            cooldown_seconds,
            field="cooldown",
            minimum=MIN_COOLDOWN_SECONDS,
            maximum=MAX_COOLDOWN_SECONDS,
        )

        def idempotent(record: Mapping[str, Any]) -> bool:
            return (
                record["state"] == "CONTACTED"
                and record.get("last_message_digest") == message_digest
                and record.get("last_channel") == channel
                and record.get("compensation_path") == compensation_path
            )

        def mutate(record: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
            if record.get("last_message_digest") == message_digest:
                raise ValidationError(
                    "message digest is already recorded with different contact metadata"
                )
            record["state"] = "CONTACTED"
            record["contact_count"] = int(record["contact_count"]) + 1
            record["last_contacted_at"] = _format_timestamp(now)
            record["last_message_digest"] = message_digest
            record["last_channel"] = channel
            record["compensation_path"] = compensation_path
            record["release_reason"] = None
            record["lease_expires_at"] = _format_timestamp(
                now + dt.timedelta(seconds=cooldown_seconds)
            )
            return record

        return self._update_owned(
            identity=identity,
            agent_id=agent_id,
            operation_id=operation_id,
            mutate=mutate,
            idempotent_match=idempotent,
            commit_message=f"claim(outreach): record contact {identity.claim_key[:12]} by {agent_id}",
        )

    def release(
        self,
        *,
        target_kind: str,
        contact: str,
        agent_id: str,
        operation_id: str,
        reason: str,
    ) -> ClaimReceipt:
        identity = normalize_target(target_kind, contact)
        agent_id = _safe_owner(agent_id, field="agent id")
        operation_id = _safe_owner(operation_id, field="operation id")
        reason = _safe_label(reason, field="release reason", max_length=240)

        def idempotent(record: Mapping[str, Any]) -> bool:
            return record["state"] == "RELEASED" and record.get("release_reason") == reason

        def mutate(record: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
            record["state"] = "RELEASED"
            record["release_reason"] = reason
            record["lease_expires_at"] = _format_timestamp(now)
            return record

        return self._update_owned(
            identity=identity,
            agent_id=agent_id,
            operation_id=operation_id,
            mutate=mutate,
            idempotent_match=idempotent,
            commit_message=f"claim(outreach): release {identity.claim_key[:12]} by {agent_id}",
        )
