"""Production host authority for pursuit-portfolio current-use operations.

The trusted key location is not selected by candidate input or CLI arguments.
Tests may patch ``HOST_KEY_PATH``; production callers do not get a key-path
parameter on the current-use API.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .current import (
    AuthorizedPortfolio,
    compile_authorized_current,
    load_authority_key,
    verify_authorized_current,
)

HOST_KEY_PATH = Path.home() / ".config" / "commons" / "pursuit-portfolio" / "authority-key.json"


def compile_current(
    source: Mapping[str, Any], authority: Mapping[str, Any]
) -> AuthorizedPortfolio:
    """Compile current-use evidence under the fixed retained host authority."""
    key = load_authority_key(HOST_KEY_PATH)
    return compile_authorized_current(source, authority, key)


def verify_current(
    result_raw: bytes,
    markdown_raw: bytes,
    receipt_raw: bytes,
    authority_raw: bytes,
    current_receipt_raw: bytes,
) -> dict[str, Any]:
    """Fresh-current verify under the fixed retained host authority."""
    key = load_authority_key(HOST_KEY_PATH)
    return verify_authorized_current(
        result_raw,
        markdown_raw,
        receipt_raw,
        authority_raw,
        current_receipt_raw,
        key,
    )
