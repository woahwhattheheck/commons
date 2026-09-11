"""Build the Kaggle submission archive: the V3 package with R04 on, nothing else changed.

usage: python make_submission.py <candidates/v3 dir> <canonical tar.gz> <out.tar.gz> [horizon]

Uses build_v3.package_files() and build_v3.build_bytes() so the archive is the same
deterministic function of (canonical, overlay, apply_v3) as the V3 build, with exactly one
edit: TITAN-CONFIG.json sets r04_sale_window true (and r04_sale_horizon if given).
"""
import hashlib
import json
import sys


def fail(message):
    raise SystemExit(message)


if not 4 <= len(sys.argv) <= 5:
    fail("usage: python make_submission.py <candidates/v3 dir> <canonical tar.gz> <out.tar.gz> [horizon]")

V3, CANON, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
if len(sys.argv) > 4:
    try:
        HORIZON = int(sys.argv[4])
    except ValueError:
        fail("sale horizon must be an integer of at least 1")
    if HORIZON < 1:
        fail("sale horizon must be at least 1")
else:
    HORIZON = None

sys.path.insert(0, V3)
import build_v3  # noqa: E402

files = build_v3.package_files(CANON)
base_digest = hashlib.sha256(build_v3.build_bytes(files)).hexdigest()
config = json.loads(files["TITAN-CONFIG.json"].decode("utf-8"))
if config.get("r04_sale_window") is not False:
    fail("refusing to build submission: expected source package r04_sale_window=false")
config["r04_sale_window"] = True
if HORIZON is not None:
    config["r04_sale_horizon"] = HORIZON
files["TITAN-CONFIG.json"] = (json.dumps(config, indent=2) + "\n").encode("utf-8")
blob = build_v3.build_bytes(files)
with open(OUT, "wb") as handle:
    handle.write(blob)
changed = [k for k in ("r03_full_router", "r04_sale_window", "r04_sale_horizon", "r01_shop_router", "r02_route_bank")]
print("base package", base_digest)
print("submission  ", hashlib.sha256(blob).hexdigest(), len(files), "files", len(blob), "bytes ->", OUT)
print("route keys:", {k: config[k] for k in changed})
