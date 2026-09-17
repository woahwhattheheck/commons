from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from laundry_desk import LaundryDesk


def _export_stem(prefix: str, object_id: str) -> str:
    readable = f"{prefix}-{object_id.replace(':', '_')}"
    if len((readable + ".json").encode("utf-8")) <= 240:
        return readable
    digest = hashlib.sha256(object_id.encode("utf-8")).hexdigest()
    return f"{prefix}-sha256-{digest}"


def _write_export_bundle(out: Path, prefix: str, object_id: str, exports: dict[str, str]) -> dict[str, str]:
    out.mkdir(parents=True, exist_ok=True)
    if out.is_symlink():
        raise RuntimeError("refusing symlink export directory")

    suffixes = {"json": "json", "csv": "csv", "markdown": "md"}
    stem = _export_stem(prefix, object_id)
    planned: list[tuple[str, Path, str]] = []
    for kind, text in exports.items():
        if kind not in suffixes:
            raise RuntimeError(f"unsupported export kind: {kind}")
        target = out / f"{stem}.{suffixes[kind]}"
        planned.append((kind, target, text))

    occupied = [target for _, target, _ in planned if target.exists() or target.is_symlink()]
    if occupied:
        raise FileExistsError(f"refusing to overwrite existing export path: {occupied[0]}")

    created_paths: list[Path] = []
    created: dict[str, str] = {}
    try:
        for kind, target, text in planned:
            with target.open("x", encoding="utf-8", newline="") as handle:
                handle.write(text)
                handle.flush()
            created_paths.append(target)
            created[kind] = str(target)
    except BaseException:
        for target in reversed(created_paths):
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        raise
    return created


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
        prefix = "route" if route_mode else "customer"
        created = _write_export_bundle(out, prefix, object_id, exports)
        result = {"created": created, "authority": {k: False for k in ["customer_messaging","provider_navigation","accounting_mutation","payment_mutation","deployment","revenue_assertion"]}}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
