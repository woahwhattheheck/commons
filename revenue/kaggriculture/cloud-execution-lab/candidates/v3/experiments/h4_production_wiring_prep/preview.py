"""Executable, non-mutating preview for wiring reviewed H4 into the packaged R04 route.

This script deliberately never edits the repository. It consumes the exact files on the
current checkout, asserts the known V3.1/H4 anchors, and materializes a prospective patch in
a caller-supplied temporary/output directory. The output is wiring *prep*, not a package
receipt and not a default/promotion action.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
REPO_ROOT = V3.parents[4]
APPLY = V3 / "apply_v3.py"
DONOR = V3 / "experiments" / "h4_strawberry" / "r04_h4_strawberry.py"
OVERLAY_R04 = V3 / "overlay" / "r04_full_router.py"

EXPECTED_DONOR_BLOB = "ecad11eb195a82273f73b78ac7b319552a27cbcd"
EXPECTED_R04_BLOB = "21c4f1db0298f8955b1f5ad366bd780a89cad206"


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_apply_v3(text: str) -> str:
    """Return a prospective apply_v3.py with one default-off H4 feature dial.

    The production route always imports the already-reviewed H4 wrapper. With the new dial
    false (the default), that wrapper leaves the H4 transform off and preserves the reviewed
    POLICY_AGENT -> ROW_ORDER -> EVENING_FLUSH -> OPEN ordering. With the dial true it inserts
    only the reviewed strawberry reconciliation before ROW_ORDER.
    """
    text = replace_once(
        text,
        '    "r04_cattle_early": True,\n',
        '    "r04_cattle_early": True,\n    "r04_strawberry_topup": False,\n',
        "PARAMS r04 default",
    )
    text = replace_once(
        text,
        '    "    r04_cattle_early: bool = True\\n"\n',
        '    "    r04_cattle_early: bool = True\\n"\n'
        '    "    r04_strawberry_topup: bool = False\\n"\n',
        "Feature field",
    )
    text = replace_once(
        text,
        '    "                from r04_full_router import install\\n"\n',
        '    "                from r04_h4_strawberry import install\\n"\n',
        "R04 installer import",
    )
    text = replace_once(
        text,
        '    "                                 bool(self.features.r04_cattle_early))(observation, configuration)\\n"\n',
        '    "                                 bool(self.features.r04_cattle_early),\\n"\n'
        '    "                                 bool(self.features.r04_strawberry_topup))(observation, configuration)\\n"\n',
        "R04 installer argument",
    )
    text = replace_once(
        text,
        '    "                self.diagnostics[\'cattle_early\'] = bool(self.features.r04_cattle_early)\\n"\n',
        '    "                self.diagnostics[\'cattle_early\'] = bool(self.features.r04_cattle_early)\\n"\n'
        '    "                self.diagnostics[\'strawberry_topup\'] = bool(self.features.r04_strawberry_topup)\\n"\n',
        "R04 diagnostics",
    )
    ast.parse(text, filename="apply_v3.py")
    return text


def materialize(out_dir: Path) -> dict[str, str]:
    """Emit only prospective source files below *out_dir* and return their blob receipts."""
    out_dir = Path(out_dir).resolve()
    repo_root = REPO_ROOT.resolve()
    if out_dir == repo_root or repo_root in out_dir.parents:
        raise ValueError("refusing to materialize wiring preview inside repository")

    donor = DONOR.read_bytes()
    r04 = OVERLAY_R04.read_bytes()
    if git_blob_sha(donor) != EXPECTED_DONOR_BLOB:
        raise ValueError("reviewed H4 donor blob drift")
    if git_blob_sha(r04) != EXPECTED_R04_BLOB:
        raise ValueError("reviewed R04 base blob drift")

    apply_text = APPLY.read_text(encoding="utf-8")
    patched_apply = patch_apply_v3(apply_text)
    ast.parse(donor.decode("utf-8"), filename="r04_h4_strawberry.py")

    target_v3 = out_dir / "candidates" / "v3"
    target_overlay = target_v3 / "overlay"
    target_overlay.mkdir(parents=True, exist_ok=True)
    (target_v3 / "apply_v3.py").write_text(patched_apply, encoding="utf-8")
    shutil.copyfile(DONOR, target_overlay / "r04_h4_strawberry.py")

    receipts = {
        "source_apply_blob": git_blob_sha(APPLY.read_bytes()),
        "source_r04_blob": git_blob_sha(r04),
        "source_h4_donor_blob": git_blob_sha(donor),
        "preview_apply_blob": git_blob_sha(patched_apply.encode("utf-8")),
        "preview_h4_overlay_blob": git_blob_sha((target_overlay / "r04_h4_strawberry.py").read_bytes()),
    }
    return receipts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipts = materialize(args.out)
    for key, value in sorted(receipts.items()):
        print(f"{key}={value}")
    print("H4_PRODUCTION_WIRING_PREVIEW_OK")


if __name__ == "__main__":
    main()
