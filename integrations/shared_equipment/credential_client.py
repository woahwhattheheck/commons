"""Requester runtime client. Private key and decrypted value never go to stdout.

Keep CredentialRequest alive in the requesting runtime while its public request
travels through the HTTP/Slack equipment road. Call open() there, then use the
returned real value directly in that runtime. No key files or new vault needed.
"""
from __future__ import annotations

import json
import urllib.request
import uuid

from .credential_transfer import (
    CredentialTransferError, CredentialSources, crypto, open_credential, public_hex,
)


class CredentialRequest:
    def __init__(self, credential_ref: str, *, request_id: str | None = None, call_id: str = "retrieve"):
        self._private_key = crypto()[0].generate()
        self._arguments = {
            "credential_ref": credential_ref, "transfer_id": uuid.uuid4().hex,
            "request_id": request_id or "credential-" + uuid.uuid4().hex,
            "call_id": call_id, "recipient_public_key": public_hex(self._private_key),
        }

    def arguments(self) -> dict:
        return dict(self._arguments)

    def equipment_request(self) -> dict:
        return {"request_id": self._arguments["request_id"], "call_id": self._arguments["call_id"],
                "name": "credential_retrieve_sealed", "arguments": self.arguments()}

    def slack_request(self) -> str:
        return "<commons_equipment_request>" + json.dumps(self.equipment_request(), separators=(",", ":")) + "</commons_equipment_request>"

    def open(self, result: dict):
        """Accept a raw sealed result or existing HTTP/service result wrappers.

        If HTTP request/call IDs are present, compare them with the retained
        request as well. The encrypted envelope always binds both IDs itself.
        """
        try:
            for _ in range(4):
                if not isinstance(result, dict) or result.get("isError") or result.get("ok") is False:
                    raise ValueError()
                if "ciphertext" in result:
                    return open_credential(result, self._private_key, self._arguments)
                for field in ("request_id", "call_id"):
                    if field in result and result[field] != self._arguments[field]:
                        raise ValueError()
                result = result["result"]
        except Exception:
            raise CredentialTransferError("credential_delivery_invalid") from None
        raise CredentialTransferError("credential_delivery_invalid")


def retrieve_http(credential_ref: str, *, base_url="http://127.0.0.1:8878", opener=None):
    """Get an actual credential in caller memory through the existing gateway."""
    pending = CredentialRequest(credential_ref)
    request = urllib.request.Request(base_url.rstrip("/") + "/v1/tools/call",
        data=json.dumps(pending.equipment_request()).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with (opener or urllib.request.urlopen)(request, timeout=90) as response:
            result = json.loads(response.read())
    except Exception:
        raise CredentialTransferError("credential_transport_unavailable") from None
    return pending.open(result)


def retrieve_local(credential_ref: str):
    """Same-host direct raw reader; no broker, encryption dependency, or grant."""
    return CredentialSources().read(credential_ref)
