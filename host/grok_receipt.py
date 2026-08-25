#!/usr/bin/env python3
"""Normalize one completed Grok Build JSON envelope without trusting scratch.

The Grok Build ``--output-format json`` envelope contains an authoritative
``text`` field and may also contain a non-authoritative ``thought`` field.
This tool accepts exactly one ``json`` fence in ``text``. It never reads or
merges ``thought`` and it never launches Grok, reads account files, or acts as
an authorization gate.

Usage:

  python3 host/grok_receipt.py --check receipt.json
  python3 host/grok_receipt.py --output normalized.json receipt.json
  grok ... --output-format json | python3 host/grok_receipt.py -
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


SCHEMA = "grok-receipt/v1"

EXIT_OK = 0
EXIT_CLI_USAGE = 2
EXIT_MISSING_FILE = 3
EXIT_INVALID_ENVELOPE = 4
EXIT_ZERO_FENCES = 5
EXIT_MULTIPLE_FENCES = 6
EXIT_INVALID_INNER_JSON = 7
EXIT_WRONG_TYPE = 8
EXIT_MISSING_PACKET_ID = 9
EXIT_WRITE_FAILURE = 10
EXIT_FINDER_FAILED = 12

STATUS_BY_EXIT = {
    EXIT_OK: "OK",
    EXIT_CLI_USAGE: "CLI_USAGE",
    EXIT_MISSING_FILE: "MISSING_FILE",
    EXIT_INVALID_ENVELOPE: "INVALID_ENVELOPE",
    EXIT_ZERO_FENCES: "ZERO_FENCES",
    EXIT_MULTIPLE_FENCES: "MULTIPLE_FENCES",
    EXIT_INVALID_INNER_JSON: "INVALID_INNER_JSON",
    EXIT_WRONG_TYPE: "WRONG_TYPE",
    EXIT_MISSING_PACKET_ID: "MISSING_PACKET_ID",
    EXIT_WRITE_FAILURE: "WRITE_FAILURE",
    EXIT_FINDER_FAILED: "FINDER_FAILED",
}

OPTIONAL_OUTER_FIELDS = (
    "stopReason",
    "requestId",
    "num_turns",
    "total_cost_usd",
    "total_cost_usd_ticks",
)


def sha256_hex(raw):
    """SHA-256 of the exact source bytes."""
    return hashlib.sha256(bytes(raw)).hexdigest()


def _source_name(source):
    """Do not echo an absolute/private input path into normalized output."""
    if source in (None, "-"):
        return "-"
    return os.path.basename(os.fspath(source))


def _error(exit_code, message, raw=None, source="-"):
    payload = {
        "schema": SCHEMA,
        "status": STATUS_BY_EXIT[exit_code],
        "exit_code": exit_code,
        "error": str(message),
        "source": {"name": _source_name(source)},
    }
    if raw is not None:
        payload["source"]["bytes"] = len(raw)
        payload["source_sha256"] = sha256_hex(raw)
    return payload, exit_code


def _json_fence(text):
    """Return one JSON fence body or an exact structural failure.

    Grok sometimes appends the opener to the final prose line
    (``answer follows.```json``) rather than emitting CommonMark. Accept that
    measured form only when the marker ends the line. State tracking prevents
    marker strings inside the JSON body from being counted as new fences.
    A complete block followed by an unclosed second opener is ambiguous.
    """
    lines = str(text).splitlines(keepends=True)
    openers = 0
    blocks = []
    body_lines = []
    in_json = False
    for line in lines:
        if not in_json:
            if line.rstrip().lower().endswith("```json"):
                openers += 1
                in_json = True
                body_lines = []
            continue
        if line.strip() == "```":
            blocks.append("".join(body_lines))
            body_lines = []
            in_json = False
        else:
            body_lines.append(line)
    if not openers:
        return None, EXIT_ZERO_FENCES, "text contains no fenced JSON object"
    if openers != 1:
        return (
            None,
            EXIT_MULTIPLE_FENCES,
            "text contains %d JSON fence openers; exactly one is required"
            % openers,
        )
    if in_json or len(blocks) != 1:
        return None, EXIT_INVALID_INNER_JSON, "JSON fence is not closed"
    return blocks[0], EXIT_OK, ""


def evaluate_receipt(raw, source="-"):
    """Validate raw envelope bytes and return ``(normalized, exit_code)``."""
    try:
        envelope = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return _error(
            EXIT_INVALID_ENVELOPE,
            "outer envelope is not UTF-8 JSON: %s" % exc,
            raw,
            source,
        )
    if not isinstance(envelope, dict):
        return _error(
            EXIT_INVALID_ENVELOPE,
            "outer envelope must be an object",
            raw,
            source,
        )

    text = envelope.get("text")
    session_id = envelope.get("sessionId")
    usage = envelope.get("usage")
    model_usage = envelope.get("modelUsage")
    invalid = []
    if not isinstance(text, str):
        invalid.append("text:string")
    if not isinstance(session_id, str) or not session_id.strip():
        invalid.append("sessionId:nonempty-string")
    if not isinstance(usage, dict):
        invalid.append("usage:object")
    if (
        not isinstance(model_usage, dict)
        or not model_usage
        or not all(isinstance(value, dict) for value in model_usage.values())
    ):
        invalid.append("modelUsage:nonempty-object")
    if invalid:
        return _error(
            EXIT_INVALID_ENVELOPE,
            "outer envelope missing/invalid " + ", ".join(invalid),
            raw,
            source,
        )

    body, fence_exit, fence_error = _json_fence(text)
    if fence_exit != EXIT_OK:
        return _error(fence_exit, fence_error, raw, source)
    try:
        packet = json.loads(body)
    except ValueError as exc:
        return _error(
            EXIT_INVALID_INNER_JSON,
            "fenced body is not JSON: %s" % exc,
            raw,
            source,
        )
    if not isinstance(packet, dict):
        return _error(
            EXIT_WRONG_TYPE,
            "fenced JSON must be an object",
            raw,
            source,
        )
    packet_id = packet.get("packet_id")
    if not isinstance(packet_id, str) or not packet_id.strip():
        return _error(
            EXIT_MISSING_PACKET_ID,
            "fenced object requires packet_id:nonempty-string",
            raw,
            source,
        )

    models = sorted(str(name) for name in model_usage)
    outer = {
        name: envelope[name]
        for name in OPTIONAL_OUTER_FIELDS
        if name in envelope
    }
    digest = sha256_hex(raw)
    normalized = {
        "schema": SCHEMA,
        "status": "OK",
        "exit_code": EXIT_OK,
        "source_sha256": digest,
        "source": {
            "name": _source_name(source),
            "bytes": len(raw),
            "sha256": digest,
        },
        "sessionId": session_id,
        "model": models[0] if len(models) == 1 else None,
        "models": models,
        "usage": usage,
        "modelUsage": model_usage,
        "outer": outer,
        "packet_id": packet_id,
        "packet": packet,
        "fence_count": 1,
        "excluded_fields": ["text", "thought"],
    }
    return normalized, EXIT_OK


def _render(payload):
    return (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _read_source(source, stdin=None):
    if source == "-":
        stream = stdin or sys.stdin.buffer
        return stream.read(), None
    try:
        with open(source, "rb") as handle:
            return handle.read(), None
    except FileNotFoundError:
        return None, _error(
            EXIT_MISSING_FILE,
            "input file does not exist",
            source=source,
        )
    except OSError as exc:
        return None, _error(
            EXIT_FINDER_FAILED,
            "input file could not be read: %s" % exc,
            source=source,
        )


def _self_test():
    packet = {"packet_id": "synthetic-self-test", "value": 1}
    envelope = {
        "text": "result\n```json\n%s\n```\n" % json.dumps(packet),
        "thought": "```json\n{\"packet_id\":\"scratch\"}\n```",
        "sessionId": "synthetic-session",
        "usage": {"total_tokens": 1},
        "modelUsage": {"synthetic-model": {"modelCalls": 1}},
    }
    raw = json.dumps(envelope).encode("utf-8")
    normalized, code = evaluate_receipt(raw)
    assert code == EXIT_OK
    assert normalized["packet"] == packet
    assert "thought" not in normalized
    assert "text" not in normalized
    return {"schema": SCHEMA, "status": "OK", "self_test": True}


def main(argv=None, stdin=None, stdout=None):
    parser = argparse.ArgumentParser(
        description="Normalize one completed Grok Build JSON envelope"
    )
    parser.add_argument("source", nargs="?", help="receipt JSON path or - for stdin")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and emit normalized JSON (the default behavior)",
    )
    parser.add_argument("--output", help="also write normalized JSON to this path")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    out = stdout or sys.stdout.buffer

    if args.self_test:
        rendered = _render(_self_test())
        out.write(rendered)
        return EXIT_OK

    source = args.source
    if source is None:
        stream = stdin or sys.stdin.buffer
        if hasattr(stream, "isatty") and stream.isatty():
            parser.error("source is required when stdin is a terminal")
        source = "-"

    raw, read_error = _read_source(source, stdin=stdin)
    if read_error is not None:
        payload, code = read_error
    else:
        payload, code = evaluate_receipt(raw, source=source)
    rendered = _render(payload)

    if args.output:
        try:
            with open(args.output, "wb") as handle:
                handle.write(rendered)
        except OSError as exc:
            payload, code = _error(
                EXIT_WRITE_FAILURE,
                "normalized output could not be written: %s" % exc,
                raw,
                source,
            )
            rendered = _render(payload)

    out.write(rendered)
    return code


if __name__ == "__main__":
    sys.exit(main())
