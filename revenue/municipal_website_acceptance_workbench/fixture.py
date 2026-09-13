from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from .model import (
    ACCESSIBILITY,
    ACCESSIBILITY_EVIDENCE_FAILURE,
    INTEGRATION,
    INTEGRATION_FIXTURE_MISMATCH,
    LINK_DOCUMENT,
    LINK_OR_DOCUMENT_FAILURE,
    MIGRATION,
    MIGRATION_DIGEST_MISMATCH,
    REDIRECT,
    REDIRECT_CHAIN_INVALID,
    RESTORE,
    RESTORE_EVIDENCE_INVALID,
    ROLE_PERMISSION,
    ROLE_PERMISSION_DRIFT,
    sha256_text,
)

AS_OF = datetime(2026, 9, 13, 9, 40, tzinfo=timezone.utc)
CLEAN_PER_KIND = 20
DEFECT_PER_KIND = 4
TOTAL_CLEAN = CLEAN_PER_KIND * 7
TOTAL_DEFECT = DEFECT_PER_KIND * 7
TOTAL = TOTAL_CLEAN + TOTAL_DEFECT


def _ts(days_ago: int = 1) -> str:
    return (AS_OF - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def _base(sequence: int, kind: str, resource_id: str, details: dict[str, Any]) -> dict[str, Any]:
    source_ref = f"synthetic://municipal-uat/{kind.lower()}/{sequence:03d}"
    return {
        "sequence": sequence,
        "evidence_id": f"EVID-{sequence:04d}",
        "kind": kind,
        "resource_id": resource_id,
        "source_ref": source_ref,
        "observed_at": _ts(),
        "source_snapshot_sha256": sha256_text(source_ref),
        "details": details,
    }


def _clean_for_kind(kind: str, sequence: int, index: int) -> dict[str, Any]:
    digest = sha256_text(f"{kind}:{index}:expected")
    if kind == MIGRATION:
        return _base(sequence, kind, f"PAGE-{index:03d}", {
            "legacy_path": f"/legacy/page-{index}",
            "new_path": f"/services/page-{index}",
            "expected_content_sha256": digest,
            "observed_content_sha256": digest,
        })
    if kind == REDIRECT:
        return _base(sequence, kind, f"REDIR-{index:03d}", {
            "legacy_path": f"/old/{index}",
            "expected_target_path": f"/new/{index}",
            "observed_target_path": f"/new/{index}",
            "http_status": 301,
            "hop_count": 1,
        })
    if kind == LINK_DOCUMENT:
        return _base(sequence, kind, f"LINK-{index:03d}", {
            "page_path": f"/departments/d{index}",
            "target_path": f"/documents/doc-{index}.pdf",
            "http_status": 200,
            "document_expected_sha256": digest,
            "document_observed_sha256": digest,
        })
    if kind == ACCESSIBILITY:
        return _base(sequence, kind, f"A11Y-{index:03d}", {
            "page_path": f"/pages/a11y-{index}",
            "standard": "WCAG2.2AA",
            "tool": "synthetic-accessibility-scanner",
            "critical_count": 0,
            "serious_count": 0,
            "max_age_days": 30,
        })
    if kind == INTEGRATION:
        return _base(sequence, kind, f"INTEG-{index:03d}", {
            "integration_name": ["forms", "calendar", "agenda"][index % 3],
            "fixture_id": f"FIX-{index:03d}",
            "expected_result_sha256": digest,
            "observed_result_sha256": digest,
        })
    if kind == ROLE_PERMISSION:
        permissions = ["CONTENT_EDIT", "CONTENT_VIEW"] if index % 2 else ["CONTENT_VIEW"]
        permissions = sorted(permissions)
        return _base(sequence, kind, f"ROLE-{index:03d}", {
            "role": "EDITOR" if index % 2 else "VIEWER",
            "expected_permissions": permissions,
            "observed_permissions": list(permissions),
        })
    if kind == RESTORE:
        return _base(sequence, kind, f"RESTORE-{index:03d}", {
            "backup_sha256": digest,
            "restored_sha256": digest,
            "restore_exit_code": 0,
            "expected_item_count": 1000 + index,
            "restored_item_count": 1000 + index,
        })
    raise AssertionError(kind)


def build_synthetic_case() -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    kinds = [MIGRATION, REDIRECT, LINK_DOCUMENT, ACCESSIBILITY, INTEGRATION, ROLE_PERMISSION, RESTORE]
    rows: list[dict[str, Any]] = []
    expected = {
        MIGRATION_DIGEST_MISMATCH: [],
        REDIRECT_CHAIN_INVALID: [],
        LINK_OR_DOCUMENT_FAILURE: [],
        ACCESSIBILITY_EVIDENCE_FAILURE: [],
        INTEGRATION_FIXTURE_MISMATCH: [],
        ROLE_PERMISSION_DRIFT: [],
        RESTORE_EVIDENCE_INVALID: [],
    }
    sequence = 0
    clean_by_kind: dict[str, list[dict[str, Any]]] = {}
    for kind in kinds:
        clean_by_kind[kind] = []
        for index in range(1, CLEAN_PER_KIND + 1):
            sequence += 1
            row = _clean_for_kind(kind, sequence, index)
            rows.append(row)
            clean_by_kind[kind].append(row)

    defect_plan = [
        (MIGRATION, MIGRATION_DIGEST_MISMATCH),
        (REDIRECT, REDIRECT_CHAIN_INVALID),
        (LINK_DOCUMENT, LINK_OR_DOCUMENT_FAILURE),
        (ACCESSIBILITY, ACCESSIBILITY_EVIDENCE_FAILURE),
        (INTEGRATION, INTEGRATION_FIXTURE_MISMATCH),
        (ROLE_PERMISSION, ROLE_PERMISSION_DRIFT),
        (RESTORE, RESTORE_EVIDENCE_INVALID),
    ]
    for kind, code in defect_plan:
        for index in range(4):
            sequence += 1
            row = deepcopy(clean_by_kind[kind][index])
            row["sequence"] = sequence
            row["evidence_id"] = f"EVID-{sequence:04d}"
            row["resource_id"] = f"DEFECT-{kind}-{index+1}"
            row["source_ref"] = f"synthetic://municipal-uat/defect/{kind.lower()}/{index+1}"
            row["source_snapshot_sha256"] = sha256_text(row["source_ref"])
            if kind == MIGRATION:
                row["details"]["observed_content_sha256"] = sha256_text(f"bad-migration-{index}")
            elif kind == REDIRECT:
                row["details"]["hop_count"] = 2
            elif kind == LINK_DOCUMENT:
                row["details"]["http_status"] = 404
            elif kind == ACCESSIBILITY:
                row["details"]["critical_count"] = 1
            elif kind == INTEGRATION:
                row["details"]["observed_result_sha256"] = sha256_text(f"bad-integration-{index}")
            elif kind == ROLE_PERMISSION:
                row["details"]["observed_permissions"] = ["CONTENT_DELETE"]
            elif kind == RESTORE:
                row["details"]["restored_item_count"] += 1
            rows.append(row)
            expected[code].append(row["evidence_id"])
    assert sequence == TOTAL
    return rows, expected
