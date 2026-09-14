from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from core import StudioStore, canonical_bytes, loads_strict, sha256_bytes, verify_bundle


def write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def command_demo(args: argparse.Namespace) -> dict:
    fixture = loads_strict(Path(args.fixture).read_bytes())
    store = StudioStore(args.db)
    workspace = store.configure_workspace(
        fixture["workspace"], request_key="demo-workspace-v1", expected_revision=None
    )
    plan = store.save_plan(fixture["plan"], request_key="demo-plan-v1", expected_revision=None)
    support = store.create_support_handoff(
        {
            "plan_id": fixture["plan"]["plan_id"],
            "category": "LAUNCH_REVIEW",
            "description": "Please review the first branded class plan before creator handoff.",
            "contact_preference": "LOCAL_OWNER_REVIEW",
        },
        request_key="demo-support-v1",
    )
    bundle = store.export_bundle(fixture["plan"]["plan_id"])
    output = Path(args.output)
    write_exclusive(output, bundle)
    verified = verify_bundle(bundle)
    return {
        "workspace": workspace,
        "plan": plan,
        "support": support,
        "bundle": {"path": str(output), "bytes": len(bundle), "sha256": sha256_bytes(bundle)},
        "verification": verified,
    }


def command_export(args: argparse.Namespace) -> dict:
    store = StudioStore(args.db)
    bundle = store.export_bundle(args.plan_id)
    output = Path(args.output)
    write_exclusive(output, bundle)
    return {
        "status": "EXPORTED",
        "plan_id": args.plan_id,
        "path": str(output),
        "bytes": len(bundle),
        "sha256": sha256_bytes(bundle),
        "verification": verify_bundle(bundle),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Creator-backed niche app studio CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="build the checked-in synthetic ceramics workspace")
    demo.add_argument("--db", required=True)
    demo.add_argument("--fixture", default="example_workspace.json")
    demo.add_argument("--output", required=True)
    demo.set_defaults(func=command_demo)

    export = sub.add_parser("export", help="export an existing persisted plan")
    export.add_argument("--db", required=True)
    export.add_argument("--plan-id", required=True)
    export.add_argument("--output", required=True)
    export.set_defaults(func=command_export)

    verify = sub.add_parser("verify", help="verify a deterministic export bundle")
    verify.add_argument("bundle")
    verify.set_defaults(func=lambda args: verify_bundle(Path(args.bundle).read_bytes()))

    args = parser.parse_args()
    result = args.func(args)
    print(canonical_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
