from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

from .current import (
    HISTORICAL_MODE,
    compile_current_dossier,
    compile_historical_dossier,
    verify_current_dossier,
    verify_historical_dossier,
)
from .engine import DossierError, canonical_bytes, render_markdown, strict_json_loads

MAX_INPUT = 1_048_576
_READ_CHUNK = 64 * 1024


def _timestamp_ns(st: os.stat_result, name: str) -> int:
    ns_name = f"st_{name}_ns"
    if hasattr(st, ns_name):
        return int(getattr(st, ns_name))
    return int(getattr(st, f"st_{name}") * 1_000_000_000)


def _generation_fingerprint(st: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(st.st_dev),
        int(st.st_ino),
        int(stat.S_IFMT(st.st_mode)),
        int(st.st_size),
        _timestamp_ns(st, "mtime"),
        _timestamp_ns(st, "ctime"),
    )


def read_regular(path: str) -> str:
    p = Path(path)
    inspected = os.lstat(p)
    if not stat.S_ISREG(inspected.st_mode):
        raise DossierError(f"not a regular input file: {path}")
    if inspected.st_size > MAX_INPUT:
        raise DossierError(f"input too large: {path}")

    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise DossierError("platform does not provide O_NOFOLLOW for safe input reads")
    fd = os.open(p, flags | nofollow)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise DossierError(f"not a regular input file: {path}")
        if opened.st_size > MAX_INPUT:
            raise DossierError(f"input too large: {path}")
        opened_generation = _generation_fingerprint(opened)
        if _generation_fingerprint(inspected) != opened_generation:
            raise DossierError(f"input changed before open: {path}")

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(_READ_CHUNK, MAX_INPUT + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_INPUT:
                raise DossierError(f"input too large: {path}")
            chunks.append(chunk)

        finished = os.fstat(fd)
        if _generation_fingerprint(finished) != opened_generation:
            raise DossierError(f"input changed during read: {path}")
        data = b"".join(chunks)
        if len(data) != opened.st_size:
            raise DossierError(f"input changed during read: {path}")
    finally:
        os.close(fd)
    return data.decode("utf-8")


def write_new(path: str, data: bytes) -> None:
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("short write")
            view = view[n:]
    finally:
        os.close(fd)


def _render_output(dossier: dict) -> str:
    rendered = render_markdown(dossier)
    if dossier.get("evaluation_mode") == HISTORICAL_MODE:
        rendered = rendered.replace(
            "## What we can show now",
            "## What was evidenced at replay time",
            1,
        )
        return (
            "# NON-CURRENT HISTORICAL REPLAY\n\n"
            "This deterministic replay is for integrity/debugging only. "
            "It cannot establish current readiness.\n\n"
            + rendered
        )
    return rendered


def main(argv: list[str] | None = None) -> int:
    """Compile/verify the unprivileged prospect-safe surface.

    Public CLI use owns its evaluation clock: no caller-supplied timestamp can
    create or verify CURRENT readiness. Historical replay is a library/test
    boundary only. A hidden argv-injection compatibility seam exists solely for
    retained programmatic tests and always yields HISTORICAL_INTEGRITY_ONLY /
    NON_CURRENT output; public command-line invocation rejects that flag.

    Deliberately no CLI flag accepts commercial-truth authority. Hosts that
    independently authenticate buyer/payment/accounting facts must call the
    engine/current library APIs with their retained trust map.
    """
    ap = argparse.ArgumentParser(
        description="Compile and verify prospect-safe Commons SwarmOps evidence dossiers"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    cp = sub.add_parser("compile")
    cp.add_argument("packet")
    cp.add_argument("policy")
    cp.add_argument(
        "--as-of",
        dest="historical_as_of",
        help=argparse.SUPPRESS,
    )
    cp.add_argument("--json-out", required=True)
    cp.add_argument("--markdown-out", required=True)

    vp = sub.add_parser("verify")
    vp.add_argument("packet")
    vp.add_argument("policy")
    vp.add_argument("candidate")
    vp.add_argument(
        "--as-of",
        dest="historical_as_of",
        help=argparse.SUPPRESS,
    )

    public_invocation = argv is None
    ns = ap.parse_args(argv)
    if public_invocation and ns.historical_as_of is not None:
        ap.error(
            "--as-of is not accepted by the public current CLI; "
            "use compile_historical_dossier()/verify_historical_dossier()"
        )
    try:
        packet = strict_json_loads(read_regular(ns.packet))
        policy = strict_json_loads(read_regular(ns.policy))

        if ns.cmd == "compile":
            if ns.historical_as_of is None:
                dossier = compile_current_dossier(packet, policy, {})
                exit_code = 0 if dossier["status"] == "READY_FOR_OWNER_REVIEW" else 2
            else:
                dossier = compile_historical_dossier(packet, policy, ns.historical_as_of, {})
                exit_code = 0
            write_new(ns.json_out, canonical_bytes(dossier) + b"\n")
            write_new(ns.markdown_out, _render_output(dossier).encode("utf-8"))
            return exit_code

        candidate = strict_json_loads(read_regular(ns.candidate))
        if ns.historical_as_of is None:
            verified = verify_current_dossier(packet, policy, candidate, {})
        else:
            verified = verify_historical_dossier(packet, policy, ns.historical_as_of, candidate, {})
        return 0 if verified else 3
    except (DossierError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
