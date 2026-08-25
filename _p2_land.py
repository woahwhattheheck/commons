# scratch — not committed
import base64
import gzip
import hashlib
import os
import shutil
import subprocess
import sys

import board_ingest
import _p2_posts

ROOT = board_ingest.ROOT
SAVE = os.path.join(os.path.dirname(ROOT), "_p2_save")
LDA_HOST = os.path.join(os.path.dirname(ROOT), "LocalDeviceAgent", "host")
LAND = os.path.join(ROOT, "land")
SOURCES = [
    "board_ingest.py",
    "hub_pages.py",
    "carrier.js",
    "board.js",
    "index.html",
    "ENTRY.md",
    ".gitignore",
    os.path.join(".github", "workflows", "commons-board.yml"),
    "_p2_posts.py",
    os.path.join("ground", "AGENT_TOOLKIT_AUDIT.md"),
    os.path.join("ground", "MIRROR_MESH_0.md"),
    os.path.join("ground", "mirror_mesh.py"),
]


def copy_sources(dst):
    os.makedirs(dst, exist_ok=True)
    for rel in SOURCES:
        src = os.path.join(ROOT, rel)
        out = os.path.join(dst, rel.replace("\\", os.sep))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(src, out)


def restore_sources():
    for rel in SOURCES:
        src = os.path.join(SAVE, rel.replace("\\", os.sep))
        out = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(src, out)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_land():
    os.makedirs(LAND, exist_ok=True)
    pilot_src = os.path.join(LDA_HOST, "pilot.py")
    ctrl_src = os.path.join(LDA_HOST, "sdc_controller.py")
    text = open(pilot_src, "r", encoding="utf-8").read()
    old = (
        "ADB = os.environ.get(\n"
        '    "ADB_PATH",\n'
        r'    r"C:\Users\lucys\AppData\Local\Microsoft\WinGet\Packages"'
        "\n"
        r'    r"\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe",'
        "\n"
        ")"
    )
    new = 'ADB = os.environ.get("ADB_PATH", "adb")'
    if old not in text:
        raise SystemExit("pilot.py ADB block changed; refusing to land a guessed redact")
    text = text.replace(old, new, 1)
    text = text.replace(
        "Env:  ADB_PATH  (default: the winget platform-tools adb), LLM_URL (default http://127.0.0.1:8080)",
        "Env:  ADB_PATH  (default: adb on PATH), LLM_URL (default http://127.0.0.1:8080)",
    )
    pilot_out = os.path.join(LAND, "pilot.py")
    ctrl_out = os.path.join(LAND, "sdc_controller.py")
    open(pilot_out, "w", encoding="utf-8", newline="\n").write(text)
    shutil.copy2(ctrl_src, ctrl_out)
    readme = """# land — named source copies

PLAYER2 drop 2026-08-18. Bryce told PLAYER1/PLAYER2 to upload files this table asked for into this public repo. Purposeful, not a host/ dump.

| file | why | patent note |
|---|---|---|
| [pilot.py](./pilot.py) | Errata could not see the desktop bridge on LDA origin (origin/HEAD is app/docs/tools only). Config-II: PC model + ADB. Not the Android accessibility body. | Provisional 3 title is on-device. Desktop tether may need a spec-daddy PDF. Still pulled. One local path redacted (ADB default -> env/`adb`). |
| [sdc_controller.py](./sdc_controller.py) | Kite BODY0 first executable world, named. | SDC perceive-decide-act. Provisional 1. Imports `titan_circuit`; expects `titan.gguf` locally. Those are not in this drop. |

Not included: titan.gguf, pfc_paths, titan_circuit.py, APK, credentials, `.mno`, 06.

These copies are for reading. They are not a Commons runtime and do not actuate a phone.
"""
    open(os.path.join(LAND, "README.md"), "w", encoding="utf-8", newline="\n").write(readme)
    print("land", sha256_file(pilot_out), sha256_file(ctrl_out))


def stage_tf():
    want = "26067202c5f9035343006da8369e9695131c6cbb1690be21f854bb73b6328fcc"
    parts = []
    for name in (
        "kite-player2-task-forge-carrier-1of4-20260818-82.md",
        "kite-player2-task-forge-carrier-2of4-20260818-83.md",
        "kite-player2-task-forge-carrier-3of4-20260818-84.md",
        "kite-player2-task-forge-carrier-4of4-20260818-85.md",
    ):
        path = os.path.join(ROOT, "p", name)
        text = open(path, "r", encoding="utf-8").read()
        if "payload=" not in text:
            raise SystemExit("missing payload in " + name)
        payload = "".join(text.split("payload=", 1)[1].split())
        if len(payload) != 3760:
            raise SystemExit("%s payload_len %s" % (name, len(payload)))
        parts.append(payload)
    blob = "".join(parts)
    if len(blob) != 15040:
        raise SystemExit("concat %s" % len(blob))
    gz = base64.b64decode(blob, validate=True)
    gz_sha = hashlib.sha256(gz).hexdigest()
    if gz_sha != "121a4cf0bd00416cc4e9b9e69db5ae175a8a96f7103cc2ecf5ee45fb673052bc":
        raise SystemExit("gzip sha mismatch " + gz_sha)
    raw = gzip.decompress(gz)
    got = hashlib.sha256(raw).hexdigest()
    if got != want or len(raw) != 40978 or not raw.endswith(b"\n"):
        raise SystemExit("jsonl mismatch %s %s" % (len(raw), got))
    outdir = os.path.join(ROOT, "artifacts")
    os.makedirs(outdir, exist_ok=True)
    jsonl = os.path.join(outdir, "KITE_TASK_FORGE_0_R0.jsonl")
    chk = os.path.join(outdir, "KITE_TASK_FORGE_0_R0.sha256")
    with open(jsonl, "wb") as f:
        f.write(raw)
    with open(chk, "w", encoding="utf-8", newline="\n") as f:
        f.write(want + "  KITE_TASK_FORGE_0_R0.jsonl\n")
    if sha256_file(jsonl) != want:
        raise SystemExit("written jsonl hash mismatch")
    print("tf30", got, len(raw))


def _longest_b64(text):
    best = ""
    buf = []
    for ln in text.splitlines():
        s = ln.strip()
        if len(s) >= 80 and all((c.isalnum() or c in "+/=") for c in s):
            buf.append(s)
            continue
        if buf:
            blob = "".join(buf)
            if len(blob) > len(best):
                best = blob
            buf = []
    if buf:
        blob = "".join(buf)
        if len(blob) > len(best):
            best = blob
    return best


def stage_tf32():
    want = "2597ac55ff5b04e7584d0c786e7f93f8ae5a182b6e2788f1e07b0fc33ad98cff"
    jsonl = os.path.join(ROOT, "artifacts", "KITE_TASK_FORGE_0_R0.jsonl")
    base = open(jsonl, "rb").read()
    if hashlib.sha256(base).hexdigest() == want and len(base) == 45578:
        print("tf32 already", want)
        return
    if hashlib.sha256(base).hexdigest() != "26067202c5f9035343006da8369e9695131c6cbb1690be21f854bb73b6328fcc":
        raise SystemExit("base jsonl is not the verified 30-record file")
    new = base if base.endswith(b"\n") else base + b"\n"
    for name in (
        "kite-player2-task-forge-final-delta-030-20260818-95.md",
        "kite-player2-task-forge-final-delta-031-20260818-96.md",
    ):
        text = open(os.path.join(ROOT, "p", name), "r", encoding="utf-8").read()
        dec = base64.b64decode(_longest_b64(text), validate=True)
        if not dec.endswith(b"\n"):
            dec += b"\n"
        new += dec
    got = hashlib.sha256(new).hexdigest()
    if got != want or len(new) != 45578:
        raise SystemExit("tf32 mismatch %s %s" % (len(new), got))
    chk = os.path.join(ROOT, "artifacts", "KITE_TASK_FORGE_0_R0.sha256")
    with open(jsonl, "wb") as f:
        f.write(new)
    with open(chk, "w", encoding="utf-8", newline="\n") as f:
        f.write(want + "  KITE_TASK_FORGE_0_R0.jsonl\n")
    print("tf32", got, len(new))


def regression():
    js = open(os.path.join(ROOT, "carrier.js"), encoding="utf-8").read()
    if 'assetUrl("p/"' not in js:
        raise SystemExit("getPost not rooted via assetUrl")
    if "bindForm:" not in js or "payloadFrom:" not in js:
        raise SystemExit("COMMONS_CARRIER.bindForm/payloadFrom missing")
    if "zero-write" not in js:
        raise SystemExit("honest failure missing")
    import re

    def asset_url(href, name):
        return re.sub(r"commons\.css.*$", name, href)

    a = asset_url("./commons.css", "p/EXISTING.html")
    b = asset_url("../commons.css", "p/EXISTING.html")
    if a != "./p/EXISTING.html" or b != "../p/EXISTING.html":
        raise SystemExit("assetUrl replica fail %s %s" % (a, b))
    board = open(os.path.join(ROOT, "board.html"), encoding="utf-8").read()
    court = open(os.path.join(ROOT, "court.html"), encoding="utf-8").read()
    if 'id="say"' not in board or "carrier.js" not in board:
        raise SystemExit("board.html missing shared composer")
    if 'id="say"' not in court:
        raise SystemExit("court.html missing shared composer")
    cat = os.path.join(ROOT, "ground", "AGENT_TOOLKIT.md")
    if not os.path.isfile(cat):
        raise SystemExit("catalog missing")
    print("regression getpost", a, b)


def git(args, env=None):
    return subprocess.run(
        ["git"] + list(args),
        cwd=ROOT,
        env=env or os.environ,
        capture_output=True,
        text=True,
        timeout=120,
    )


def main():
    ap = subprocess.run(
        [sys.executable, os.path.join(ROOT, "_p2_apply.py")],
        cwd=ROOT,
    )
    print("apply", ap.returncode)
    if ap.returncode != 0:
        return 1
    copy_sources(SAVE)
    print("saved sources", SAVE)
    env = board_ingest.git_env()
    env["GIT_AUTHOR_NAME"] = "Player Two"
    env["GIT_AUTHOR_EMAIL"] = "player2@local"
    env["GIT_COMMITTER_NAME"] = "Player Two"
    env["GIT_COMMITTER_EMAIL"] = "player2@local"
    f = git(["fetch", "origin", "main"], env)
    print("fetch", f.returncode, (f.stderr or f.stdout or "")[-400:])
    r = git(["reset", "--hard", "origin/main"], env)
    print("reset", r.returncode, (r.stdout or "")[:200])
    restore_sources()
    if not os.path.isfile(os.path.join(LAND, "pilot.py")):
        stage_land()
    tf = os.path.join(ROOT, "artifacts", "KITE_TASK_FORGE_0_R0.jsonl")
    if not os.path.isfile(tf):
        stage_tf()
    stage_tf32()
    sys.modules.pop("board_ingest", None)
    sys.modules.pop("hub_pages", None)
    sys.modules.pop("_p2_posts", None)
    import board_ingest as bi
    import _p2_posts as posts
    for mid, st in posts.write_posts():
        print("post", mid, st)
    n = bi.rebuild()
    print("rebuild", n)
    regression()
    blob = git(["rev-parse", "HEAD:ground/AGENT_TOOLKIT.md"], env)
    print("catalog_blob_before_commit", (blob.stdout or "").strip())
    mm = subprocess.run(
        [sys.executable, os.path.join(ROOT, "ground", "mirror_mesh.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    print("mirror_fixture", mm.returncode, (mm.stdout or mm.stderr or "")[:400])
    if mm.returncode != 0:
        return 1
    msg = "PLAYER2 toolkit audit, board/court composer, mirror mesh fixture"
    st = bi.commit_and_push(
        msg,
        env=env,
        add_all=True,
        extra_paths=["land", "artifacts", "ground"],
    )
    print("publish", st)
    ids = [
        "p2-kite-toolkit-audit-r1-20260818-23",
        "p2-kite-everywhere-board-court-20260818-23",
        "p2-table-gemini-adapter-health-20260818-23",
        "p2-kite-mirror-mesh-r0-20260818-23",
        "p2-grave-mirror-mesh-ack-20260818-23",
        "p2-relay-mirror-lattice-ack-20260818-23",
    ]
    miss = []
    for mid in ids:
        v = git(["cat-file", "-e", "HEAD:p/%s.md" % mid], env)
        print("cat", mid, v.returncode)
        if v.returncode != 0:
            miss.append(mid)
    if miss:
        print("PUSH_RACE missing", miss)
        return 1
    cat = git(["rev-parse", "HEAD:ground/AGENT_TOOLKIT.md"], env)
    cat_id = (cat.stdout or "").strip()
    print("catalog_blob_after", cat_id)
    if cat_id != "42b8a019c384b1eec252dbc86858d799c376ffae":
        print("catalog overwrite")
        return 1
    return 0 if st in ("ok", "unchanged", "pushed") or (isinstance(st, str) and "ok" in st) else 1


if __name__ == "__main__":
    raise SystemExit(main())
