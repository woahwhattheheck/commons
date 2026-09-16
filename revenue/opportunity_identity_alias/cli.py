"""Offline CLI over the repository-carried current opportunity alias registry."""
from __future__ import annotations

import argparse
import json
import stat
import sys
from pathlib import Path

from .registry import validate_transition
from .resolver import resolve_current, verify_current
from .strict import IdentityAliasError, MAX_JSON_BYTES, canonical_json, strict_json_loads


def _load(path: str):
    target = Path(path)
    try:
        st = target.lstat()
    except OSError as exc:
        raise IdentityAliasError(f"input unavailable: {path}") from exc
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise IdentityAliasError(f"input must be an ordinary non-symlink file: {path}")
    if st.st_size > MAX_JSON_BYTES:
        raise IdentityAliasError(f"input exceeds size limit: {path}")
    try:
        raw = target.read_bytes()
    except OSError as exc:
        raise IdentityAliasError(f"input read failed: {path}") from exc
    if len(raw) > MAX_JSON_BYTES:
        raise IdentityAliasError(f"input exceeds size limit: {path}")
    try:
        return strict_json_loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise IdentityAliasError(f"input is not UTF-8: {path}") from exc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser("resolve-current"); resolve.add_argument("observation")
    verify = sub.add_parser("verify-current"); verify.add_argument("observation"); verify.add_argument("result")
    transition = sub.add_parser("validate-transition"); transition.add_argument("previous"); transition.add_argument("candidate")
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve-current":
            out = resolve_current(_load(args.observation))
        elif args.command == "verify-current":
            out = {"verified": verify_current(_load(args.observation), _load(args.result))}
            if not out["verified"]:
                print(json.dumps(out, sort_keys=True, separators=(",", ":")), file=sys.stderr)
                return 2
        else:
            out = validate_transition(_load(args.previous), _load(args.candidate))
        sys.stdout.buffer.write(canonical_json(out) + b"\n")
        return 0
    except (IdentityAliasError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
