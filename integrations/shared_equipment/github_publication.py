"""GitHub metadata writes through the existing account publishing service."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from .services import EquipmentError, redacted


def publish(operation, arguments, operation_id, *, runner=None, client=None):
    if not isinstance(operation_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}", operation_id):
        raise EquipmentError("operation_id must be a stable publication ID")
    client = Path(client) if client is not None else Path.home() / ".commons/tjlabs-publication/publish.py"
    if not client.is_file():
        raise EquipmentError("existing account publishing client is unavailable; restore its shared installation")
    envelope = {"operation_id": operation_id, "operation": operation, "args": arguments}
    try:
        result = (runner or subprocess.run)(
            [sys.executable, str(client), "publish"],
            input=json.dumps(envelope, ensure_ascii=False), text=True, encoding="utf-8",
            capture_output=True, timeout=150,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        raise EquipmentError("publication response unavailable; reconcile the same operation_id",
                             code="publisher_transport_failed", uncertain=True) from None
    try:
        receipt = json.loads(result.stdout)
    except (ValueError, TypeError):
        raise EquipmentError("publication receipt unavailable; reconcile the same operation_id",
                             code="publisher_response_invalid", uncertain=True) from None
    if not isinstance(receipt, dict) or receipt.get("operation_id") != operation_id:
        raise EquipmentError("publication receipt identity mismatch; reconcile the same operation_id",
                             code="publisher_response_invalid", uncertain=True)
    ok = result.returncode == 0 and receipt.get("allow") is True and isinstance(receipt.get("receipt"), dict)
    uncertain = receipt.get("error") in {
        "GITHUB_DELIVERY_UNCERTAIN", "OPERATION_IN_PROGRESS_OR_REQUIRES_RECONCILIATION",
    } or receipt.get("state") in {"DISPATCHING", "DELIVERY_UNCERTAIN"}
    return {"ok": ok, "operation_id": operation_id, "uncertain": uncertain,
            "publication": redacted(receipt)}
