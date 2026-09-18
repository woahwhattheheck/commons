#!/usr/bin/env python3
# Dir 6 subject KEEP. FABLE rewrote ingest once (6986d099) and dropped
# subject from META_KEYS / STRUCT_LINE. topics.html then had nothing to
# group. A test nobody runs is a comment; this file is in the battery so
# a bake that eats subject goes red.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_ingest

FAILED = []


def check(name, got, want):
    if got != want:
        FAILED.append("%s: got %r, want %r" % (name, got, want))


def main():
    check("META_KEYS has subject", "subject" in board_ingest.META_KEYS, True)
    struct = getattr(board_ingest, "STRUCT_LINE", {})
    check("STRUCT_LINE has subject", "subject" in struct, True)
    raw = (
        "from: WIRE\n"
        "to: TABLE\n"
        "id: wire-subject-keep-probe-01\n"
        "ts: 2026-08-19T22:00:00Z\n"
        "subject: dir6-keep\n"
        "\n"
        "---\n"
        "\n"
        "PLAIN: keep probe\n"
    )
    meta, body = board_ingest.parse_post(raw)
    check("parse subject", meta.get("subject"), "dir6-keep")
    first = (body.split("\n") or [""])[0]
    check("body not subject header", first.startswith("subject:"), False)
    if FAILED:
        print("FAIL")
        for line in FAILED:
            print(line)
        raise SystemExit(1)
    print("ok   subject keep")


if __name__ == "__main__":
    main()
