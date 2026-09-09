#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Self-verifying compressed source capsule; see README.md for inspection."""
from __future__ import annotations

import base64 as _base64
import hashlib as _hashlib
from pathlib import Path as _Path
import zlib as _zlib

_EXPECTED_PARTS = 2
_EXPECTED_SHA256 = "9ffc3ea5f8c208227fa804eced4b837644700dad74fcf0c4bec05ab0c8fe0641"
_prefix = _Path(__file__).name + ".zlib.b64."
_parts = sorted(_Path(__file__).parent.glob(_prefix + "*"))
if len(_parts) != _EXPECTED_PARTS or [p.name for p in _parts] != [f"{_prefix}{i:02d}" for i in range(_EXPECTED_PARTS)]:
    raise RuntimeError(f"{__file__}: source capsule part-set drift")
try:
    _payload = "".join(p.read_text(encoding="ascii") for p in _parts).encode("ascii")
    _source = _zlib.decompress(_base64.b64decode(_payload, validate=True))
except (OSError, UnicodeError, ValueError, _zlib.error) as _exc:
    raise RuntimeError(f"{__file__}: invalid source capsule") from _exc
if _hashlib.sha256(_source).hexdigest() != _EXPECTED_SHA256:
    raise RuntimeError(f"{__file__}: source capsule digest drift")
exec(compile(_source, str(_Path(__file__).with_suffix(".source.py")), "exec"), globals(), globals())
