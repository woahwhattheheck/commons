"""Build the score-facing V3.1 submission archive with the field-gated R04 tuple.

usage: python make_submission.py <candidates/v3 dir> <canonical tar.gz> <out.tar.gz> [horizon]

Uses build_v3.package_files() and build_v3.build_bytes() so the archive is the same
deterministic function of (canonical, overlay, apply_v3) as the V3.1 build, then performs
only the submission config transform:

* r04_sale_window = true;
* r04_sale_fertilizer = true;
* r04_cattle_early = false;
* r04_sale_horizon = 8 unless argv[4] supplies a positive integer override.

All other shipped keys, including H4 ``r04_strawberry_topup`` and rival-gated L3
``r04_no_late_sale_advance``, are inherited unchanged from the materialized package.

The cattle default is intentionally OFF for the score-facing submission after the
2026-09-11 opponent-diverse field harm check: 1,984 games/arm against 14 published
agents lost 48 baseline wins with cattle_early enabled (1909-75 vs 1957-27), while
sale_fertilizer preserved the 1957-27 record and improved paired margin.
"""
from __future__ import annotations

import hashlib
import json
import sys
from typing import Mapping


DEFAULT_SUBMISSION_HORIZON = 8
SUBMISSION_KEYS = (
    "r03_full_router",
    "r04_sale_window",
    "r04_sale_horizon",
    "r04_sale_fertilizer",
    "r04_cattle_early",
    "r04_no_late_sale_advance",
    "r04_strawberry_topup",
    "r01_shop_router",
    "r02_route_bank",
)


def _require_bool(config: Mapping[str, object], key: str) -> None:
    if key not in config or type(config[key]) is not bool:
        raise AssertionError(f"{key} must exist as a JSON boolean before submission transform")


def _positive_int(value, label):
    if type(value) is not int or value <= 0:
        raise AssertionError(f"{label} must be a positive integer")
    return value


def apply_submission_config(files, horizon=None):
    """Return a detached package-file mapping with the field-gated submission config.

    This helper is intentionally pure with respect to ``files`` so tooling/tests can
    prove that TITAN-CONFIG.json is the only changed package member.
    """
    out = dict(files)
    config = json.loads(out["TITAN-CONFIG.json"].decode("utf-8"))
    if not isinstance(config, dict):
        raise AssertionError("TITAN-CONFIG.json must decode to an object")
    for key in ("r04_sale_window", "r04_sale_fertilizer", "r04_cattle_early"):
        _require_bool(config, key)
    _positive_int(config.get("r04_sale_horizon"), "base r04_sale_horizon")
    if config["r04_sale_window"] is not False:
        raise AssertionError("base package must ship with r04_sale_window=false")

    target_horizon = DEFAULT_SUBMISSION_HORIZON if horizon is None else _positive_int(
        horizon, "submission horizon"
    )
    config["r04_sale_window"] = True
    config["r04_sale_horizon"] = target_horizon
    config["r04_sale_fertilizer"] = True
    config["r04_cattle_early"] = False

    out["TITAN-CONFIG.json"] = (json.dumps(config, indent=2) + "\n").encode("utf-8")
    return out, config


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) not in (3, 4):
        raise SystemExit(
            "usage: python make_submission.py <candidates/v3 dir> <canonical tar.gz> <out.tar.gz> [horizon]"
        )
    v3, canon, output = argv[:3]
    # Fail closed on caller-controlled score-facing input before importing the package
    # builder or touching canonical/package bytes. This preserves the reviewed builder
    # boundary even for malformed/invalid CLI horizons.
    horizon = None
    if len(argv) == 4:
        horizon = _positive_int(int(argv[3]), "submission horizon")

    sys.path.insert(0, v3)
    import build_v3  # noqa: E402

    base_files = build_v3.package_files(canon)
    base_digest = hashlib.sha256(build_v3.build_bytes(base_files)).hexdigest()
    files, config = apply_submission_config(base_files, horizon)
    blob = build_v3.build_bytes(files)
    with open(output, "wb") as handle:
        handle.write(blob)

    print("base package", base_digest)
    print("submission  ", hashlib.sha256(blob).hexdigest(), len(files), "files", len(blob), "bytes ->", output)
    print("route keys:", {key: config[key] for key in SUBMISSION_KEYS})


if __name__ == "__main__":
    main()
