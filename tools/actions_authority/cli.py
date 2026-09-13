from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from .authority import classify
from .common import EvidenceError, _canonical_bytes, _time, parse_json_bytes


def _same_existing_file(left: Path, right: Path) -> bool:
    try:
        return os.path.samefile(left, right)
    except (FileNotFoundError, OSError):
        return False


def _read_input(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError("input must be an existing ordinary non-symlink file")
    return path.read_bytes()


def _publish_create_exclusive(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise EvidenceError("output already exists")
    parent = path.parent
    if not parent.is_dir():
        raise EvidenceError("output parent must be an existing directory")
    fd, stage_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".stage", dir=parent)
    stage = Path(stage_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(stage, path)
        except FileExistsError as exc:
            raise EvidenceError("output already exists") from exc
        try:
            dir_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify policy-bound exact-head GitHub Actions evidence without calling GitHub."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-age-seconds", type=int, default=1800)
    parser.add_argument("--max-future-skew-seconds", type=int, default=300)
    parser.add_argument("--now", help="Explicit ISO-8601 evaluation time for reproducible/offline verification")
    args = parser.parse_args(argv)

    try:
        source_path = args.input.absolute()
        raw = _read_input(source_path)
        input_path = source_path.resolve(strict=True)
        output_path = args.out.absolute()
        if output_path.is_symlink() or _same_existing_file(input_path, output_path):
            raise EvidenceError("input and output must not alias")
        payload = parse_json_bytes(raw)
        now = _time(args.now, "--now") if args.now is not None else None
        receipt = classify(
            payload,
            now=now,
            max_age_seconds=args.max_age_seconds,
            max_future_skew_seconds=args.max_future_skew_seconds,
        )
        _publish_create_exclusive(output_path, _canonical_bytes(receipt))
        return 3
    except (EvidenceError, OSError) as exc:
        print(f"ACTIONS_AUTHORITY_ERROR: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
