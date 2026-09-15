from __future__ import annotations

import math
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping


def install(base: ModuleType) -> None:
    """Install narrow fail-closed guards over the reviewed base generation."""
    original_sha256_tree = base.sha256_tree
    original_verify_receipt = base.verify_receipt

    def sha256_tree(root: Any) -> str:
        root_path = Path(root)
        if root_path.is_symlink():
            raise base.ContractError("zarr path must be a real directory, not a symlink")
        return original_sha256_tree(root)

    def verify_receipt(receipt: Mapping[str, Any]) -> bool:
        if not original_verify_receipt(receipt):
            return False
        try:
            config = receipt["audit_config"]
            summary = receipt["audit_summary"]
            accepted = summary["accepted_points"]
            fraction = float(summary["accepted_fraction"])
            expected_decision = (
                "REVIEW"
                if accepted > 0
                and fraction >= float(config["min_global_review_fraction"])
                else "ABSTAIN"
            )
            if summary["decision"] != expected_decision:
                return False
            median_offset = summary["median_accepted_offset"]
            max_abs_offset = summary["max_abs_accepted_offset"]
            if accepted == 0:
                return median_offset is None and max_abs_offset is None
            if any(
                type(value) not in (int, float) or not math.isfinite(float(value))
                for value in (median_offset, max_abs_offset)
            ):
                return False
            max_offset = float(config["max_offset"])
            if abs(float(median_offset)) > max_offset:
                return False
            if not (0.0 <= float(max_abs_offset) <= max_offset):
                return False
            return True
        except (KeyError, TypeError, ValueError):
            return False

    base.sha256_tree = sha256_tree
    base.verify_receipt = verify_receipt
