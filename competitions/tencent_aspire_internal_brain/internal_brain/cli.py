from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import AuditError, AuthorizationError, BrainError, InternalBrain, SchemaError, strict_loads, verify_audit


def _load(path: str):
    return strict_loads(Path(path).read_text("utf-8"))


def _emit(value) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tencent Aspire Internal Brain local reference engine")
    sub = parser.add_subparsers(dest="command", required=True)

    query = sub.add_parser("query", help="run an authorized deterministic retrieval")
    query.add_argument("bundle")
    query.add_argument("request")
    query.add_argument("--audit-out")

    verify = sub.add_parser("verify-audit", help="verify an exported tamper-evident audit chain")
    verify.add_argument("audit")

    validate = sub.add_parser("validate", help="strictly validate and normalize a bundle")
    validate.add_argument("bundle")

    args = parser.parse_args(argv)
    try:
        if args.command == "query":
            brain = InternalBrain(_load(args.bundle))
            result = brain.query(_load(args.request))
            _emit(result)
            if args.audit_out:
                Path(args.audit_out).write_text(
                    json.dumps(brain._audit, indent=2, sort_keys=True) + "\n", "utf-8"
                )
            return 0
        if args.command == "verify-audit":
            raw = _load(args.audit)
            if not isinstance(raw, list):
                raise SchemaError("audit file must contain a JSON list")
            _emit(verify_audit(raw))
            return 0
        brain = InternalBrain(_load(args.bundle))
        normalized = brain.export_bundle()
        _emit({
            "valid": True,
            "tenant_id": brain.tenant_id,
            "roles": len(brain.roles),
            "users": len(brain.users),
            "documents": len(brain.documents),
            "bundle": normalized,
        })
        return 0
    except AuthorizationError as exc:
        _emit({"error": "AuthorizationError", "code": exc.code, "message": str(exc)})
        return 3
    except (SchemaError, AuditError, OSError, json.JSONDecodeError) as exc:
        _emit({"error": type(exc).__name__, "message": str(exc)})
        return 2
    except BrainError as exc:
        _emit({"error": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
