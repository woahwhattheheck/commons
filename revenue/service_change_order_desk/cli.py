from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path
from typing import Any

from .desk import DeskError, build_package, canonical_json, strict_json_loads, verify_package
from .fixture import acceptance_manifest, build_fixture

MAX_INPUT_BYTES = 2_000_000


def _read_json(path_text: str) -> Any:
    path = Path(path_text)
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise DeskError("INPUT_READ_FAILED", f"{path}:{exc}") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise DeskError("INPUT_NOT_REGULAR_FILE", str(path))
    if metadata.st_size > MAX_INPUT_BYTES:
        raise DeskError("INPUT_TOO_LARGE", str(path))
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise DeskError("INPUT_READ_FAILED", f"{path}:{exc}") from exc
    if len(data) != metadata.st_size:
        raise DeskError("INPUT_CHANGED_DURING_READ", str(path))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DeskError("INPUT_NOT_UTF8", str(path)) from exc
    return strict_json_loads(text)


def _safe_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise DeskError("OUTPUT_SYMLINK_FORBIDDEN", str(path))
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    if temporary.exists():
        temporary.unlink()
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _emit(value: Any) -> None:
    sys.stdout.write(canonical_json(value) + "\n")


def _package_command(args: argparse.Namespace) -> int:
    baseline = _read_json(args.baseline)
    change = _read_json(args.change)
    events = _read_json(args.events)
    package = build_package(
        baseline,
        change,
        events,
        expected_baseline_sha256=args.expected_baseline_sha256,
        evaluation_time=args.evaluation_time,
    )
    output_dir = Path(args.output_dir)
    _safe_write(output_dir / "change-order-package.json", canonical_json(package) + "\n")
    _safe_write(output_dir / "change-order.md", package["markdown"])
    verification = verify_package(package)
    _safe_write(output_dir / "verification.json", canonical_json(verification) + "\n")
    _emit({
        "status": package["receipt"]["status"],
        "hold_codes": package["receipt"]["hold_codes"],
        "package_sha256": package["package_sha256"],
        "output_dir": str(output_dir),
    })
    return 2 if package["receipt"]["status"] == "HOLD" else 0


def _verify_command(args: argparse.Namespace) -> int:
    package = _read_json(args.package)
    _emit(verify_package(package))
    return 0


def _fixture_command(args: argparse.Namespace) -> int:
    fixture = build_fixture(approved=False)
    approved = build_fixture(approved=True)
    output_dir = Path(args.output_dir)
    files = {
        "baseline.json": fixture["baseline"],
        "change.json": fixture["change"],
        "events.json": fixture["events"],
        "change-order-package.json": fixture["package"],
        "approved-package.json": approved["package"],
        "verification.json": fixture["verification"],
        "acceptance-manifest.json": acceptance_manifest(),
    }
    for filename, value in files.items():
        _safe_write(output_dir / filename, canonical_json(value) + "\n")
    _safe_write(output_dir / "change-order.md", fixture["package"]["markdown"])
    _emit({
        "status": fixture["package"]["receipt"]["status"],
        "expected_baseline_sha256": fixture["expected_baseline_sha256"],
        "package_sha256": fixture["package"]["package_sha256"],
        "manifest_sha256": acceptance_manifest()["manifest_sha256"],
        "output_dir": str(output_dir),
    })
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline service change-order custody desk")
    subparsers = parser.add_subparsers(dest="command", required=True)

    package = subparsers.add_parser("package", help="Build and verify a deterministic package")
    package.add_argument("--baseline", required=True)
    package.add_argument("--change", required=True)
    package.add_argument("--events", required=True)
    package.add_argument("--expected-baseline-sha256", required=True)
    package.add_argument("--evaluation-time", required=True, help="Trusted UTC time, YYYY-MM-DDTHH:MM:SSZ")
    package.add_argument("--output-dir", required=True)
    package.set_defaults(func=_package_command)

    verify = subparsers.add_parser("verify", help="Verify package structure and internal integrity")
    verify.add_argument("package")
    verify.set_defaults(func=_verify_command)

    fixture = subparsers.add_parser("fixture", help="Write a deterministic synthetic judge fixture")
    fixture.add_argument("--output-dir", required=True)
    fixture.set_defaults(func=_fixture_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return int(args.func(args))
    except DeskError as exc:
        _emit({"status": "ERROR", "code": exc.code, "detail": exc.detail})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
