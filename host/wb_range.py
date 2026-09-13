#!/usr/bin/env python3
"""WB-RANGE public entry point with strict HTTP Range transport validation.

The implementation core is kept byte-for-byte in ``_wb_range_core``; this
facade hardens the transport boundary and rebinds the core's RangeReader so
all existing index/slice/verify/metric/serve call paths share the same strict
contract.
"""

from __future__ import annotations

import re as _re
from pathlib import Path as _Path
from urllib.parse import urlsplit as _urlsplit

try:  # package import (tests / ``python -m``)
    from . import _wb_range_core as _core
except ImportError:  # direct ``python host/wb_range.py`` execution
    import _wb_range_core as _core


# Re-export the existing WB-RANGE API before replacing RangeReader. Functions
# defined in the core resolve ``RangeReader`` from the core module at call time;
# rebinding ``_core.RangeReader`` below therefore hardens every existing path.
for _name, _value in vars(_core).items():
    if not _name.startswith("__") and _name != "RangeReader":
        globals()[_name] = _value


WbRangeError = _core.WbRangeError


def _validate_transport_url(url: str) -> None:
    """Allow HTTPS everywhere and plain HTTP only on exact loopback hosts."""
    try:
        parts = _urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError as exc:
        raise WbRangeError("malformed artifact URL") from exc
    scheme = parts.scheme.lower()
    if scheme == "https" and host:
        return
    if scheme == "http" and host in {"localhost", "127.0.0.1", "::1"}:
        return
    raise WbRangeError(
        "url must use https; plain HTTP is only permitted for localhost rehearsal"
    )


class _StrictRedirectHandler(_core.urllib.request.HTTPRedirectHandler):
    """Reject transport downgrades before urllib follows a redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        source_scheme = _urlsplit(req.full_url).scheme.lower()
        target_scheme = _urlsplit(newurl).scheme.lower()
        if source_scheme == "https" and target_scheme != "https":
            raise WbRangeError(
                "HTTPS downgrade rejected before redirect follow: %s" % newurl
            )
        _validate_transport_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RangeReader(_core.RangeReader):
    """HTTP Range reader that fails closed on ambiguous transport responses."""

    def __init__(self, url: str, cache_dir: _Path, *,
                 limit: int = _core.DEFAULT_LIMIT_BYTES,
                 use_cache: bool = True):
        _validate_transport_url(url)
        self.url = url
        self.cache_dir = _Path(cache_dir)
        self.limit = int(limit)
        self.use_cache = use_cache
        self.chunks_dir = self.cache_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.cache_dir / "cache_manifest.json"
        self.manifest = self._load_manifest()

    @staticmethod
    def _open_response(request, timeout: int):
        opener = _core.urllib.request.build_opener(_StrictRedirectHandler())
        return opener.open(request, timeout=timeout)

    def _validate_range_response(self, response, offset: int, length: int) -> int:
        status = getattr(response, "status", None)
        if status is None:
            getcode = getattr(response, "getcode", None)
            status = getcode() if callable(getcode) else None
        if status != 206:
            raise WbRangeError(
                "unexpected HTTP status %s; byte ranges require 206" % status
            )

        geturl = getattr(response, "geturl", None)
        final_url = geturl() if callable(geturl) else self.url
        source_scheme = _urlsplit(self.url).scheme.lower()
        final_scheme = _urlsplit(final_url).scheme.lower()
        if source_scheme == "https" and final_scheme != "https":
            # Defense in depth for custom handlers/test doubles. The normal
            # urllib path rejects this before a downgraded request is followed.
            raise WbRangeError(
                "HTTPS downgrade rejected: final response URL is %s" % final_url
            )
        _validate_transport_url(final_url)

        encoding = (response.headers.get("Content-Encoding", "") or "").strip()
        if encoding and encoding.lower() != "identity":
            raise WbRangeError(
                "unexpected Content-Encoding %r; range bytes must be identity"
                % encoding
            )

        content_range = (response.headers.get("Content-Range", "") or "").strip()
        match = _re.fullmatch(
            r"bytes[ \t]+(\d+)-(\d+)/(\d+)", content_range,
            flags=_re.IGNORECASE,
        )
        expected_end = offset + length - 1
        if not match:
            raise WbRangeError(
                "invalid Content-Range %r for requested bytes %d-%d"
                % (content_range, offset, expected_end)
            )
        actual_start, actual_end, total = (int(group) for group in match.groups())
        if actual_start != offset or actual_end != expected_end:
            raise WbRangeError(
                "Content-Range interval %d-%d does not match requested bytes %d-%d"
                % (actual_start, actual_end, offset, expected_end)
            )
        if total <= actual_end:
            raise WbRangeError(
                "Content-Range total %d is incompatible with interval %d-%d"
                % (total, actual_start, actual_end)
            )
        return total

    @staticmethod
    def _require_exact_body(data: bytes, length: int) -> None:
        if len(data) != length:
            qualifier = "short" if len(data) < length else "overlong"
            raise WbRangeError(
                "%s range body: wanted %d bytes, got %d"
                % (qualifier, length, len(data))
            )

    def _fetch(self, offset: int, length: int) -> bytes:
        request = _core.urllib.request.Request(
            self.url,
            headers={
                "Range": "bytes=%d-%d" % (offset, offset + length - 1),
                "User-Agent": _core.USER_AGENT,
                "Accept-Encoding": "identity",
            },
        )
        try:
            with self._open_response(request, timeout=120) as response:
                self._validate_range_response(response, offset, length)
                data = response.read(length + 1)
        except _core.urllib.error.HTTPError as exc:
            raise WbRangeError(
                "HTTP %s on range %d+%d" % (exc.code, offset, length)
            ) from exc
        except _core.urllib.error.URLError as exc:
            raise WbRangeError("fetch failed: %s" % exc.reason) from exc
        self._require_exact_body(data, length)
        return data

    def _fetch_raw(self, offset: int, length: int) -> int:
        request = _core.urllib.request.Request(
            self.url,
            headers={
                "Range": "bytes=%d-%d" % (offset, offset + length - 1),
                "User-Agent": _core.USER_AGENT,
                "Accept-Encoding": "identity",
            },
        )
        try:
            with self._open_response(request, timeout=60) as response:
                total = self._validate_range_response(response, offset, length)
                data = response.read(length + 1)
        except _core.urllib.error.HTTPError as exc:
            raise WbRangeError(
                "HTTP %s on range %d+%d" % (exc.code, offset, length)
            ) from exc
        except _core.urllib.error.URLError as exc:
            raise WbRangeError("fetch failed: %s" % exc.reason) from exc
        self._require_exact_body(data, length)
        return total


# Critical: all functions/classes defined in the preserved implementation core
# now resolve this strict reader when they instantiate RangeReader.
_core.RangeReader = RangeReader


if __name__ == "__main__":
    try:
        raise SystemExit(_core.main())
    except WbRangeError as exc:
        print("INVALID: %s" % exc, file=_core.sys.stderr)
        raise SystemExit(2)
