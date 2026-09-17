#!/usr/bin/env python3
"""Reject new public/customer backlinks to Commons infrastructure.

Commons is coordination infrastructure, not a credibility/storefront backlink.
This guard is intentionally diff-scoped by default so historical provenance is
not rewritten. Internal receipts/evidence/tests remain outside the public
surface classifier. Explicit exceptions are exact path+URL grants and require
an owner-approval marker.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Iterable, Mapping, Sequence


EXCEPTION_MANIFEST = Path("public_surface_isolation_exceptions.json")

FORBIDDEN_URL_RE = re.compile(
    r"""https://(?:
        github\.com/woahwhattheheck/commons
        |api\.github\.com/repos/woahwhattheheck/commons
        |raw\.githubusercontent\.com/woahwhattheheck/commons
        |woahwhattheheck\.github\.io/commons
    )(?=$|[/?#])[^ \t\r\n<>\"']*""",
    re.IGNORECASE | re.VERBOSE,
)
_TRAILING_PUNCTUATION = ".,;:!?)]}"

_ALWAYS_PUBLIC_SUFFIXES = {".htm", ".html", ".css", ".svg"}
_PUBLIC_SUFFIXES = {
    ".css", ".htm", ".html", ".js", ".json", ".jsx", ".md", ".markdown",
    ".mjs", ".rst", ".svg", ".ts", ".tsx", ".txt", ".vue", ".xml",
    ".yaml", ".yml",
}
_PUBLIC_DIR_HINTS = {
    "commercial", "customer", "customers", "demo", "demos", "deliverable",
    "deliverables", "docs", "landing", "outreach", "p", "pages", "proposal",
    "proposals", "public", "report", "reports", "site", "storefront", "web",
    "website",
}
_PUBLIC_NAME_HINTS = {
    "commerce", "commercial", "customer", "demo", "deliverable", "diagnostic",
    "expertise", "landing", "outreach", "proposal", "public", "report",
    "storefront",
}
_INTERNAL_DIR_HINTS = {
    ".agents", ".claude", ".codex", ".cursor", ".gemini", ".git", ".github",
    "__pycache__", "builds", "chunks", "ci", "evidence", "excerpts",
    "fixtures", "host", "node_modules", "receipts", "records", "tests",
    "vendor",
}
_INTERNAL_FILES = {
    EXCEPTION_MANIFEST.as_posix(),
    "public_surface_isolation_guard.py",
    "test_public_surface_isolation_guard.py",
}


class GuardError(RuntimeError):
    """Invalid input or repository state."""


@dataclass(frozen=True)
class ExceptionGrant:
    path: str
    url: str
    owner_approval: str
    reason: str


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    url: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: forbidden Commons public backlink: {self.url}"


def _norm_path(raw: str) -> str:
    value = str(raw).replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if not value or value.startswith("/"):
        raise GuardError(f"invalid repository-relative path: {raw!r}")
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise GuardError(f"invalid repository-relative path: {raw!r}")
    return PurePosixPath(*parts).as_posix()


def _trim_url(raw: str) -> str:
    return raw.rstrip(_TRAILING_PUNCTUATION)


def _forbidden_urls(text: str) -> Iterable[tuple[int, str]]:
    for line_no, line in enumerate(text.splitlines(), 1):
        for match in FORBIDDEN_URL_RE.finditer(line):
            url = _trim_url(match.group(0))
            if url:
                yield line_no, url


def is_public_surface(path: str) -> bool:
    """Classify externally consumable files without sweeping internal receipts."""
    normalized = _norm_path(path)
    if normalized in _INTERNAL_FILES:
        return False

    pure = PurePosixPath(normalized)
    suffix = pure.suffix.lower()
    if suffix not in _PUBLIC_SUFFIXES:
        return False

    directories = {part.lower() for part in pure.parts[:-1]}
    if directories & _INTERNAL_DIR_HINTS:
        return False

    if suffix in _ALWAYS_PUBLIC_SUFFIXES:
        return True
    if len(pure.parts) == 1:
        return True
    if directories & _PUBLIC_DIR_HINTS:
        return True

    stem_words = {
        token for token in re.split(r"[^a-z0-9]+", pure.stem.lower()) if token
    }
    return bool(stem_words & _PUBLIC_NAME_HINTS)


def load_exceptions(path: Path = EXCEPTION_MANIFEST) -> Mapping[tuple[str, str], ExceptionGrant]:
    if not path.exists():
        raise GuardError(f"exception manifest missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GuardError(f"cannot read exception manifest {path}: {exc}") from exc

    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise GuardError("exception manifest must be an object with version=1")
    entries = payload.get("exceptions")
    if not isinstance(entries, list):
        raise GuardError("exception manifest 'exceptions' must be a list")

    grants: dict[tuple[str, str], ExceptionGrant] = {}
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            raise GuardError(f"exception #{index} must be an object")
        required = {"path", "url", "owner_approval", "reason"}
        if set(item) != required:
            raise GuardError(
                f"exception #{index} must contain exactly {sorted(required)}"
            )
        if not all(isinstance(item[key], str) and item[key].strip() for key in required):
            raise GuardError(f"exception #{index} fields must be non-empty strings")

        normalized = _norm_path(item["path"])
        url = _trim_url(item["url"].strip())
        if FORBIDDEN_URL_RE.fullmatch(url) is None:
            raise GuardError(f"exception #{index} url is not a Commons backlink: {url}")
        approval = item["owner_approval"].strip()
        if not approval.startswith("OWNER-APPROVED:"):
            raise GuardError(
                f"exception #{index} owner_approval must start with 'OWNER-APPROVED:'"
            )
        grant = ExceptionGrant(
            path=normalized,
            url=url,
            owner_approval=approval,
            reason=item["reason"].strip(),
        )
        key = (grant.path, grant.url)
        if key in grants:
            raise GuardError(f"duplicate exception for {grant.path} {grant.url}")
        grants[key] = grant
    return grants


def scan_text(
    path: str,
    text: str,
    grants: Mapping[tuple[str, str], ExceptionGrant],
) -> list[Violation]:
    normalized = _norm_path(path)
    if not is_public_surface(normalized):
        return []
    violations = []
    for line_no, url in _forbidden_urls(text):
        if (normalized, url) not in grants:
            violations.append(Violation(normalized, line_no, url))
    return violations


def scan_paths(
    paths: Iterable[str],
    grants: Mapping[tuple[str, str], ExceptionGrant],
) -> list[Violation]:
    violations: list[Violation] = []
    for raw in paths:
        normalized = _norm_path(raw)
        if not is_public_surface(normalized):
            continue
        source = Path(normalized)
        if not source.is_file():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise GuardError(f"cannot read public surface {normalized}: {exc}") from exc
        violations.extend(scan_text(normalized, text, grants))
    return violations


def _git_paths(args: Sequence[str]) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        raise GuardError(f"git {' '.join(args)} failed: {detail}".strip()) from exc
    try:
        return [
            item.decode("utf-8")
            for item in completed.stdout.split(b"\0")
            if item
        ]
    except UnicodeDecodeError as exc:
        raise GuardError("git returned a non-UTF-8 path") from exc


def changed_paths(base: str, head: str = "HEAD") -> list[str]:
    if not base or not head:
        raise GuardError("base and head must be non-empty")
    return _git_paths(
        ["diff", "--name-only", "--diff-filter=ACMR", "-z", f"{base}...{head}", "--"]
    )


def all_candidate_paths() -> list[str]:
    return _git_paths(["ls-files", "-z"])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exceptions",
        type=Path,
        default=EXCEPTION_MANIFEST,
        help="exact path+URL exception manifest",
    )
    parser.add_argument("--head", default="HEAD", help="head revision for --base mode")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base", help="scan added/modified/renamed files in BASE...HEAD")
    source.add_argument("--all", action="store_true", help="scan all tracked public surfaces")
    source.add_argument("--paths", nargs="+", help="scan only these repository-relative paths")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        grants = load_exceptions(args.exceptions)
        if args.base:
            paths = changed_paths(args.base, args.head)
        elif args.all:
            paths = all_candidate_paths()
        else:
            paths = list(args.paths)
        violations = scan_paths(paths, grants)
    except GuardError as exc:
        print(f"PUBLIC_SURFACE_ISOLATION_ERROR: {exc}", file=sys.stderr)
        return 2

    if violations:
        print(
            "PUBLIC_SURFACE_ISOLATION_BLOCKED: customer/public surfaces must not "
            "backlink to Commons infrastructure.",
            file=sys.stderr,
        )
        for violation in violations:
            print(violation.render(), file=sys.stderr)
        print(
            "Use a product/repository-specific customer route instead. Internal "
            "receipts and provenance may retain Commons references outside public "
            "customer surfaces. Exceptions require an exact path+URL owner approval.",
            file=sys.stderr,
        )
        return 1

    print(f"PUBLIC_SURFACE_ISOLATION_OK scanned_paths={len(paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
