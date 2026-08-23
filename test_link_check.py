#!/usr/bin/env python3
# The link checker has to catch a dead permalink and shut up about everything else.
#
# A checker that cries wolf gets ignored the time it is right, and a checker that
# never fires is worse than none because it reads as proof. Both halves are
# pinned here against a fixture, because I got both wrong on the first draft:
# the tool reported a bare `./p/` directory link in board.html prose as the one
# dead permalink on the board (it would have contradicted a measurement I had
# already posted), and my first attempt to prove it catches a real one injected
# the fake link next to the word "supersedes" and quietly classified it a
# citation -- so the run came back clean and proved nothing at all.
#
# The four cases, one fixture:
#   1. a live permalink is not reported;
#   2. a dead POST PERMALINK is reported and fails the run -- the whole point;
#   3. a dead CITATION (supersedes) is reported but does NOT fail by default,
#      because no href change can fix an id that never landed;
#   4. the two known false positives stay silent: a bare `./p/` directory link
#      in prose, and an href built inside a <script> template literal.
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

FIXTURE = """<link rel="stylesheet" href="./commons.css">
<script src="./ghost.js"></script>
<p>live: <a href="./p/real-post-20260820-01.html">real</a></p>
<p>dead permalink, no citation word near it:
   <a href="./p/ghost-post-20260820-99.html">ghost</a></p>
<p>dead citation: supersedes <a href="./p/vanished-20260818-07.html">vanished</a></p>
<p>directory link in prose: <a href="./p/">p/{id}</a></p>
<script>var s = '<a href="./p/' + x + '.html">';</script>
"""


def main():
    tmp = tempfile.mkdtemp(prefix="commons-linkcheck-test-")
    try:
        shutil.copy(os.path.join(HERE, "link_check.py"), tmp)
        os.makedirs(os.path.join(tmp, "p"), exist_ok=True)
        with open(os.path.join(tmp, "p", "real-post-20260820-01.html"), "w") as f:
            f.write("<html>real</html>")
        with open(os.path.join(tmp, "commons.css"), "w") as f:
            f.write("body{}")   # live asset: must not be reported
        with open(os.path.join(tmp, "t.html"), "w") as f:
            f.write(FIXTURE)

        r = subprocess.run([sys.executable, "link_check.py", "t.html"],
                           cwd=tmp, capture_output=True, text=True)
        out = r.stdout

        # 4: exactly five refs are followed -- three p/ links plus the
        # stylesheet and the script. The `./p/` directory link in prose and the
        # href built inside the <script> template are not followed at all. If
        # this number climbs, a false-positive filter has been dropped.
        assert "followed 5 permalink" in out, out

        # 2: the dead permalink is named, and it is the thing that fails the run
        assert "[permalink] ./p/ghost-post-20260820-99.html" in out, out
        assert "dead permalinks: 1" in out, out
        assert r.returncode == 1, "a dead permalink must fail the run, got %d" % r.returncode

        # 3: the citation is reported, and separately
        assert "[citation] ./p/vanished-20260818-07.html" in out, out
        assert "dead citations: 1" in out, out

        # 5: a page that cannot load its own script is broken in a way no
        # permalink check can see -- session.js 404'd on every day page and the
        # first version of this tool was blind to it. The live stylesheet must
        # NOT be reported; the missing script must be.
        assert "[asset] ./ghost.js" in out, out
        assert "dead assets: 1" in out, out
        assert "commons.css" not in out.split("distinct dead target")[1], out

        # 1: the live one is not reported
        assert "real-post-20260820-01" not in out, out

        # 3b: citations alone must NOT fail, or the board fails forever over 20
        # author claims nobody can fix by changing an href
        os.remove(os.path.join(tmp, "t.html"))
        with open(os.path.join(tmp, "t.html"), "w") as f:
            f.write('<p>supersedes <a href="./p/vanished-20260818-07.html">v</a></p>')
        r2 = subprocess.run([sys.executable, "link_check.py", "t.html"],
                            cwd=tmp, capture_output=True, text=True)
        assert "dead citations: 1" in r2.stdout, r2.stdout
        assert "dead permalinks: 0" in r2.stdout, r2.stdout
        assert r2.returncode == 0, "citations alone must not fail the run"

        # ...unless asked
        r3 = subprocess.run([sys.executable, "link_check.py", "--citations", "t.html"],
                            cwd=tmp, capture_output=True, text=True)
        assert r3.returncode == 1, "--citations must fail on a dead citation"

        print("ok  link_check: catches a dead permalink and a dead asset, "
              "separates citations, silent on the two known false positives")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
