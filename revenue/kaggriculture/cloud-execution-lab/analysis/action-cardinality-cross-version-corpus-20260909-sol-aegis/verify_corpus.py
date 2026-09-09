#!/usr/bin/env python3
"""Verify SOL-AEGIS' compact cross-version TITAN cardinality corpus.

The manifest is an integrity-bound summary. With ``--replay-dir`` this tool
also hashes, decodes, and independently replays the exact gzip evidence,
checking action row k against observation row k-1 for every seat.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import gzip
import hashlib
import hmac
import io
import json
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence

SCHEMA = "titan.action-cardinality-cross-version-corpus.v1"
INTERPRETATION = (
    "This corpus proves cross-version unreachable submitted hand rows in the "
    "identified replay bytes. It does not prove score delta, causality, engine "
    "equivalence, candidate strength, or release readiness."
)
MAX_TRANSPORT_BYTES = 64 << 20
MAX_JSON_BYTES = 128 << 20
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SLACK_FILE_RE = re.compile(r"^F[A-Z0-9]+$")
TOP_KEYS = {
    "schema",
    "source_label",
    "automatic_promotion",
    "sources",
    "summary",
    "interpretation",
    "corpus_sha256",
}
SOURCE_KEYS = {
    "episode",
    "filename",
    "slack_file_id",
    "transport_bytes",
    "transport_sha256",
    "json_bytes",
    "json_sha256",
    "decisions_audited",
    "seat",
    "blocks",
}
BLOCK_KEYS = {
    "start_step",
    "end_step",
    "observable_hands",
    "submitted_hand_rows",
    "unreachable_opcodes",
}
SUMMARY_KEYS = {
    "source_files",
    "decisions_audited",
    "block_count",
    "unreachable_rows",
    "seat",
    "opcode_counts",
    "day5_sequence_sha256",
}


class CorpusError(ValueError):
    pass


def _reject_constant(value: str) -> None:
    raise CorpusError(f"non-finite JSON constant is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CorpusError(f"duplicate JSON key is forbidden: {key!r}")
        result[key] = value
    return result


def strict_loads(data: bytes) -> Any:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CorpusError(f"not strict UTF-8: {exc}") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except CorpusError:
        raise
    except json.JSONDecodeError as exc:
        raise CorpusError(f"invalid JSON: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CorpusError(f"not canonical JSON: {exc}") from exc


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_uint(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _check_hash(value: Any, name: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise CorpusError(f"{name} is not a lowercase SHA-256")


def _expanded_expected(source: Mapping[str, Any]) -> list[dict[str, Any]]:
    expected: list[dict[str, Any]] = []
    for block in source["blocks"]:
        excess = block["submitted_hand_rows"] - block["observable_hands"]
        opcodes = block["unreachable_opcodes"]
        cursor = 0
        for step in range(block["start_step"], block["end_step"] + 1):
            expected.append(
                {
                    "seat": source["seat"],
                    "step": step,
                    "observable_hands": block["observable_hands"],
                    "submitted_hand_rows": block["submitted_hand_rows"],
                    "unreachable_opcodes": opcodes[cursor : cursor + excess],
                }
            )
            cursor += excess
    return expected


def verify_manifest(manifest: Any) -> tuple[bool, str]:
    try:
        _verify_manifest(manifest)
    except CorpusError as exc:
        return False, str(exc)
    return True, "verified"


def _verify_manifest(manifest: Any) -> None:
    if not isinstance(manifest, Mapping) or set(manifest) != TOP_KEYS:
        raise CorpusError("top-level field set mismatch")
    if manifest["schema"] != SCHEMA:
        raise CorpusError("schema mismatch")
    if manifest["automatic_promotion"] is not False:
        raise CorpusError("automatic_promotion must remain false")
    if manifest["interpretation"] != INTERPRETATION:
        raise CorpusError("interpretation contract mismatch")
    if not isinstance(manifest["source_label"], str) or not manifest["source_label"]:
        raise CorpusError("source_label is missing")

    digest = manifest["corpus_sha256"]
    _check_hash(digest, "corpus_sha256")
    payload = copy.deepcopy(dict(manifest))
    payload.pop("corpus_sha256")
    actual_digest = sha256(canonical_bytes(payload))
    if not hmac.compare_digest(digest, actual_digest):
        raise CorpusError("corpus_sha256 does not bind the payload")

    sources = manifest["sources"]
    if not isinstance(sources, list) or not sources:
        raise CorpusError("sources must be a non-empty list")
    filenames: list[str] = []
    seats: set[int] = set()
    total_decisions = 0
    total_blocks = 0
    total_rows = 0
    opcode_counts: Counter[str] = Counter()
    day5_sequences: list[list[str]] = []

    for source in sources:
        if not isinstance(source, Mapping) or set(source) != SOURCE_KEYS:
            raise CorpusError("source field set mismatch")
        episode = source["episode"]
        filename = source["filename"]
        if not is_uint(episode) or not isinstance(filename, str):
            raise CorpusError("source episode/filename is malformed")
        if filename != f"{episode}.json.gz":
            raise CorpusError(f"filename does not bind episode {episode}")
        if not isinstance(source["slack_file_id"], str) or not SLACK_FILE_RE.fullmatch(source["slack_file_id"]):
            raise CorpusError(f"{filename}: malformed Slack file ID")
        for key in ("transport_bytes", "json_bytes", "decisions_audited", "seat"):
            if not is_uint(source[key]) or source[key] == 0 and key != "seat":
                raise CorpusError(f"{filename}: invalid {key}")
        _check_hash(source["transport_sha256"], f"{filename}.transport_sha256")
        _check_hash(source["json_sha256"], f"{filename}.json_sha256")
        filenames.append(filename)
        seats.add(source["seat"])
        total_decisions += source["decisions_audited"]

        blocks = source["blocks"]
        if not isinstance(blocks, list) or not blocks:
            raise CorpusError(f"{filename}: blocks must be non-empty")
        previous_end = -1
        for block in blocks:
            if not isinstance(block, Mapping) or set(block) != BLOCK_KEYS:
                raise CorpusError(f"{filename}: block field set mismatch")
            for key in ("start_step", "end_step", "observable_hands", "submitted_hand_rows"):
                if not is_uint(block[key]):
                    raise CorpusError(f"{filename}: invalid block {key}")
            start = block["start_step"]
            end = block["end_step"]
            observable = block["observable_hands"]
            submitted = block["submitted_hand_rows"]
            if start > end or start <= previous_end:
                raise CorpusError(f"{filename}: blocks overlap or are not sorted")
            if submitted <= observable:
                raise CorpusError(f"{filename}: block is not over-cardinality")
            opcodes = block["unreachable_opcodes"]
            expected_rows = (end - start + 1) * (submitted - observable)
            if (
                not isinstance(opcodes, list)
                or len(opcodes) != expected_rows
                or any(not isinstance(code, str) or not code for code in opcodes)
            ):
                raise CorpusError(f"{filename}: block opcode cardinality mismatch")
            previous_end = end
            total_blocks += 1
            total_rows += len(opcodes)
            opcode_counts.update(opcodes)
            if start == 123 and end == 144:
                day5_sequences.append(opcodes)

    if filenames != sorted(filenames) or len(filenames) != len(set(filenames)):
        raise CorpusError("sources are not unique and filename-sorted")
    if len(seats) != 1:
        raise CorpusError("corpus does not identify one affected seat")
    if len(day5_sequences) != len(sources) or any(seq != day5_sequences[0] for seq in day5_sequences[1:]):
        raise CorpusError("day-5 sequence is not identical across every source")

    summary = manifest["summary"]
    if not isinstance(summary, Mapping) or set(summary) != SUMMARY_KEYS:
        raise CorpusError("summary field set mismatch")
    for key in ("source_files", "decisions_audited", "block_count", "unreachable_rows", "seat"):
        if not is_uint(summary[key]):
            raise CorpusError(f"summary.{key} is not a uint")
    _check_hash(summary["day5_sequence_sha256"], "summary.day5_sequence_sha256")
    expected_summary = {
        "source_files": len(sources),
        "decisions_audited": total_decisions,
        "block_count": total_blocks,
        "unreachable_rows": total_rows,
        "seat": next(iter(seats)),
        "opcode_counts": dict(sorted(opcode_counts.items())),
        "day5_sequence_sha256": sha256(canonical_bytes(day5_sequences[0])),
    }
    if dict(summary) != expected_summary:
        raise CorpusError("summary does not re-derive from sources and blocks")


def _bounded_decode_gzip(raw: bytes, source: str) -> bytes:
    if len(raw) > MAX_TRANSPORT_BYTES:
        raise CorpusError(f"{source}: transport exceeds bound")
    output = bytearray()
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
            while True:
                chunk = stream.read(min(1 << 20, MAX_JSON_BYTES + 1 - len(output)))
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > MAX_JSON_BYTES:
                    raise CorpusError(f"{source}: decoded JSON exceeds bound")
    except CorpusError:
        raise
    except (EOFError, OSError) as exc:
        raise CorpusError(f"{source}: invalid gzip: {exc}") from exc
    return bytes(output)


def derive_replay(document: Any, source: str) -> tuple[int, list[dict[str, Any]]]:
    if not isinstance(document, Mapping) or set(document).isdisjoint({"steps"}):
        raise CorpusError(f"{source}: missing steps")
    steps = document["steps"]
    if not isinstance(steps, list) or len(steps) < 2:
        raise CorpusError(f"{source}: steps must contain at least two frames")
    if not isinstance(steps[0], list) or not steps[0]:
        raise CorpusError(f"{source}: invalid first frame")
    seat_count = len(steps[0])
    for index, frame in enumerate(steps):
        if not isinstance(frame, list) or len(frame) != seat_count:
            raise CorpusError(f"{source}: frame {index} seat cardinality mismatch")
        if any(not isinstance(record, Mapping) for record in frame):
            raise CorpusError(f"{source}: frame {index} contains non-object seat")

    findings: list[dict[str, Any]] = []
    decisions = 0
    for step in range(1, len(steps)):
        before = steps[step - 1]
        after = steps[step]
        for seat in range(seat_count):
            observation = before[seat].get("observation")
            action = after[seat].get("action")
            if not isinstance(observation, Mapping) or not isinstance(action, Mapping):
                raise CorpusError(f"{source}: step {step} seat {seat} lacks decision evidence")
            player = observation.get("player")
            farms = observation.get("farms")
            hands = action.get("hands", [])
            if not is_uint(player) or player != seat:
                raise CorpusError(f"{source}: step {step} seat/player mismatch")
            if not isinstance(farms, list) or player >= len(farms):
                raise CorpusError(f"{source}: step {step} cannot resolve farm")
            farm = farms[player]
            if not isinstance(farm, Mapping) or not isinstance(farm.get("hands"), list):
                raise CorpusError(f"{source}: step {step} lacks observed hands")
            if not isinstance(hands, list):
                raise CorpusError(f"{source}: step {step} action hands is not a list")
            for row in hands:
                if not isinstance(row, list) or not row or not isinstance(row[0], str) or not row[0]:
                    raise CorpusError(f"{source}: step {step} has malformed hand row")
            decisions += 1
            observable = len(farm["hands"])
            submitted = len(hands)
            if submitted > observable:
                findings.append(
                    {
                        "seat": seat,
                        "step": step,
                        "observable_hands": observable,
                        "submitted_hand_rows": submitted,
                        "unreachable_opcodes": [row[0] for row in hands[observable:]],
                    }
                )
    return decisions, findings


def verify_replay_files(manifest: Mapping[str, Any], replay_dir: Path) -> None:
    for source in manifest["sources"]:
        path = replay_dir / source["filename"]
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise CorpusError(f"{source['filename']}: cannot read replay: {exc}") from exc
        if len(raw) != source["transport_bytes"] or sha256(raw) != source["transport_sha256"]:
            raise CorpusError(f"{source['filename']}: transport identity mismatch")
        decoded = _bounded_decode_gzip(raw, source["filename"])
        if len(decoded) != source["json_bytes"] or sha256(decoded) != source["json_sha256"]:
            raise CorpusError(f"{source['filename']}: decoded JSON identity mismatch")
        document = strict_loads(decoded)
        decisions, actual = derive_replay(document, source["filename"])
        if decisions != source["decisions_audited"]:
            raise CorpusError(f"{source['filename']}: decision count mismatch")
        expected = _expanded_expected(source)
        if actual != expected:
            raise CorpusError(f"{source['filename']}: replay findings differ from manifest")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("CORPUS.json"))
    parser.add_argument("--replay-dir", type=Path, help="also reproduce findings from raw gzip replays")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = strict_loads(args.manifest.read_bytes())
        _verify_manifest(manifest)
        if args.replay_dir is not None:
            verify_replay_files(manifest, args.replay_dir)
    except (OSError, CorpusError) as exc:
        print(f"HOLD {exc}", file=sys.stderr)
        return 1
    summary = manifest["summary"]
    mode = "manifest+replays" if args.replay_dir is not None else "manifest"
    print(
        "PASS "
        f"mode={mode} sources={summary['source_files']} "
        f"decisions={summary['decisions_audited']} "
        f"unreachable_rows={summary['unreachable_rows']} "
        f"corpus_sha256={manifest['corpus_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
