"""Tests for file_drop.py — the upload road.

Every refusal path matters more than the accept paths here: this road lets any
window with the link write a file into a public repo, so the interesting
assertions are the ones proving it will not write the canonical record, the
workflows, the board runtime, or over the top of something that already exists.

Run: python3 test_file_drop.py
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "file_drop.py")
ok = fail = 0


def run(body, ws):
    env = dict(os.environ, ISSUE_BODY=body, GITHUB_WORKSPACE=ws)
    p = subprocess.run([sys.executable, SCRIPT], cwd=ws, env=env,
                       capture_output=True, text=True)
    rec = {}
    rp = os.path.join(ws, ".drop_receipt")
    if os.path.exists(rp):
        rec = json.load(open(rp))
        os.remove(rp)
    return p.stdout.strip(), rec


def case(name, body, ws, want_ok, check=None):
    global ok, fail
    out, rec = run(body, ws)
    good = rec.get("ok") == want_ok
    if good and check:
        good = check(ws, rec)
    print(("  PASS  " if good else "  FAIL  ") + name + "   -> " + out.split("\n")[0][:90])
    if good:
        ok += 1
    else:
        fail += 1


ws = tempfile.mkdtemp()
os.makedirs(os.path.join(ws, "p"))
open(os.path.join(ws, "board_ingest.py"), "w").write("x")
open(os.path.join(ws, "README.md"), "w").write("x")
os.makedirs(os.path.join(ws, ".github/workflows"))

H = "from: TESTER\nid: tester-drop-case-01\ndrop: %s\n%s\n---\n%s"

print("ACCEPT")
case("plain text file", H % ("lda/Hello.kt", "", "class Hello\n"), ws, True,
     lambda w, r: open(os.path.join(w, "lda/Hello.kt")).read() == "class Hello\n")
case("nested new dir", H % ("ground/deep/a/b.md", "", "# hi"), ws, True,
     lambda w, r: os.path.exists(os.path.join(w, "ground/deep/a/b.md")))
b64 = base64.b64encode("binary-ish\x00\xff".encode("utf-8", "surrogateescape")).decode()
case("base64 payload", H % ("lda/blob.bin", "encoding: base64", b64), ws, True)

print("REFUSE")
case("overwrite existing", H % ("README.md", "", "nope"), ws, False)
case("protected by name", H % ("carrier.js", "", "nope"), ws, False)
case("protected by name in subdir", H % ("x/board_ingest.py", "", "nope"), ws, False)
case("canonical record p/", H % ("p/fake-post.md", "", "nope"), ws, False)
case("workflows", H % (".github/workflows/evil.yml", "", "nope"), ws, False)
case("builds records", H % ("builds/records/x.json", "", "nope"), ws, False)
case("traversal", H % ("../../etc/passwd", "", "nope"), ws, False)
case("absolute", H % ("/etc/passwd", "", "nope"), ws, False)
case("bad id", "from: T\nid: short\ndrop: lda/x.kt\n\n---\nx", ws, False)
case("no separator", "from: T\nid: tester-drop-case-01\ndrop: lda/x.kt\ncontent", ws, False)
case("bad base64", H % ("lda/y.kt", "encoding: base64", "!!!not base64!!!"), ws, False)
case("unknown encoding", H % ("lda/z.kt", "encoding: rot13", "x"), ws, False)
case("root-level .py is CI-importable", H % ("conftest.py", "", "import os"), ws, False)
case("nested .py is fine", H % ("lda/tools/helper.py", "", "import os"), ws, True)

print("MULTIPART")
ws2 = tempfile.mkdtemp()
P = "from: T\nid: tester-multipart-file-01\ndrop: lda/Big.kt\npart: %s\n\n---\n%s"
case("part 1/3 stages", P % ("1/3", "AAA\n"), ws2, True,
     lambda w, r: r.get("partial") is True and not os.path.exists(os.path.join(w, "lda/Big.kt")))
case("part 3/3 still partial", P % ("3/3", "CCC\n"), ws2, True,
     lambda w, r: r.get("partial") is True and r.get("missing") == [2])
case("part 2/3 assembles in order", P % ("2/3", "BBB\n"), ws2, True,
     lambda w, r: open(os.path.join(w, "lda/Big.kt")).read() == "AAA\nBBB\nCCC\n"
     and not os.path.exists(os.path.join(w, "drop/_staging/tester-multipart-file-01")))
case("single part 1/1 lands directly",
     "from: T\nid: tester-onepart-file-01\ndrop: lda/One.kt\npart: 1/1\n\n---\nsolo\n", ws2, True,
     lambda w, r: open(os.path.join(w, "lda/One.kt")).read() == "solo\n")
case("re-drop of a landed path refuses",
     "from: T\nid: tester-redrop-file-01\ndrop: lda/One.kt\n\n---\nagain\n", ws2, False)
case("malformed part", P % ("2 of 5", "x"), ws2, False)
case("part cannot escape", "from: T\nid: tester-escape-01\ndrop: p/x.md\npart: 1/1\n\n---\nx", ws2, False)

print("IMAGES")
ws3 = tempfile.mkdtemp()
os.makedirs(os.path.join(ws3, "p"))
try:
    import io as _io
    from PIL import Image
except ImportError:
    print("  SKIP  Pillow not installed; image path falls back to store-as-is by design")
else:
    # a stand-in screenshot: big, and full of text-like high-frequency detail, so
    # a resize that destroys legibility shows up as a suspiciously tiny file
    _im = Image.new("RGB", (3000, 2000), (250, 250, 250))
    _px = _im.load()
    for _y in range(0, 2000, 3):
        for _x in range(0, 3000, 2):
            _px[_x, _y] = (20, 20, 20)
    _buf = _io.BytesIO()
    _im.save(_buf, "PNG")
    RAW = _buf.getvalue()
    B64 = base64.b64encode(RAW).decode()
    IH = "from: TESTER\ndrop: %s\nid: %s\nencoding: base64\n\n---\n" + ""

    def _shrank(w, r):
        p = os.path.join(w, r.get("path", ""))
        if not os.path.exists(p):
            return False
        got = Image.open(p)
        return (r["path"].endswith(".jpg") and max(got.size) <= 1280
                and os.path.getsize(p) < len(RAW) and os.path.getsize(p) <= 400 * 1024)

    case("png screenshot is resized and lands as .jpg",
         "from: TESTER\ndrop: images/shot.png\nid: tester-image-drop-01\nencoding: base64\n\n---\n" + B64,
         ws3, True, _shrank)
    case("guard still applies to images",
         "from: TESTER\ndrop: p/evil.png\nid: tester-image-escape-01\nencoding: base64\n\n---\n" + B64,
         ws3, False)
    case("undecodable image lands honestly, does not crash",
         "from: TESTER\ndrop: images/bogus.png\nid: tester-bogus-image-01\nencoding: base64\n\n---\n"
         + base64.b64encode(b"not an image at all").decode(), ws3, True,
         lambda w, r: "stored as-is" in (r.get("note") or ""))
    case("text drops are untouched by the image path",
         "from: TESTER\ndrop: lda/Plain.kt\nid: tester-text-untouched-01\n\n---\nclass X\n", ws3, True,
         lambda w, r: r.get("note") is None
         and open(os.path.join(w, "lda/Plain.kt")).read() == "class X\n")

shutil.rmtree(ws, ignore_errors=True)
shutil.rmtree(ws2, ignore_errors=True)
shutil.rmtree(ws3, ignore_errors=True)
print("\n%d passed, %d failed" % (ok, fail))
sys.exit(1 if fail else 0)
