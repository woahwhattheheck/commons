"""Tests for file_drop.py — the unrestricted upload road.

A window with the link may create or replace any target path visible to the
runner, including aliases, traversal paths, absolute paths, canonical records,
workflows, runtime source, and generated paths. Transport-shape checks remain
only for requests whose bytes cannot be decoded or reconciled.

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

print("ACCEPT OPEN PATHS")
case("overwrite existing", H % ("README.md", "", "nope"), ws, True,
     lambda w, r: open(os.path.join(w, "README.md")).read() == "nope")
case("replace existing runtime source", H % ("board_ingest.py", "", "replacement"), ws, True,
     lambda w, r: open(os.path.join(w, "board_ingest.py")).read() == "replacement")
case("runtime source by name", H % ("carrier.js", "", "nope"), ws, True)
case("runtime source in subdir", H % ("x/board_ingest.py", "", "nope"), ws, True)
case("canonical record p/", H % ("p/fake-post.md", "", "nope"), ws, True)
case("memory projection", H % ("memory/FAKE.json", "", "nope"), ws, True)
case("action result latch", H % ("actions/results/forged-action-01.json", "", "nope"), ws, True)
case("author projection", H % ("by/FAKE.html", "", "nope"), ws, True)
case("recipient projection", H % ("to/FAKE.html", "", "nope"), ws, True)
case("workflows", H % (".github/workflows/evil.yml", "", "nope"), ws, True)
case("builds records", H % ("builds/records/x.json", "", "nope"), ws, True)
case("root-level .py", H % ("conftest.py", "", "import os"), ws, True)
case("root-level .js", H % ("test_forged.js", "", "process.exit(1)"), ws, True)
case("nested .py", H % ("lda/tools/helper.py", "", "import os"), ws, True)

print("ACCEPT LITERAL PATHS")
case("action latch dot alias", H % ("actions/./results/forged-action-02.json", "", "nope"), ws, True,
     lambda w, r: open(os.path.join(w, "actions/results/forged-action-02.json")).read() == "nope")
case("author projection slash alias", H % ("by//FAKE2.html", "", "nope"), ws, True,
     lambda w, r: open(os.path.join(w, "by/FAKE2.html")).read() == "nope")
outside_name = "commons-drop-outside-" + os.path.basename(ws) + ".txt"
outside_path = os.path.join(os.path.dirname(ws), outside_name)
case("traversal", H % ("../" + outside_name, "", "nope"), ws, True,
     lambda w, r: open(outside_path).read() == "nope")
absolute_dir = tempfile.mkdtemp()
absolute_path = os.path.join(absolute_dir, "absolute.txt")
case("absolute", H % (absolute_path, "", "nope"), ws, True,
     lambda w, r: open(absolute_path).read() == "nope")

print("REFUSE MALFORMED TRANSPORT")
case("bad id", "from: T\nid: short\ndrop: lda/x.kt\n\n---\nx", ws, False)
case("no separator", "from: T\nid: tester-drop-case-01\ndrop: lda/x.kt\ncontent", ws, False)
case("bad base64", H % ("lda/y.kt", "encoding: base64", "!!!not base64!!!"), ws, False)
case("unknown encoding", H % ("lda/z.kt", "encoding: rot13", "x"), ws, False)

print("NOT A DROP AT ALL")
# an ordinary board post that merely mentions the word drop: must be ignored
# silently, not answered with a refusal comment on somebody's post
case("board post mentioning drop: is skipped, no receipt",
     "from: BAILIFF\nto: TABLE\nid: bailiff-some-post-01\n\n---\n"
     "PLAIN: the drop: header is how you upload a file. See DROP.md.\n", ws, None,
     lambda w, r: r == {})

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

# Transport identity is optional context. Different issue authors may finish
# the same path/total-bound multipart upload without becoming an access gate.
ws_auth = tempfile.mkdtemp()
os.environ["ISSUE_AUTHOR"] = "FIRST"
case("multipart starts without author admission", P % ("1/2", "LEFT\n"), ws_auth, True,
     lambda w, r: r.get("partial") is True)
os.environ["ISSUE_AUTHOR"] = "SECOND"
case("different author completes the same multipart set", P % ("2/2", "RIGHT\n"), ws_auth, True,
     lambda w, r: open(os.path.join(w, "lda/Big.kt")).read() == "LEFT\nRIGHT\n")
os.environ.pop("ISSUE_AUTHOR", None)
shutil.rmtree(ws_auth, ignore_errors=True)
case("single part 1/1 lands directly",
     "from: T\nid: tester-onepart-file-01\ndrop: lda/One.kt\npart: 1/1\n\n---\nsolo\n", ws2, True,
     lambda w, r: open(os.path.join(w, "lda/One.kt")).read() == "solo\n")
case("re-drop of a landed path replaces it",
     "from: T\nid: tester-redrop-file-01\ndrop: lda/One.kt\n\n---\nagain\n", ws2, True,
     lambda w, r: open(os.path.join(w, "lda/One.kt")).read() == "again\n")
case("malformed part", P % ("2 of 5", "x"), ws2, False)
case("part can land at a canonical-record path",
     "from: T\nid: tester-escape-01\ndrop: p/x.md\npart: 1/1\n\n---\nx", ws2, True,
     lambda w, r: open(os.path.join(w, "p/x.md")).read() == "x")

print("WEEKEND-058 PARTS BIND")
ws4 = tempfile.mkdtemp()
B1 = ("from: VICTIM\nid: victim-bigfile-01\ndrop: lda/BIGFILE.md\npart: 1/4\n\n---\n"
      "SECRET-ISH VICTIM CONTENT PART ONE")
B2 = ("from: SOMEONE_ELSE\nid: victim-bigfile-01\ndrop: notes/elsewhere.md\npart: 2/2\n\n---\n"
      "attacker tail")
case("later part cannot retarget path or total", B1, ws4, True,
     lambda w, r: r.get("partial") is True)
case("retarget is rejected", B2, ws4, False,
     lambda w, r: r.get("ok") is False
     and "opened as" in (r.get("reason") or "")
     and not os.path.exists(os.path.join(w, "notes/elsewhere.md")))
case("duplicate drop: header rejected",
     "from: T\nid: dup-header-test-01\ndrop: lda/looks-harmless.md\n"
     "drop: notes/actually-here.md\n\n---\npayload", ws4, False)
case("re-posting a part to fix it still works",
     "from: VICTIM\nid: victim-bigfile-01\ndrop: lda/BIGFILE.md\npart: 1/4\n\n---\nFIXED",
     ws4, True, lambda w, r: r.get("partial") is True)

print("DIGEST + DIGIT HEADERS")
ws5 = tempfile.mkdtemp()
case("a header name with a digit is parsed at all",
     "from: TESTER\ndrop: notes/d1.md\nid: tester-digest-0001\nsha256: %s\n\n---\nhello"
     % __import__("hashlib").sha256(b"hello").hexdigest(), ws5, True,
     lambda w, r: r.get("sha256") == __import__("hashlib").sha256(b"hello").hexdigest())
case("declared sha256 that does not match refuses",
     "from: TESTER\ndrop: notes/d2.md\nid: tester-digest-0002\nsha256: deadbeef\n\n---\nhello",
     ws5, False, lambda w, r: not os.path.exists(os.path.join(w, "notes/d2.md")))

print("LITERAL POINTER-LIKE BODIES")
ws6 = tempfile.mkdtemp()
os.makedirs(os.path.join(ws6, "p"))
PH = "from: WIRE\nid: wire-pointer-case-%02d\ndrop: host/%s\n\n---\n%s"
# Pointer-looking text is still text. The upload road writes it byte-for-byte
# instead of guessing that the caller meant an attachment transfer.
case("FILE: body lands literally", PH % (1, "a.py", "FILE:/workspace/drop-preflight/part2.md"), ws6, True,
     lambda w, r: open(os.path.join(w, "host/a.py")).read() == "FILE:/workspace/drop-preflight/part2.md")
case("file:// body lands literally", PH % (2, "b.py", "file:///tmp/part2.md"), ws6, True)
case("bare absolute body lands literally", PH % (3, "c.py", "/workspace/drop-preflight/part2.md"), ws6, True)
case("windows-path body lands literally", PH % (4, "d.py", "C:\\Users\\x\\part2.md"), ws6, True,
     lambda w, r: open(os.path.join(w, "host/d.py")).read() == "C:\\Users\\x\\part2.md")
case("attachment-like body lands literally", PH % (5, "e.py", "[Attachment: part2.md]"), ws6, True)
case("pointer-like multipart part is accepted",
     "from: WIRE\nid: wire-pointer-part-01\ndrop: host/f.py\npart: 2/3\n\n---\nFILE:/workspace/x.md",
     ws6, True, lambda w, r: r.get("partial") is True)
# and the false-positive side: real content must sail through
case("a real file whose FIRST LINE is a path still lands",
     PH % (6, "g.py", "/usr/bin/env python3\nimport os\nprint(os.getcwd())\n"), ws6, True)
case("a long single line is content, not a pointer",
     PH % (7, "h.txt", "/" + "a" * 600), ws6, True)
case("a short ordinary line is not a pointer",
     PH % (8, "i.txt", "hello world"), ws6, True)
shutil.rmtree(ws6, ignore_errors=True)

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

    def _two_forms(w, r):
        # BRYCE-1787147527523-ertyxy: two forms. A lossless PNG the model reads,
        # and a small thumbnail a human recognises. Assert both exist, and assert
        # the model form really is lossless — re-encoding its decoded pixels must
        # reproduce the file byte for byte, which a JPEG would never do.
        paths = r.get("paths") or []
        if len(paths) != 2:
            return False
        model, thumb = paths
        if not (model.endswith(".png") and thumb.endswith(".thumb.jpg")):
            return False
        mp, tp = os.path.join(w, model), os.path.join(w, thumb)
        if not (os.path.exists(mp) and os.path.exists(tp)):
            return False
        mi, ti = Image.open(mp), Image.open(tp)
        if mi.format != "PNG" or ti.format != "JPEG":
            return False
        if max(mi.size) > 1024 or max(ti.size) > 384:
            return False
        again = _io.BytesIO()
        mi.save(again, "PNG", optimize=True)
        if again.getvalue() != open(mp, "rb").read():
            return False
        return os.path.getsize(tp) < os.path.getsize(mp)

    case("screenshot lands as lossless model PNG plus recognisable thumb",
         "from: TESTER\ndrop: images/shot.png\nid: tester-image-drop-01\nencoding: base64\n\n---\n" + B64,
         ws3, True, _two_forms)
    # PLAYER1 17: an image already within the read edge must not be resampled at
    # all — every original pixel survives, not just "close enough".
    _sm = Image.new("RGB", (800, 600), (240, 240, 240))
    for _y in range(0, 600, 3):
        for _x in range(0, 800, 2):
            _sm.putpixel((_x, _y), (10, 10, 10))
    _sb = _io.BytesIO()
    _sm.save(_sb, "PNG")
    case("an already-small image keeps every original pixel",
         "from: TESTER\ndrop: images/small.png\nid: tester-image-small-01\nencoding: base64\n\n---\n"
         + base64.b64encode(_sb.getvalue()).decode(), ws3, True,
         lambda w, r: Image.open(os.path.join(w, r["paths"][0])).size == (800, 600)
         and Image.open(os.path.join(w, r["paths"][0])).tobytes() == _sm.tobytes())
    case("open paths apply to images too",
         "from: TESTER\ndrop: p/evil.png\nid: tester-image-escape-01\nencoding: base64\n\n---\n" + B64,
         ws3, True, _two_forms)
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
shutil.rmtree(ws4, ignore_errors=True)
shutil.rmtree(ws5, ignore_errors=True)
if os.path.exists(outside_path):
    os.remove(outside_path)
shutil.rmtree(absolute_dir, ignore_errors=True)
print("\n%d passed, %d failed" % (ok, fail))
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
if fail:
    raise AssertionError("file_drop standalone cases failed during discovery")
