from __future__ import annotations

"""Recovered production boundary for the Vetter tech-transfer evidence gate.

The predecessor implementation is retained byte-for-byte in ``_engine_v1.py``.
This facade owns production ingress/currentness and patches the retained
normalizer so every public compile path enforces snapshot chronology.
"""

import errno

try:  # package import
    from . import _engine_v1 as _impl
except ImportError:  # direct ``python engine.py`` / cwd tests
    import _engine_v1 as _impl

# Preserve the predecessor implementation surface for compatibility. Function
# objects copied here still retain _engine_v1's globals, which is intentional;
# the boundary functions below are redefined explicitly and, where necessary,
# installed back into that module's lookup graph.
for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

_ORIGINAL_NORMALIZE_SNAPSHOT = _impl.normalize_snapshot
_HISTORICAL_VERIFY_REPORT = _impl.verify_report


def _validate_snapshot_chronology(value: object, name: str) -> None:
    """Reject observations that claim to occur after their snapshot capture."""
    if type(value) is not dict:
        return  # retained validator owns the canonical type error
    captured_raw = value.get("captured_at_utc")
    rows = value.get("rows")
    if captured_raw is None or type(rows) is not list:
        return
    captured = _impl.parse_utc(captured_raw, f"{name}.captured_at_utc")
    for idx, row in enumerate(rows):
        if type(row) is not dict or "last_updated_utc" not in row:
            continue
        updated = _impl.parse_utc(
            row["last_updated_utc"], f"{name}.rows[{idx}].last_updated_utc"
        )
        if updated > captured:
            raise _impl.TransferError(
                f"{name}.rows[{idx}].last_updated_utc is later than snapshot capture"
            )


def normalize_snapshot(
    value: object,
    name: str,
    *,
    expected_role: str,
    as_of: object,
) -> dict[str, object]:
    _validate_snapshot_chronology(value, name)
    return _ORIGINAL_NORMALIZE_SNAPSHOT(
        value, name, expected_role=expected_role, as_of=as_of
    )


# The retained compile function resolves normalize_snapshot through its module
# globals at call time. Install the repaired authority there so direct retained
# callers, package callers, and CLI callers traverse the same chronology gate.
_impl.normalize_snapshot = normalize_snapshot


def compile_transfer(
    source: object, receiving: object, policy: object, *, as_of: str
) -> dict[str, object]:
    return _impl.compile_transfer(source, receiving, policy, as_of=as_of)


def verify_report(report: object) -> dict[str, object]:
    """Historical byte-integrity replay bound to the report's original as_of."""
    return _HISTORICAL_VERIFY_REPORT(report)


def _plain_report_snapshot(snapshot: object, name: str) -> dict[str, object]:
    if type(snapshot) is not dict:
        raise _impl.TransferError(f"report.{name} must be an object")
    expected = set(_impl.SNAPSHOT_KEYS) | {"snapshot_sha256"}
    if set(snapshot) != expected:
        raise _impl.TransferError(f"report.{name} key set invalid")
    return {key: snapshot[key] for key in _impl.SNAPSHOT_KEYS}


def _process_utc_now(
    _datetime=_impl.datetime,
    _timezone=_impl.timezone,
) -> str:
    """Process-owned current UTC; production APIs accept no caller as-of."""
    return _impl.format_utc(_datetime.now(_timezone.utc))


def _semantic_projection(report: object) -> dict[str, object]:
    if type(report) is not dict:
        raise _impl.TransferError("report must be an object")
    return {
        key: value
        for key, value in report.items()
        if key not in {"as_of", "receipt_sha256"}
    }


def _make_current_verifier(
    _clock=_process_utc_now,
    _historical=_HISTORICAL_VERIFY_REPORT,
    _compile=_impl.compile_transfer,
    _plain=_plain_report_snapshot,
    _project=_semantic_projection,
):
    # Binding authority objects into this closure prevents ordinary post-import
    # module-global rebinding from changing the production currentness path.
    def current(report: object) -> dict[str, object]:
        historical = _historical(report)
        if type(report) is not dict:
            raise _impl.TransferError("report must be an object")
        now = _clock()
        rebuilt = _compile(
            _plain(report["source"], "source"),
            _plain(report["receiving"], "receiving"),
            report["policy"],
            as_of=now,
        )
        if _project(rebuilt) != _project(report):
            raise _impl.TransferError(
                "report is no longer current: decision semantics changed at process UTC"
            )
        return {
            "verified": True,
            "historical_replay_verified": bool(historical["verified"]),
            "state": rebuilt["summary"]["state"],
            "receipt_sha256": historical["receipt_sha256"],
            "current_as_of": now,
            "current_receipt_sha256": rebuilt["receipt_sha256"],
        }

    return current


verify_report_current = _make_current_verifier()


def _fd_fingerprint(st: object) -> tuple[int, int, int, int, int, int]:
    return (
        int(st.st_dev),
        int(st.st_ino),
        int(st.st_mode),
        int(st.st_size),
        int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))),
        int(getattr(st, "st_ctime_ns", int(st.st_ctime * 1_000_000_000))),
    )


def _read_bounded(path: str | _impl.os.PathLike[str]) -> bytes:
    """Read one retained regular-file generation with an in-read hard cap."""
    if not hasattr(_impl.os, "O_NOFOLLOW"):
        raise _impl.TransferError("secure no-follow input open is unavailable")
    flags = _impl.os.O_RDONLY | _impl.os.O_NOFOLLOW
    if hasattr(_impl.os, "O_CLOEXEC"):
        flags |= _impl.os.O_CLOEXEC
    if hasattr(_impl.os, "O_NONBLOCK"):
        flags |= _impl.os.O_NONBLOCK
    try:
        fd = _impl.os.open(path, flags)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.EMLINK}:
            raise _impl.TransferError("input final symlink is forbidden") from None
        raise _impl.TransferError(
            f"unable to open input safely: {exc.strerror or exc}"
        ) from None

    try:
        before = _impl.os.fstat(fd)
        if not _impl.stat.S_ISREG(before.st_mode):
            raise _impl.TransferError("input must be a regular file")
        if before.st_size > MAX_JSON_BYTES:
            raise _impl.TransferError("input exceeds byte limit")

        chunks: list[bytes] = []
        total = 0
        while True:
            remaining = MAX_JSON_BYTES + 1 - total
            if remaining <= 0:
                raise _impl.TransferError("input exceeds byte limit during read")
            chunk = _impl.os.read(fd, min(64 * 1024, remaining))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_JSON_BYTES:
                raise _impl.TransferError("input exceeds byte limit during read")
            chunks.append(chunk)

        after = _impl.os.fstat(fd)
        if _fd_fingerprint(before) != _fd_fingerprint(after):
            raise _impl.TransferError("input generation changed during read")
        if total != after.st_size:
            raise _impl.TransferError("input size changed during read")
        return b"".join(chunks)
    finally:
        _impl.os.close(fd)


# Keep any retained helper that dynamically resolves the ingress function on the
# repaired implementation as well. The facade CLI below never calls the old
# pathname reader directly.
_impl._read_bounded = _read_bounded


def _make_compile_cli(
    _reader=_read_bounded,
    _clock=_process_utc_now,
    _compile=_impl.compile_transfer,
    _load=_impl.load_json_bytes,
    _write_bytes=_impl.write_new_bytes,
    _write_text=_impl.write_new_text,
    _render=_impl.render_markdown,
    _canonical=_impl.canonical_json_bytes,
):
    def run(args: object) -> int:
        request = _impl._exact_object(
            _load(_reader(args.input)), _impl.COMPILE_INPUT_KEYS, "compile input"
        )
        report = _compile(
            request["source"],
            request["receiving"],
            request["policy"],
            as_of=_clock(),
        )
        _write_bytes(args.report, _canonical(report))
        _write_text(args.markdown, _render(report))
        print(
            _impl.json.dumps(
                {
                    "state": report["summary"]["state"],
                    "receipt_sha256": report["receipt_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0

    return run


def _make_verify_cli(
    _reader=_read_bounded,
    _load=_impl.load_json_bytes,
    _verify=verify_report_current,
    _render=_impl.render_markdown,
):
    def run(args: object) -> int:
        report = _load(_reader(args.report))
        result = _verify(report)
        if args.markdown:
            actual = _reader(args.markdown).decode("utf-8")
            if actual != _render(report):
                raise _impl.TransferError("Markdown projection mismatch")
        print(_impl.json.dumps(result, sort_keys=True))
        return 0

    return run


_compile_cli = _make_compile_cli()
_verify_cli = _make_verify_cli()


def _make_main(
    _compile_cli_bound=_compile_cli,
    _verify_cli_bound=_verify_cli,
):
    def run(argv: list[str] | None = None) -> int:
        parser = _impl.argparse.ArgumentParser(
            description="Read-only cross-site clinical fill tech-transfer evidence compiler"
        )
        subs = parser.add_subparsers(dest="command", required=True)
        cp = subs.add_parser("compile")
        cp.add_argument("--input", required=True)
        cp.add_argument("--report", required=True)
        cp.add_argument("--markdown", required=True)
        cp.set_defaults(func=_compile_cli_bound)
        vp = subs.add_parser("verify")
        vp.add_argument("--report", required=True)
        vp.add_argument("--markdown")
        vp.set_defaults(func=_verify_cli_bound)
        args = parser.parse_args(argv)
        try:
            return args.func(args)
        except _impl.TransferError as exc:
            parser.error(str(exc))
        return 2

    return run


main = _make_main()

TransferError = _impl.TransferError
render_markdown = _impl.render_markdown
canonical_json_bytes = _impl.canonical_json_bytes
canonical_sha256 = _impl.canonical_sha256
format_utc = _impl.format_utc
MAX_JSON_BYTES = _impl.MAX_JSON_BYTES

__all__ = [
    "TransferError",
    "compile_transfer",
    "verify_report",
    "verify_report_current",
    "render_markdown",
    "canonical_json_bytes",
    "canonical_sha256",
    "format_utc",
    "normalize_snapshot",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
