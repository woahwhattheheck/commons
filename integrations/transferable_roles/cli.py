#!/usr/bin/env python3
"""CLI entry for transferable roles.

Examples:
  python3 integrations/transferable_roles/cli.py create --file fixtures/synthetic_crm_followup_role.json --store /tmp/roles
  python3 integrations/transferable_roles/cli.py equip ROLE --session A --harness cursor --seat HINGE --store /tmp/roles
  python3 integrations/transferable_roles/cli.py bind-route ROLE --route grokbot_control_g2 --session-id sess-1 --last-run-id run-9 --store /tmp/roles
  python3 integrations/transferable_roles/cli.py transfer ROLE --from-session A --to-session B --to-harness claude --seat TENON --store /tmp/roles
  python3 integrations/transferable_roles/cli.py release ROLE --from-session A --store /tmp/roles
  python3 integrations/transferable_roles/cli.py advance-obligation ROLE --id ob-1 --status done --evidence-pointer p/example.md --store /tmp/roles
  python3 integrations/transferable_roles/cli.py export ROLE --store /tmp/roles
  python3 integrations/transferable_roles/cli.py import --file /tmp/role-export.json --store /tmp/roles-successor
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

    b = sub.add_parser(
        "bind-route",
        help="stamp durable G2 session_id/last_run_id onto a named access_route",
    )
    b.add_argument("role_id")
    b.add_argument("--route", required=True, help="access_route.name")
    b.add_argument("--session-id", help="durable G2 conversation id")
    b.add_argument("--last-run-id", help="last G2 run_id")
    b.add_argument("--pool-id", help="pool name only; never invent a second pool")

    r = sub.add_parser(
        "release",
        help="clear occupant so a later session can equip (keeps bound routes)",
    )
    r.add_argument("role_id")
    r.add_argument(
        "--from-session",
        help="optional guard: must match current occupant.session_id",
    )

    a = sub.add_parser(
        "advance-obligation",
        help="update one obligation status/next_action/evidence (not credentials)",
    )
    a.add_argument("role_id")
    a.add_argument("--id", required=True, dest="obligation_id", help="obligation.id")
    a.add_argument("--status", help="open|done|blocked|deferred")
    a.add_argument("--next-action")
    a.add_argument("--evidence-pointer")

    i = sub.add_parser("inspect", help="print role record")
    i.add_argument("role_id")

    x = sub.add_parser("export", help="export portable package (no secrets)")
    x.add_argument("role_id")

    m = sub.add_parser(
        "import",
        help="import export_package JSON without reminting role_id",
    )
    m.add_argument("--file", type=Path, required=True, help="JSON package path")

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
        elif args.cmd == "bind-route":
            _print(
                store.bind_access_route(
                    args.role_id,
                    route_name=args.route,
                    session_id=args.session_id,
                    last_run_id=args.last_run_id,
                    pool_id=args.pool_id,
                )
            )
        elif args.cmd == "release":
            _print(
                store.release(
                    args.role_id,
                    from_session_id=args.from_session,
                )
            )
        elif args.cmd == "advance-obligation":
            _print(
                store.advance_obligation(
                    args.role_id,
                    args.obligation_id,
                    status=args.status,
                    next_action=args.next_action,
                    evidence_pointer=args.evidence_pointer,
                )
            )
        elif args.cmd == "inspect":
            _print(store.inspect(args.role_id))
        elif args.cmd == "export":
            _print(store.export_package(args.role_id))
        elif args.cmd == "import":
            _print(store.import_package(_load_json(args.file)))
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
