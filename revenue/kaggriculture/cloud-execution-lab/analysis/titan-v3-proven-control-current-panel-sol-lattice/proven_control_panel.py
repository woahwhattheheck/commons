# SPDX-License-Identifier: Apache-2.0
"""Transparent loader for the reviewable compressed implementation chunks."""
from __future__ import annotations

import base64
from pathlib import Path
import zlib

_HERE = Path(__file__).resolve().parent
_PARTS = sorted(_HERE.glob("proven_control_panel.py.zlib.b64.*"))
if not _PARTS:
    raise RuntimeError("matched-panel implementation chunks are missing")
_NAMES = [path.name for path in _PARTS]
_EXPECTED = [f"proven_control_panel.py.zlib.b64.{index:02d}" for index in range(len(_PARTS))]
if _NAMES != _EXPECTED:
    raise RuntimeError(f"matched-panel implementation chunk sequence changed: {_NAMES}")
try:
    _ENCODED = "".join("".join(path.read_text(encoding="ascii").split()) for path in _PARTS)
    _SOURCE = zlib.decompress(base64.b64decode(_ENCODED, validate=True))
except (OSError, UnicodeError, ValueError, zlib.error) as exc:
    raise RuntimeError("matched-panel implementation payload is invalid") from exc
exec(compile(_SOURCE, str(_HERE / "proven_control_panel.impl.py"), "exec"), globals(), globals())
