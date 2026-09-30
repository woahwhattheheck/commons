"""Build the V3.1 Kaggle submission with R04 + promoted L3 no-late-sale-advance.

usage: python make_submission.py <candidates/v3 dir> <canonical tar.gz> <out.tar.gz> [horizon]

`build_v3` remains the deterministic base package function.  Submission-only edits are:
1. TITAN-CONFIG.json: r04_sale_window = true (existing V3 submission selection), and
2. r04_full_router.py: suppress E184 future-sale reservation at absolute step >= 648.

The L3 edit is an exact one-seam source transform.  It runs before `reserve_sales()` can
book `sale_window_debts`; pre-threshold debts still settle normally, and the tape's own
late SELL rows are untouched.  The threshold and seam match the green Riot L3 carrier
`riot/v3.1-lanes@dc1779ed79cd7fdd091187df1e8f0c4e5f185555`.
"""
from __future__ import annotations

import hashlib
import json
import sys

L3_STEP = 648
L3_SEAM = (
    "    reserve_sales(action, FarmView(observation), state, _POLICY.tapes[state.plan], step)\n"
)
L3_REPLACEMENT = (
    "    if step < 648:\n"
    "        reserve_sales(action, FarmView(observation), state, _POLICY.tapes[state.plan], step)\n"
)


def apply_l3_no_late_sale_advance(files):
    """Return a copy of package files with the exact L3 reservation gate applied.

    Fail closed if the audited E184 seam moved or became ambiguous.  No other file is
    touched, and the input mapping/bytes are not mutated.
    """
    out = dict(files)
    source = out["r04_full_router.py"].decode("utf-8")
    count = source.count(L3_SEAM)
    if count != 1:
        raise RuntimeError("L3 E184 reservation seam count %d != 1" % count)
    patched = source.replace(L3_SEAM, L3_REPLACEMENT, 1)
    out["r04_full_router.py"] = patched.encode("utf-8")
    return out


def build_submission(v3_dir, canonical, out_path, horizon=None):
    sys.path.insert(0, v3_dir)
    import build_v3  # noqa: E402

    files = build_v3.package_files(canonical)
    base_digest = hashlib.sha256(build_v3.build_bytes(files)).hexdigest()

    config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
    assert config["r04_sale_window"] is False
    config["r04_sale_window"] = True
    if horizon is not None:
        config["r04_sale_horizon"] = int(horizon)
    files["TITAN-CONFIG.json"] = (json.dumps(config, indent=2) + "\n").encode("utf-8")

    files = apply_l3_no_late_sale_advance(files)
    blob = build_v3.build_bytes(files)
    with open(out_path, "wb") as handle:
        handle.write(blob)

    changed = [
        "r03_full_router", "r04_sale_window", "r04_sale_horizon",
        "r01_shop_router", "r02_route_bank",
    ]
    print("base package", base_digest)
    print("submission  ", hashlib.sha256(blob).hexdigest(), len(files), "files", len(blob), "bytes ->", out_path)
    print("route keys:", {k: config[k] for k in changed})
    print("promoted L3:", {"r04_no_late_sale_advance": True, "step": L3_STEP})
    return blob


def main(argv):
    if len(argv) not in (3, 4):
        raise SystemExit("usage: make_submission.py <v3-dir> <canonical.tar.gz> <out.tar.gz> [horizon]")
    v3, canonical, out_path = argv[:3]
    horizon = int(argv[3]) if len(argv) == 4 else None
    build_submission(v3, canonical, out_path, horizon)


if __name__ == "__main__":
    main(sys.argv[1:])
