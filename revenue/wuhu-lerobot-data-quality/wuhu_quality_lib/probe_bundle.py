"""Internal module for the LeRobot v2.1 quality inspector."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import html
import json
import math
import os
import shutil
import statistics
import string
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from . import probe as _previous
from .probe import *

def probe_bundle_rows(context: DatasetContext, probe: ProbeResult) -> list[dict[str, Any]]:
    """Serialize normalized probe evidence for deterministic replay.

    A captured bundle remains bound to the sampled dataset fingerprint. A
    capability that was not complete is encoded as ``partial`` so replay never
    upgrades missing evidence into a clean modality.
    """
    capability_states = {
        name: ("complete" if capability.state == "complete" else "partial")
        for name, capability in sorted(probe.capabilities.items())
    }
    rows: list[dict[str, Any]] = [
        {
            "kind": "manifest",
            "schema_version": PROBE_SCHEMA,
            "dataset_fingerprint": context.fingerprint,
            "capabilities": capability_states,
            "capability_details": {
                name: capability.to_dict() for name, capability in sorted(probe.capabilities.items())
            },
            "producer": f"wuhu-quality/{TOOL_VERSION}",
        }
    ]
    for episode_index in sorted(probe.frames):
        for row in probe.frames[episode_index]:
            normalized = dict(row)
            normalized["kind"] = "frame"
            normalized["episode_index"] = episode_index
            rows.append(canonicalize(normalized))
    for key in sorted(probe.videos):
        video = probe.videos[key]
        normalized = video.to_dict()
        normalized["kind"] = "video"
        rows.append(canonicalize(normalized))
    # Validate JSON compatibility now, before a caller opens any output file.
    for row in rows:
        try:
            json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise QualityError(f"probe record is not JSON-compatible: {exc}") from exc
    return rows


def write_probe_bundle(dataset_root: Path, out_path: Path, context: DatasetContext, probe: ProbeResult) -> Path:
    parent = prepare_output_dir(dataset_root, out_path.expanduser().absolute().parent)
    destination = parent / out_path.name
    if destination.exists() and destination.is_dir():
        raise QualityError(f"probe output is a directory: {destination}")
    content = b"".join(canonical_json_bytes(row) for row in probe_bundle_rows(context, probe))
    _atomic_write(destination, content)
    return destination

__all__ = [
    'TOOL_VERSION',
    'REPORT_SCHEMA',
    'PROBE_SCHEMA',
    'EXPECTED_CODEBASE_VERSION',
    'REQUIRED_METADATA',
    'REQUIRED_FRAME_COLUMNS',
    'SEVERITY_ORDER',
    'SEVERITY_PENALTY',
    'DIMENSIONS',
    'CAPABILITY_STATES',
    'NONFINITE_TOKENS',
    'QualityError',
    'DuplicateKeyError',
    'Config',
    'Issue',
    '_Span',
    'IssueSink',
    'Capability',
    'EpisodeMeta',
    'DatasetContext',
    'FrameSummary',
    'VideoSummary',
    'ProbeResult',
    '_ObjectPairs',
    '_strict_object',
    '_reject_constant',
    'load_json_strict',
    'load_jsonl_strict',
    'canonicalize',
    'canonical_json_bytes',
    '_is_int',
    '_finite_number',
    '_ensure_positive_int',
    '_ensure_nonnegative_int',
    '_relative_posix',
    'safe_dataset_path',
    'render_template',
    '_optional_nonnegative_int',
    '_optional_finite',
    '_optional_ratio',
    '_output_inside_dataset',
    'prepare_output_dir',
    '_atomic_write',
    '_add_metadata_failure',
    'load_context',
    '_sampled_file_digest',
    'dataset_fingerprint',
    '_probe_manifest',
    'load_probe',
    '_import_pyarrow',
    'probe_parquet',
    '_parse_fraction',
    '_run_readonly',
    '_probe_one_video',
    '_optional_stream_float',
    '_optional_stream_int',
    '_sample_video_luma',
    'probe_videos',
    'auto_probe',
    'probe_bundle_rows',
    'write_probe_bundle'
]
