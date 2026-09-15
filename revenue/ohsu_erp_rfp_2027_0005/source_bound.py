from __future__ import annotations

"""Fail-closed bootstrap for the source-bound OHSU ERP decision surface.

The reviewed predecessor implementation is retained as a non-importable text
resource and integrated only after exact Git-blob identity and exact-once
source transforms are proven. This keeps the original API/CLI surface while
removing the caller-authored intent-receipt deadline bypass that survived the
#14537 merge.
"""

import hashlib as _bootstrap_hashlib
from pathlib import Path as _BootstrapPath

_BOOTSTRAP_DONOR_NAME = "_source_bound_engine_source.txt"
_BOOTSTRAP_DONOR_GIT_BLOB = "f41ca7eb804ea3558c7018bac63aef6b53edf3e8"

_bootstrap_path = _BootstrapPath(__file__).with_name(_BOOTSTRAP_DONOR_NAME)
_bootstrap_raw = _bootstrap_path.read_bytes()
_bootstrap_git_blob = _bootstrap_hashlib.sha1(
    b"blob " + str(len(_bootstrap_raw)).encode("ascii") + b"\0" + _bootstrap_raw
).hexdigest()
if _bootstrap_git_blob != _BOOTSTRAP_DONOR_GIT_BLOB:
    raise RuntimeError(
        "source_bound donor identity mismatch; refusing to compile unreviewed bytes"
    )

_bootstrap_source = _bootstrap_raw.decode("utf-8", "strict")

_BOOTSTRAP_OLD_DEADLINE = """        receipt = facts["intent_receipt"]
        if receipt is None and now_utc >= intent_utc:
            status = "HOLD_INTENT_DEADLINE"
            blockers.append("NO_INTENT_RECEIPT_AT_OR_AFTER_DEADLINE")
            actions.append("VERIFY_WITH_PROCUREMENT_WHETHER_RESPONSE_REMAINS_ELIGIBLE")
        elif receipt is not None and _dt.datetime.fromisoformat(
            receipt["submitted_at"].replace("Z", "+00:00")
        ) > intent_utc:
            status = "HOLD_INTENT_CHRONOLOGY"
            blockers.append("INTENT_RECEIPT_AFTER_CONFIRMED_DEADLINE")
            actions.append("VERIFY_INTENT_ACCEPTANCE_WITH_PROCUREMENT")
        elif facts["route"] == "UNKNOWN":
"""

_BOOTSTRAP_NEW_DEADLINE = """        receipt = facts["intent_receipt"]
        receipt_after_deadline = (
            receipt is not None
            and _dt.datetime.fromisoformat(
                receipt["submitted_at"].replace("Z", "+00:00")
            ) > intent_utc
        )
        if now_utc >= intent_utc:
            if receipt_after_deadline:
                status = "HOLD_INTENT_CHRONOLOGY"
                blockers.append("INTENT_RECEIPT_AFTER_CONFIRMED_DEADLINE")
                actions.append("VERIFY_INTENT_ACCEPTANCE_WITH_PROCUREMENT")
            else:
                status = "HOLD_INTENT_DEADLINE"
                blockers.append(
                    "NO_INTENT_RECEIPT_AT_OR_AFTER_DEADLINE"
                    if receipt is None
                    else "UNVERIFIED_CALLER_INTENT_RECEIPT_CANNOT_CLEAR_DEADLINE"
                )
                actions.append("VERIFY_WITH_PROCUREMENT_WHETHER_RESPONSE_REMAINS_ELIGIBLE")
        elif receipt_after_deadline:
            status = "HOLD_INTENT_CHRONOLOGY"
            blockers.append("INTENT_RECEIPT_AFTER_CONFIRMED_DEADLINE")
            actions.append("VERIFY_INTENT_ACCEPTANCE_WITH_PROCUREMENT")
        elif facts["route"] == "UNKNOWN":
"""

_BOOTSTRAP_OLD_SOURCE_POLICY = """        "source_policy": {
            "buyer_workbooks_published_to_public_repo": False,
            "source_digest_match_required": True,
            "attachment_provenance_authenticated_by_code": False,
        },
"""

_BOOTSTRAP_NEW_SOURCE_POLICY = """        "source_policy": {
            "buyer_workbooks_published_to_public_repo": False,
            "source_digest_match_required": True,
            "attachment_provenance_authenticated_by_code": False,
            "caller_intent_receipt_authenticated_by_code": False,
            "caller_intent_receipt_clears_deadline": False,
        },
"""

for _bootstrap_old, _bootstrap_new, _bootstrap_label in (
    (_BOOTSTRAP_OLD_DEADLINE, _BOOTSTRAP_NEW_DEADLINE, "deadline gate"),
    (_BOOTSTRAP_OLD_SOURCE_POLICY, _BOOTSTRAP_NEW_SOURCE_POLICY, "source policy"),
):
    if _bootstrap_source.count(_bootstrap_old) != 1:
        raise RuntimeError(
            f"source_bound donor {_bootstrap_label} transform is not exact-once"
        )
    _bootstrap_source = _bootstrap_source.replace(_bootstrap_old, _bootstrap_new, 1)

# Execute the integrated engine in this module's real namespace. This preserves
# the predecessor's public/internal symbols, CLI behavior, and test monkeypatch
# semantics (notably `_now_utc`) without exposing an importable unsafe donor.
exec(compile(_bootstrap_source, str(_bootstrap_path), "exec"), globals(), globals())

# Imported-module cleanup only. When invoked with `python -m ...`, the donor's
# own `if __name__ == "__main__"` exits through main() before reaching here.
for _bootstrap_name in tuple(globals()):
    if _bootstrap_name.startswith("_bootstrap") or _bootstrap_name.startswith("_BOOTSTRAP"):
        globals().pop(_bootstrap_name, None)
