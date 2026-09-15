"""Subprocess-backed production authority API.

The public compile/verify functions intentionally do not consume the production
key, floor, or verifier clock in this Python process. They serialize bounded
candidate bytes to a fresh isolated child. Paths/time inside the caller process
therefore are not authority capabilities.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from .authority_protocol import (
    MAX_WORKER_RESPONSE_BYTES,
    PRODUCTION_HOST_SEAL_SCHEMA,
    WORKER_REQUEST_SCHEMA,
    WORKER_RESPONSE_SCHEMA,
)
from .core import CompiledPortfolio, PortfolioError, load_json_bytes
from .current import MAX_AUTHORITY_BYTES, AuthorizedPortfolio, _canonical
from .host import HostAuthorizedPortfolio


def _build_api():
    worker_path = Path(__file__).resolve().with_name("authority_worker.py")
    executable = str(Path(sys.executable).resolve())
    run_process = subprocess.run
    encode = base64.b64encode
    decode = base64.b64decode

    def run_worker(operation: str, payload: dict[str, str]) -> dict[str, Any]:
        request = {
            "schema": WORKER_REQUEST_SCHEMA,
            "operation": operation,
            "payload": payload,
        }
        raw = (
            json.dumps(
                request,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        try:
            completed = run_process(
                [executable, "-I", "-S", str(worker_path)],
                input=raw,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={},
                check=False,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PortfolioError("isolated authority worker unavailable") from exc
        if len(completed.stdout) > MAX_WORKER_RESPONSE_BYTES:
            raise PortfolioError("isolated authority worker response exceeds byte bound")
        try:
            response = json.loads(completed.stdout.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PortfolioError("isolated authority worker returned invalid response") from exc
        if type(response) is not dict or response.get("schema") != WORKER_RESPONSE_SCHEMA:
            raise PortfolioError("isolated authority worker response schema mismatch")
        if response.get("ok") is not True:
            error = response.get("error")
            if type(error) is not str or not error:
                error = "authority worker rejected request"
            raise PortfolioError(f"isolated authority worker: {error}")
        if completed.returncode != 0:
            raise PortfolioError("isolated authority worker failed after success response")
        result = response.get("payload")
        if type(result) is not dict:
            raise PortfolioError("isolated authority worker payload missing")
        return result

    def encode_bytes(raw: bytes) -> str:
        if not isinstance(raw, (bytes, bytearray)):
            raise PortfolioError("authority worker boundary requires bytes")
        return encode(bytes(raw)).decode("ascii")

    def decode_bytes(value: object, maximum: int, where: str) -> bytes:
        if type(value) is not str:
            raise PortfolioError(f"{where}: authority worker byte field missing")
        try:
            raw = decode(value.encode("ascii"), validate=True)
        except Exception as exc:
            raise PortfolioError(f"{where}: invalid worker base64") from exc
        if len(raw) > maximum:
            raise PortfolioError(f"{where}: worker byte bound exceeded")
        return raw

    def compile_current(
        source: Mapping[str, Any], authority: Mapping[str, Any]
    ) -> HostAuthorizedPortfolio:
        source_raw = _canonical(dict(source))
        authority_raw = _canonical(dict(authority))
        payload = run_worker(
            "compile",
            {
                "source": encode_bytes(source_raw),
                "authority": encode_bytes(authority_raw),
            },
        )
        expected = {
            "portfolio",
            "markdown",
            "receipt",
            "authority",
            "current_receipt",
            "host_seal",
        }
        if set(payload) != expected:
            raise PortfolioError("isolated authority compile response key mismatch")
        result_raw = decode_bytes(payload["portfolio"], 2_000_000, "portfolio.json")
        markdown_raw = decode_bytes(payload["markdown"], 2_000_000, "portfolio.md")
        receipt_raw = decode_bytes(payload["receipt"], 2_000_000, "receipt.json")
        authority_out = decode_bytes(
            payload["authority"], MAX_AUTHORITY_BYTES, "upstream-authority.json"
        )
        current_receipt_raw = decode_bytes(
            payload["current_receipt"], MAX_AUTHORITY_BYTES, "current-receipt.json"
        )
        host_seal_raw = decode_bytes(
            payload["host_seal"], MAX_AUTHORITY_BYTES, "host-seal.json"
        )
        result = load_json_bytes(result_raw, "result")
        receipt = load_json_bytes(receipt_raw, "receipt")
        authority_value = load_json_bytes(authority_out, "upstream authority")
        current_receipt = load_json_bytes(current_receipt_raw, "current receipt")
        host_seal = load_json_bytes(host_seal_raw, "host seal")
        if host_seal.get("schema") != PRODUCTION_HOST_SEAL_SCHEMA:
            raise PortfolioError("isolated authority worker did not return v3 host seal")
        compiled = CompiledPortfolio(
            result=result,
            result_bytes=result_raw,
            markdown_bytes=markdown_raw,
            receipt=receipt,
            receipt_bytes=receipt_raw,
        )
        authorized = AuthorizedPortfolio(
            compiled=compiled,
            authority=authority_value,
            authority_bytes=authority_out,
            current_receipt=current_receipt,
            current_receipt_bytes=current_receipt_raw,
        )
        return HostAuthorizedPortfolio(
            authorized=authorized,
            host_seal=host_seal,
            host_seal_bytes=host_seal_raw,
        )

    def verify_current(
        result_raw: bytes,
        markdown_raw: bytes,
        receipt_raw: bytes,
        authority_raw: bytes,
        current_receipt_raw: bytes,
        host_seal_raw: bytes,
    ) -> dict[str, Any]:
        payload = run_worker(
            "verify",
            {
                "portfolio": encode_bytes(result_raw),
                "markdown": encode_bytes(markdown_raw),
                "receipt": encode_bytes(receipt_raw),
                "authority": encode_bytes(authority_raw),
                "current_receipt": encode_bytes(current_receipt_raw),
                "host_seal": encode_bytes(host_seal_raw),
            },
        )
        return payload

    return compile_current, verify_current


compile_current, verify_current = _build_api()
del _build_api

__all__ = ["compile_current", "verify_current"]
