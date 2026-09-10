#!/usr/bin/env python3
"""Verified loader for the reviewable split source of the exact market oracle."""
from pathlib import Path as _LoaderPath
import hashlib as _loader_hashlib

_SOURCE_PARTS = (
    "official_market_transition_oracle.source.00.pyinc",
    "official_market_transition_oracle.source.01.pyinc",
    "official_market_transition_oracle.source.02.pyinc",
    "official_market_transition_oracle.source.03.pyinc",
)
_EXPECTED_SOURCE_SHA256 = "02cbfa4ea61dbdc908e5f345d3570d520eb3d9ca976fa3441c4a8883fa09b8dd"
_loader_root = _LoaderPath(__file__).resolve().parent
_loader_payload = b"".join((_loader_root / name).read_bytes() for name in _SOURCE_PARTS)
_loader_actual = _loader_hashlib.sha256(_loader_payload).hexdigest()
if _loader_actual != _EXPECTED_SOURCE_SHA256:
    raise RuntimeError(
        "official market-transition oracle source drift: "
        f"{_loader_actual} != {_EXPECTED_SOURCE_SHA256}"
    )
exec(compile(_loader_payload.decode("utf-8"), __file__, "exec"), globals(), globals())
