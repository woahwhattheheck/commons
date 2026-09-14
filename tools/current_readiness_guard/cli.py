from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .guard import Finding, PolicyError, load_policy, scan_paths

DEFAULT_POLICY = Path(__file__).with_name("policy.json")


def _policy(path: Path):
    try:
        return load_policy(path.read_bytes())
    except OSError as exc:
        raise PolicyError(f"cannot read policy: {exc}") from exc


def _emit(findings: list[Finding], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps([f.to_dict() for f in findings], sort_keys=True, separators=(",", ":")))
        return
    for f in findings:
        suffix = f" [{f.function}]" if f.function else ""
        print(f"{f.path}:{f.line}:{f.col}: {f.rule} {f.message}{suffix}")
    if findings:
        print(f"current-readiness-guard: {len(findings)} finding(s)")
    else:
        print("current-readiness-guard: PASS")


def _changed(base: str, head: str) -> list[str]:
    for rev in (base, head):
        if not rev or rev.startswith("-") or any(ch.isspace() for ch in rev):
            raise PolicyError("git revisions must be nonempty tokens")
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...{head}", "--", "revenue"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise PolicyError(f"git diff failed: {exc}") from exc
    if proc.returncode != 0:
        raise PolicyError(f"git diff failed: {proc.stderr.strip() or proc.returncode}")
    return sorted({line.strip() for line in proc.stdout.splitlines() if line.strip().endswith(".py")})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prevent caller-minted current readiness in changed revenue Python")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("paths", nargs="+")
    sub.add_parser("all", help="advisory full-repository revenue Python audit")
    changed = sub.add_parser("changed")
    changed.add_argument("--base", required=True)
    changed.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    try:
        exemptions = _policy(args.policy)
        if args.command == "scan":
            paths = args.paths
        elif args.command == "changed":
            paths = _changed(args.base, args.head)
        else:
            paths = [p.relative_to(Path.cwd()).as_posix() for p in sorted(Path.cwd().glob("revenue/**/*.py"))]
        findings = scan_paths(paths, root=Path.cwd(), exemptions=exemptions)
    except PolicyError as exc:
        print(f"current-readiness-guard policy/error: {exc}", file=sys.stderr)
        return 2
    _emit(findings, as_json=args.as_json)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
