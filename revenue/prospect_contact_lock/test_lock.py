"""Run the preserved CAS hostile corpus through the hardened core class.

The predecessor test file remains byte-preserved in ``_legacy_test_lock.py``.
This shim supplies only deterministic authority-marker truth and the deliberately
private test transport constructor; production construction remains token-only.
"""
from __future__ import annotations

import base64
import hashlib
import json
from urllib.parse import unquote, urlsplit

from . import _core
from . import _legacy_test_lock as _legacy
from .lock import (
    AUTHORITY_MARKER_PATH,
    EXPECTED_AUTHORITY_MARKER,
    ProspectContactLock,
)


class _LegacyModuleProxy:
    """Expose core API while routing legacy two-arg construction to test-only capability."""

    def __getattr__(self, name):
        return getattr(_core, name)

    @staticmethod
    def ProspectContactLock(token, transport):
        return ProspectContactLock._for_tests(token, transport)


class AuthorizedFakeTransport(_legacy.FakeTransport):
    """Legacy fake transport with a valid canonical authority marker by default."""

    def request(self, method, url, headers, body):
        parsed = urlsplit(url)
        path = (
            unquote(parsed.path.split("/contents/", 1)[1])
            if "/contents/" in parsed.path
            else ""
        )
        if method == "GET" and path == AUTHORITY_MARKER_PATH:
            self.urls.append(url)
            self.auth_headers.append(headers.get("Authorization"))
            raw = (
                json.dumps(
                    EXPECTED_AUTHORITY_MARKER,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
                + b"\n"
            )
            envelope = {
                "sha": hashlib.sha1(raw).hexdigest(),
                "encoding": "base64",
                "content": base64.b64encode(raw).decode(),
            }
            return _core.Response(200, self._headers(), json.dumps(envelope).encode())
        return super().request(method, url, headers, body)


# The preserved module resolves these globals at test execution time.
_legacy.mod = _LegacyModuleProxy()
_legacy.FakeTransport = AuthorizedFakeTransport

DATE = _legacy.DATE
FakeTransport = AuthorizedFakeTransport
ProspectContactLockTests = _legacy.ProspectContactLockTests

__all__ = ["DATE", "FakeTransport", "ProspectContactLockTests"]
