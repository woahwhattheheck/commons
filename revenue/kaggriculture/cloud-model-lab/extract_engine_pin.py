"""Extract the pinned unit-phase transition into a standalone bundled module.

The hosted archive must not depend on `kaggle_environments` being importable in
the agent process, and it must not fall back to a re-implementation: it carries
the engine's own `_apply_unit_action` and the exact transitive closure of the
helpers and constants that routine needs, copied VERBATIM from the pinned source,
with the upstream Apache-2.0 notice.

Verbatim matters. A hand-written copy would drift from the engine the moment the
pin moved, and every guard in `native_motifs.py` is only as good as the transition
it simulates. `tests/test_engine_pin_parity.py` re-checks the bundle against the
installed engine on real recorded turns and on generated states.
"""

import argparse
import ast
import hashlib
import os

ROOT = "_apply_unit_action"
HEADER = '''"""Bundled pinned unit-phase transition (GENERATED -- do not hand-edit).

Copied verbatim from Kaggle/kaggle-environments, which is licensed under the
Apache License, Version 2.0. The upstream NOTICE and full licence text ship
alongside this file as LICENSE-APACHE-2.0.txt.

  upstream   kaggle_environments/envs/kaggriculture/kaggriculture.py
  pin        {pin}
  sha256     {sha}
  extracted  {names}

Regenerate with `extract_engine_pin.py`; verify with tests/test_engine_pin_parity.py.
"""

'''


def closure(tree):
    defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    consts = {t.id: n for n in tree.body if isinstance(n, ast.Assign)
              for t in n.targets if isinstance(t, ast.Name)}
    need, seen, used = [ROOT], set(), set()
    while need:
        f = need.pop()
        if f in seen:
            continue
        seen.add(f)
        for nd in ast.walk(defs[f]):
            if isinstance(nd, ast.Name):
                if nd.id in defs and nd.id not in seen:
                    need.append(nd.id)
                if nd.id in consts:
                    used.add(nd.id)
    return defs, consts, seen, used


def build(src_path, pin, out_path):
    src = open(src_path).read()
    sha = hashlib.sha256(src.encode()).hexdigest()
    lines = src.split("\n")
    tree = ast.parse(src)
    defs, consts, fns, cns = closure(tree)

    def seg(node):
        # verbatim source segment, including any decorator-free leading blank
        return "\n".join(lines[node.lineno - 1:node.end_lineno])

    parts = [seg(consts[c]) for c in sorted(cns)]
    parts += [seg(defs[f]) for f in sorted(fns)]
    body = HEADER.format(pin=pin, sha=sha,
                         names=", ".join(sorted(cns) + sorted(fns)))
    body += "\n\n".join(parts) + "\n"
    with open(out_path, "w") as fh:
        fh.write(body)
    return {"source_sha256": sha, "functions": sorted(fns), "constants": sorted(cns),
            "bundle_sha256": hashlib.sha256(body.encode()).hexdigest()[:16],
            "bytes": len(body)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source",
                    default="/home/user/work/engine/kaggle_environments/envs/"
                            "kaggriculture/kaggriculture.py")
    ap.add_argument("--pin", default="28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c")
    ap.add_argument("--out", default="engine_pin.py")
    ap.add_argument("--license",
                    default="/home/user/work/engine/LICENSE")
    a = ap.parse_args()
    info = build(a.source, a.pin, a.out)
    dst = os.path.join(os.path.dirname(a.out) or ".", "LICENSE-APACHE-2.0.txt")
    if os.path.exists(a.license):
        with open(a.license) as fh, open(dst, "w") as out:
            out.write(fh.read())
        info["license"] = dst
    import json
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
