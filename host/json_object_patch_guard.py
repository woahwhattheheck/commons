#!/usr/bin/env python3
"""Surgically replace one JSON object while proving all other bytes/values survive.

The tool never edits the input file. ``inspect`` produces immutable whole-file
and target-object hashes. ``patch`` requires those hashes, replaces exactly one
object selected by canonical JSON Pointer, reparses the result, verifies that
all semantics outside the target subtree are unchanged, and writes a separate
output file only after every proof passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

REPORT_VERSION = "json-object-patch-guard-report/v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PatchGuardError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise PatchGuardError("non-finite JSON number is not allowed: %s" % value)


@dataclass(frozen=True)
class ParsedJson:
    text: str
    value: Any
    spans: dict[str, tuple[int, int]]


class SpanParser:
    def __init__(self, text: str):
        self.text = text
        self.decoder = json.JSONDecoder(parse_float=Decimal, parse_constant=_reject_constant)
        self.spans: dict[str, tuple[int, int]] = {}

    def parse(self) -> ParsedJson:
        start = self._skip_ws(0)
        value, end = self._value(start, "")
        final = self._skip_ws(end)
        if final != len(self.text):
            raise PatchGuardError("trailing non-whitespace after root JSON value")
        return ParsedJson(self.text, value, dict(self.spans))

    def _skip_ws(self, index: int) -> int:
        text = self.text
        while index < len(text) and text[index] in " \t\r\n":
            index += 1
        return index

    def _value(self, index: int, pointer: str) -> tuple[Any, int]:
        index = self._skip_ws(index)
        if index >= len(self.text):
            raise PatchGuardError("unexpected end of JSON at %s" % (pointer or "/"))
        char = self.text[index]
        if char == "{":
            return self._object(index, pointer)
        if char == "[":
            return self._array(index, pointer)
        try:
            value, end = self.decoder.raw_decode(self.text, index)
        except json.JSONDecodeError as exc:
            raise PatchGuardError("invalid JSON at %s: %s" % (pointer or "/", exc)) from exc
        self.spans[pointer] = (index, end)
        return value, end

    def _object(self, start: int, pointer: str) -> tuple[dict[str, Any], int]:
        index = self._skip_ws(start + 1)
        out: dict[str, Any] = {}
        if index < len(self.text) and self.text[index] == "}":
            end = index + 1
            self.spans[pointer] = (start, end)
            return out, end
        while True:
            index = self._skip_ws(index)
            if index >= len(self.text) or self.text[index] != '"':
                raise PatchGuardError("object key must be a string at %s" % (pointer or "/"))
            try:
                key, key_end = self.decoder.raw_decode(self.text, index)
            except json.JSONDecodeError as exc:
                raise PatchGuardError("invalid object key at %s" % (pointer or "/")) from exc
            if not isinstance(key, str):
                raise PatchGuardError("object key must be a string at %s" % (pointer or "/"))
            if key in out:
                raise PatchGuardError("duplicate JSON key at %s: %s" % (pointer or "/", key))
            index = self._skip_ws(key_end)
            if index >= len(self.text) or self.text[index] != ":":
                raise PatchGuardError("missing ':' after key at %s" % (pointer or "/"))
            child_pointer = pointer + "/" + _escape_pointer_part(key)
            value, index = self._value(index + 1, child_pointer)
            out[key] = value
            index = self._skip_ws(index)
            if index >= len(self.text):
                raise PatchGuardError("unterminated object at %s" % (pointer or "/"))
            if self.text[index] == "}":
                end = index + 1
                self.spans[pointer] = (start, end)
                return out, end
            if self.text[index] != ",":
                raise PatchGuardError("expected ',' or '}' at %s" % (pointer or "/"))
            index += 1

    def _array(self, start: int, pointer: str) -> tuple[list[Any], int]:
        index = self._skip_ws(start + 1)
        out: list[Any] = []
        if index < len(self.text) and self.text[index] == "]":
            end = index + 1
            self.spans[pointer] = (start, end)
            return out, end
        item = 0
        while True:
            child_pointer = pointer + "/" + str(item)
            value, index = self._value(index, child_pointer)
            out.append(value)
            item += 1
            index = self._skip_ws(index)
            if index >= len(self.text):
                raise PatchGuardError("unterminated array at %s" % (pointer or "/"))
            if self.text[index] == "]":
                end = index + 1
                self.spans[pointer] = (start, end)
                return out, end
            if self.text[index] != ",":
                raise PatchGuardError("expected ',' or ']' at %s" % (pointer or "/"))
            index = self._skip_ws(index + 1)


def _escape_pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _decode_pointer_part(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        if value[index] != "~":
            out.append(value[index])
            index += 1
            continue
        if index + 1 >= len(value) or value[index + 1] not in {"0", "1"}:
            raise PatchGuardError("invalid JSON Pointer escape")
        out.append("~" if value[index + 1] == "0" else "/")
        index += 2
    return "".join(out)


def _value_at(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise PatchGuardError("pointer must be empty or start with '/'")
    node = value
    canonical_parts: list[str] = []
    for raw in pointer.split("/")[1:]:
        part = _decode_pointer_part(raw)
        canonical_parts.append(_escape_pointer_part(part))
        if isinstance(node, dict):
            if part not in node:
                raise PatchGuardError("pointer does not resolve: %s" % pointer)
            node = node[part]
        elif isinstance(node, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part):
                raise PatchGuardError("pointer has invalid array index: %s" % pointer)
            index = int(part)
            if index >= len(node):
                raise PatchGuardError("pointer does not resolve: %s" % pointer)
            node = node[index]
        else:
            raise PatchGuardError("pointer crosses a scalar: %s" % pointer)
    canonical = "/" + "/".join(canonical_parts)
    if canonical != pointer:
        raise PatchGuardError("pointer is not canonical: %s" % pointer)
    return node


def _read_utf8_json(path: Path) -> tuple[bytes, ParsedJson]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PatchGuardError("cannot read %s: %s" % (path, exc)) from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchGuardError("%s must be UTF-8" % path) from exc
    return raw, SpanParser(text).parse()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _target_evidence(raw: bytes, parsed: ParsedJson, pointer: str) -> dict[str, Any]:
    value = _value_at(parsed.value, pointer)
    if pointer not in parsed.spans:
        raise PatchGuardError("pointer span is unavailable: %s" % pointer)
    start, end = parsed.spans[pointer]
    prefix = parsed.text[:start].encode("utf-8")
    target = parsed.text[start:end].encode("utf-8")
    suffix = parsed.text[end:].encode("utf-8")
    if len(prefix) + len(target) + len(suffix) != len(raw):
        raise PatchGuardError("UTF-8 span accounting failed")
    return {
        "value": value,
        "start_char": start,
        "end_char": end,
        "start_byte": len(prefix),
        "end_byte": len(prefix) + len(target),
        "raw_sha256": _sha256(target),
        "prefix_sha256": _sha256(prefix),
        "suffix_sha256": _sha256(suffix),
        "prefix_bytes": len(prefix),
        "target_bytes": len(target),
        "suffix_bytes": len(suffix),
    }


def inspect_file(path: Path, pointer: str) -> dict[str, Any]:
    raw, parsed = _read_utf8_json(path)
    target = _target_evidence(raw, parsed, pointer)
    if not isinstance(target["value"], dict):
        raise PatchGuardError("target pointer must resolve to an object")
    target.pop("value")
    return {
        "schema_version": REPORT_VERSION,
        "mode": "inspect",
        "ok": True,
        "input": {"path": str(path), "bytes": len(raw), "sha256": _sha256(raw)},
        "target": {"pointer": pointer, **target},
    }


def _outside_equal(before: Any, after: Any, target: str, pointer: str = "") -> None:
    if pointer == target:
        return
    if type(before) is not type(after):
        raise PatchGuardError("semantic type changed outside target at %s" % (pointer or "/"))
    if isinstance(before, dict):
        if list(before) != list(after):
            raise PatchGuardError("object keys/order changed outside target at %s" % (pointer or "/"))
        for key in before:
            child = pointer + "/" + _escape_pointer_part(key)
            _outside_equal(before[key], after[key], target, child)
        return
    if isinstance(before, list):
        if len(before) != len(after):
            raise PatchGuardError("array length changed outside target at %s" % (pointer or "/"))
        for index, (left, right) in enumerate(zip(before, after)):
            child = pointer + "/" + str(index)
            _outside_equal(left, right, target, child)
        return
    if before != after:
        raise PatchGuardError("semantic value changed outside target at %s" % (pointer or "/"))


def _validate_hash(value: str, field: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise PatchGuardError("%s must be a lowercase SHA-256" % field)


def _replacement_text(parsed: ParsedJson, pointer_line_prefix: str) -> str:
    start, end = parsed.spans[""]
    core = parsed.text[start:end]
    lines = core.splitlines()
    if len(lines) <= 1:
        return core
    leading = re.match(r"[ \t]*", pointer_line_prefix)
    base = leading.group(0) if leading else ""
    return lines[0] + "".join("\n" + base + line for line in lines[1:])


def patch_file(
    input_path: Path,
    pointer: str,
    replacement_path: Path,
    output_path: Path,
    *,
    expect_input_sha256: str,
    expect_target_sha256: str,
) -> dict[str, Any]:
    _validate_hash(expect_input_sha256, "expect_input_sha256")
    _validate_hash(expect_target_sha256, "expect_target_sha256")
    if input_path.resolve(strict=False) == output_path.resolve(strict=False):
        raise PatchGuardError("output must be a separate file; input is never edited in place")
    if output_path.exists():
        raise PatchGuardError("output already exists: %s" % output_path)

    input_raw, before = _read_utf8_json(input_path)
    actual_input_hash = _sha256(input_raw)
    if actual_input_hash != expect_input_sha256:
        raise PatchGuardError(
            "input SHA-256 changed: expected %s, got %s" % (expect_input_sha256, actual_input_hash)
        )
    before_target = _target_evidence(input_raw, before, pointer)
    if not isinstance(before_target["value"], dict):
        raise PatchGuardError("target pointer must resolve to an object")
    if before_target["raw_sha256"] != expect_target_sha256:
        raise PatchGuardError(
            "target SHA-256 changed: expected %s, got %s"
            % (expect_target_sha256, before_target["raw_sha256"])
        )

    _, replacement = _read_utf8_json(replacement_path)
    if not isinstance(replacement.value, dict):
        raise PatchGuardError("replacement root must be an object")

    start, end = before.spans[pointer]
    line_start = before.text.rfind("\n", 0, start) + 1
    line_prefix = before.text[line_start:start]
    insert = _replacement_text(replacement, line_prefix)
    candidate_text = before.text[:start] + insert + before.text[end:]
    candidate_raw = candidate_text.encode("utf-8")
    after = SpanParser(candidate_text).parse()
    after_target = _target_evidence(candidate_raw, after, pointer)
    if after_target["value"] != replacement.value:
        raise PatchGuardError("replacement value did not round-trip at target pointer")
    _outside_equal(before.value, after.value, pointer)

    before_prefix = before.text[:start].encode("utf-8")
    before_suffix = before.text[end:].encode("utf-8")
    after_start, after_end = after.spans[pointer]
    after_prefix = after.text[:after_start].encode("utf-8")
    after_suffix = after.text[after_end:].encode("utf-8")
    if before_prefix != after_prefix:
        raise PatchGuardError("prefix bytes changed outside target")
    if before_suffix != after_suffix:
        raise PatchGuardError("suffix bytes changed outside target")

    output_created = False
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        output_created = True
        with os.fdopen(fd, "wb") as handle:
            handle.write(candidate_raw)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        if output_created:
            try:
                output_path.unlink()
            except OSError:
                pass
        raise PatchGuardError("cannot publish output without overwrite: %s" % exc) from exc

    return {
        "schema_version": REPORT_VERSION,
        "mode": "patch",
        "ok": True,
        "input": {
            "path": str(input_path),
            "bytes": len(input_raw),
            "sha256": actual_input_hash,
        },
        "target": {
            "pointer": pointer,
            "before_raw_sha256": before_target["raw_sha256"],
            "after_raw_sha256": after_target["raw_sha256"],
        },
        "proof": {
            "prefix_bytes_unchanged": True,
            "suffix_bytes_unchanged": True,
            "outside_target_semantics_unchanged": True,
            "replacement_round_trip": True,
        },
        "output": {
            "path": str(output_path),
            "bytes": len(candidate_raw),
            "sha256": _sha256(candidate_raw),
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect_parser = sub.add_parser("inspect", help="hash one input and target object")
    inspect_parser.add_argument("--input", required=True)
    inspect_parser.add_argument("--pointer", required=True)

    patch_parser = sub.add_parser("patch", help="write a separately verified patched JSON file")
    patch_parser.add_argument("--input", required=True)
    patch_parser.add_argument("--pointer", required=True)
    patch_parser.add_argument("--replacement", required=True)
    patch_parser.add_argument("--output", required=True)
    patch_parser.add_argument("--expect-input-sha256", required=True)
    patch_parser.add_argument("--expect-target-sha256", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            report = inspect_file(Path(args.input), args.pointer)
        else:
            report = patch_file(
                Path(args.input),
                args.pointer,
                Path(args.replacement),
                Path(args.output),
                expect_input_sha256=args.expect_input_sha256,
                expect_target_sha256=args.expect_target_sha256,
            )
    except PatchGuardError as exc:
        print(json.dumps({"schema_version": REPORT_VERSION, "ok": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
