"""Command-line interface for the outreach claim fence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Mapping, Optional, Sequence

from .core import (
    DEFAULT_BRANCH, DEFAULT_ROOT, ClaimFenceError, ValidationError, _TARGET_KINDS,
    digest_message_file, normalize_target,
)
from .store import GitHubContentsClaimStore


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValidationError(f"argument error: {message}")


def _store_from_args(args: argparse.Namespace) -> GitHubContentsClaimStore:
    repository = args.repository or os.environ.get("OUTREACH_CLAIM_REPOSITORY")
    if not repository:
        raise ValidationError(
            "repository is required via --repository or OUTREACH_CLAIM_REPOSITORY"
        )
    token = os.environ.get(args.token_env)
    if not token:
        raise ValidationError(f"token environment variable {args.token_env!r} is empty")
    return GitHubContentsClaimStore(
        repository=repository,
        token=token,
        branch=args.branch,
        root=args.root,
        api_url=args.api_url,
    )


def _add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--kind", required=True, choices=sorted(_TARGET_KINDS))
    parser.add_argument("--contact", required=True)


def _add_owner_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--operation-id", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        description="Atomic, digest-only outreach claim coordination over GitHub"
    )
    parser.add_argument("--repository", help="coordination repository in owner/name form")
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--api-url", default="https://api.github.com")
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    subparsers = parser.add_subparsers(dest="command", required=True)

    key_parser = subparsers.add_parser("key", help="derive the privacy-minimized claim key")
    _add_target_arguments(key_parser)

    acquire_parser = subparsers.add_parser("acquire", help="atomically reserve a contact")
    _add_target_arguments(acquire_parser)
    _add_owner_arguments(acquire_parser)
    acquire_parser.add_argument("--opportunity", required=True)
    acquire_parser.add_argument("--lease-seconds", type=int, default=3600)

    inspect_parser = subparsers.add_parser("inspect", help="inspect a contact claim")
    _add_target_arguments(inspect_parser)

    renew_parser = subparsers.add_parser("renew", help="extend an owned live lease")
    _add_target_arguments(renew_parser)
    _add_owner_arguments(renew_parser)
    renew_parser.add_argument("--lease-seconds", type=int, default=3600)

    contacted_parser = subparsers.add_parser(
        "contacted", help="record a digest-only outbound event and cooldown"
    )
    _add_target_arguments(contacted_parser)
    _add_owner_arguments(contacted_parser)
    message_group = contacted_parser.add_mutually_exclusive_group(required=True)
    message_group.add_argument("--message-digest")
    message_group.add_argument("--message-file")
    contacted_parser.add_argument("--channel", required=True)
    contacted_parser.add_argument("--compensation-path", required=True)
    contacted_parser.add_argument("--cooldown-seconds", type=int, default=3 * 24 * 3600)

    release_parser = subparsers.add_parser("release", help="release an owned live claim")
    _add_target_arguments(release_parser)
    _add_owner_arguments(release_parser)
    release_parser.add_argument("--reason", required=True)
    return parser


def _print_json(value: Mapping[str, Any], *, stream: Optional[Any] = None) -> None:
    target = sys.stdout if stream is None else stream
    target.write(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        if args.command == "key":
            identity = normalize_target(args.kind, args.contact)
            _print_json(
                {
                    "ok": True,
                    "claim_key": identity.claim_key,
                    "target_kind": identity.kind,
                    "target_hint": identity.hint,
                }
            )
            return 0

        store = _store_from_args(args)
        if args.command == "acquire":
            result: Mapping[str, Any] = store.acquire(
                target_kind=args.kind,
                contact=args.contact,
                opportunity=args.opportunity,
                agent_id=args.agent_id,
                operation_id=args.operation_id,
                lease_seconds=args.lease_seconds,
            ).as_dict()
        elif args.command == "inspect":
            result = {"ok": True, "claim": store.inspect(target_kind=args.kind, contact=args.contact)}
        elif args.command == "renew":
            result = store.renew(
                target_kind=args.kind,
                contact=args.contact,
                agent_id=args.agent_id,
                operation_id=args.operation_id,
                lease_seconds=args.lease_seconds,
            ).as_dict()
        elif args.command == "contacted":
            if args.message_file:
                message_digest = digest_message_file(args.message_file)
            else:
                message_digest = args.message_digest
            result = store.mark_contacted(
                target_kind=args.kind,
                contact=args.contact,
                agent_id=args.agent_id,
                operation_id=args.operation_id,
                message_digest=message_digest,
                channel=args.channel,
                compensation_path=args.compensation_path,
                cooldown_seconds=args.cooldown_seconds,
            ).as_dict()
        elif args.command == "release":
            result = store.release(
                target_kind=args.kind,
                contact=args.contact,
                agent_id=args.agent_id,
                operation_id=args.operation_id,
                reason=args.reason,
            ).as_dict()
        else:  # pragma: no cover - argparse enforces the command set.
            raise ValidationError("unknown command")
        _print_json(result)
        return 0
    except ClaimFenceError as exc:
        _print_json(exc.safe_payload(), stream=sys.stderr)
        return exc.exit_code
