from __future__ import annotations

import argparse
import json
from pathlib import Path

from laundry_desk import LaundryDesk


def main() -> int:
    parser = argparse.ArgumentParser(description="Commercial Laundry Route & Linen Custody Operations Desk")
    parser.add_argument("database", help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("route-snapshot")
    p.add_argument("route_id")
    p = sub.add_parser("customer-snapshot")
    p.add_argument("customer_id")
    p = sub.add_parser("integrity")
    p = sub.add_parser("export-route")
    p.add_argument("route_id")
    p.add_argument("directory")
    p = sub.add_parser("export-customer")
    p.add_argument("customer_id")
    p.add_argument("directory")

    args = parser.parse_args()
    desk = LaundryDesk(args.database)
    if args.command == "route-snapshot":
        result = desk.route_snapshot(args.route_id)
    elif args.command == "customer-snapshot":
        result = desk.customer_snapshot(args.customer_id)
    elif args.command == "integrity":
        result = desk.verify_integrity()
    else:
        route_mode = args.command == "export-route"
        object_id = args.route_id if route_mode else args.customer_id
        exports = desk.render_route_exports(object_id) if route_mode else desk.render_customer_exports(object_id)
        out = Path(args.directory)
        out.mkdir(parents=True, exist_ok=True)
        if out.is_symlink():
            raise RuntimeError("refusing symlink export directory")
        prefix = "route" if route_mode else "customer"
        created = {}
        for kind, text in exports.items():
            suffix = {"json": "json", "csv": "csv", "markdown": "md"}[kind]
            target = out / f"{prefix}-{object_id.replace(':','_')}.{suffix}"
            with target.open("x", encoding="utf-8", newline="") as handle:
                handle.write(text)
            created[kind] = str(target)
        result = {"created": created, "authority": {k: False for k in ["customer_messaging","provider_navigation","accounting_mutation","payment_mutation","deployment","revenue_assertion"]}}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
