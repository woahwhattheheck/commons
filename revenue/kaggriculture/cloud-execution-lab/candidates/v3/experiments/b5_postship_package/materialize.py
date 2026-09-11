# SPDX-License-Identifier: Apache-2.0
"""Materialize an integration-ready B5 preview from the exact shipped V3.1 tree.

The source tree is never edited. A detached copy gets one default-OFF B5 package key,
the source-green helper, and the subordinate post-R04 call seam. The normal V3 builder
then owns FILES.json, overlay hashes and archive receipts in that detached tree.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys

LIVE_BASE = "a6120d0ea1bdb75eb0da2239220efce551f624a6"
LIVE_APPLY_SHA256 = "8c214c4e66a9081428c7df4ec051fe0af1ddaa22393b870822a7a362439edea5"
LIVE_PACKAGE_SHA256 = "400ae640f3258b6a6ff19f9da99c66ef9c433e315febb1d72c75296cddeb277c"
DONOR_HEAD = "15e8367e4d3fff41e7e6eb2d088327f558764454"
DONOR_BLOB = "4e4f9d490332f075cf50df595cb7a067d6236066"


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one live anchor, found {count}")
    return source.replace(old, new, 1)


def _copy_tree(source: Path, output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(
        source,
        output,
        ignore=shutil.ignore_patterns("dist", "__pycache__", "*.pyc"),
    )


def materialize(source: Path, output: Path) -> Path:
    source = source.resolve()
    output = output.resolve()
    apply_source = source / "apply_v3.py"
    manifest_source = source / "V3-MANIFEST.json"
    helper_source = Path(__file__).resolve().with_name("production_helper.py")

    apply_bytes = apply_source.read_bytes()
    apply_sha = hashlib.sha256(apply_bytes).hexdigest()
    if apply_sha != LIVE_APPLY_SHA256:
        raise SystemExit(f"live apply_v3.py drifted: {apply_sha} != {LIVE_APPLY_SHA256}")
    manifest = json.loads(manifest_source.read_text(encoding="utf-8"))
    if manifest.get("archive", {}).get("sha256") != LIVE_PACKAGE_SHA256:
        raise SystemExit("source V3 manifest is not the merged a612 package receipt")
    if manifest.get("keys", {}).get("r04_no_late_sale_advance", {}).get("default") is not False:
        # Package key default is false; score-facing merged config is applied via PARAMS below.
        raise SystemExit("unexpected L3 package-key manifest shape")
    if "b5_carrot_fertilizer" in manifest.get("keys", {}):
        raise SystemExit("source already contains a B5 package key")

    _copy_tree(source, output)

    helper_target = output / "overlay" / "b5_carrot_fertilizer.py"
    helper_target.write_bytes(helper_source.read_bytes())

    apply_path = output / "apply_v3.py"
    text = apply_path.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        '    "r04_strawberry_topup": True,\n}',
        '    "r04_strawberry_topup": True,\n    "b5_carrot_fertilizer": False,\n}',
        "B5 PARAMS default",
    )
    text = _replace_once(
        text,
        '    "    r04_strawberry_topup: bool = True\\n"\n)',
        '    "    r04_strawberry_topup: bool = True\\n"\n'
        '    "    # B5 CARROT no-detour fertilization; package-wired and shipped OFF.\\n"\n'
        '    "    b5_carrot_fertilizer: bool = False\\n"\n)',
        "B5 Features field",
    )
    hook = (
        '    "                                 bool(self.features.r04_strawberry_topup))'
        '(observation, configuration)\\n"\n'
    )
    replacement = hook + (
        '    "                if self.features.b5_carrot_fertilizer:\\n"\n'
        '    "                    from b5_carrot_fertilizer import apply_carrot_fertilizer\\n"\n'
        '    "                    before_b5 = output\\n"\n'
        '    "                    output = apply_carrot_fertilizer(observation, configuration, output)\\n"\n'
        '    "                    self.diagnostics[\'b5_carrot_fertilizer\'] = '
        '{\'activated\': output is not before_b5}\\n"\n'
    )
    text = _replace_once(text, hook, replacement, "B5 post-R04 seam")
    apply_path.write_text(text, encoding="utf-8")

    manifest_path = output / "V3-MANIFEST.json"
    detached_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    detached_manifest.setdefault("keys", {})["b5_carrot_fertilizer"] = {
        "default": False,
        "seam": "TitanAgent._v3_r03_act after the fully composed R04 delegate returns",
        "module": "b5_carrot_fertilizer.py",
        "effect": (
            "when explicitly enabled under R04, an already-authored literal PASS may become "
            "FERTILIZE only on that actor's current CARROT tile with carried fertilizer and "
            "incomplete coverage; exact-parent identity on malformed/nonstandard timing state"
        ),
        "source_donor_head": DONOR_HEAD,
        "source_donor_blob": DONOR_BLOB,
    }
    manifest_path.write_text(json.dumps(detached_manifest, indent=2) + "\n", encoding="utf-8")

    print("B5_PREVIEW_SOURCE", source)
    print("B5_PREVIEW_OUTPUT", output)
    print("B5_PREVIEW_LIVE_BASE", LIVE_BASE)
    print("B5_PREVIEW_DONOR", DONOR_HEAD, DONOR_BLOB)
    return output


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        raise SystemExit("usage: materialize.py <live-v3-root> <detached-output-v3-root>")
    materialize(Path(argv[0]), Path(argv[1]))


if __name__ == "__main__":
    main()
