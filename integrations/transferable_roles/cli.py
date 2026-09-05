#!/usr/bin/env python3
"""CLI entry for transferable roles.

Examples:
  python3 integrations/transferable_roles/cli.py create --file fixtures/synthetic_crm_followup_role.json --store /tmp/roles
  python3 integrations/transferable_roles/cli.py equip ROLE --session A --harness cursor --seat HINGE --store /tmp/roles
  python3 integrations/transferable_roles/cli.py transfer ROLE --from-session A --to-session B --to-harness claude --seat TENON --store /tmp/roles
  python3 integrations/transferable_roles/cli.py export ROLE --store /tmp/roles
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from roles import RoleError, RoleStore


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RoleError("JSON root must be an object")
    return data


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--store",
        type=Path,
        default=Path(".transferable_roles"),
        help="directory for role JSON records",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="create a role record")
    c.add_argument("--file", type=Path, required=True)
    c.add_argument("--role-id")

    e = sub.add_parser("equip", help="bind an unoccupied role to a session")
    e.add_argument("role_id")
    e.add_argument("--session", required=True)
    e.add_argument("--harness", required=True)
    e.add_argument("--account-pool")
    e.add_argument(
        "--seat",
        help="optional occupant name (not role_id); never a gate",
    )

    t = sub.add_parser("transfer", help="hand role to another session/harness")
    t.add_argument("role_id")
    t.add_argument("--from-session")
    t.add_argument("--to-session", required=True)
    t.add_argument("--to-harness", required=True)
    t.add_argument("--account-pool")
    t.add_argument(
        "--seat",
        help="optional successor occupant name (not role_id); never a gate",
    )

    i = sub.add_parser("inspect", help="print role record")
    i.add_argument("role_id")

    x = sub.add_parser("export", help="export portable package (no secrets)")
    x.add_argument("role_id")

    sub.add_parser("list", help="list role ids in the store")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = RoleStore(args.store)
    try:
        if args.cmd == "create":
            role = store.create(_load_json(args.file), role_id=args.role_id)
            _print(role)
        elif args.cmd == "equip":
            _print(
                store.equip(
                    args.role_id,
                    session_id=args.session,
                    harness=args.harness,
                    account_pool=args.account_pool,
                    seat=args.seat,
                )
            )
        elif args.cmd == "transfer":
            _print(
                store.transfer(
                    args.role_id,
                    to_session_id=args.to_session,
                    to_harness=args.to_harness,
                    from_session_id=args.from_session,
                    account_pool=args.account_pool,
                    seat=args.seat,
                )
            )
        elif args.cmd == "inspect":
            _print(store.inspect(args.role_id))
        elif args.cmd == "export":
            _print(store.export_package(args.role_id))
        elif args.cmd == "list":
            _print({"roles": store.list_ids()})
        else:
            raise RoleError(f"unknown command: {args.cmd}")
    except RoleError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
