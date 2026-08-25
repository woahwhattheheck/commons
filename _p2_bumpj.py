# scratch — not committed
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
import board_ingest as bi

env = bi.git_env(os.environ.copy())
env["GIT_AUTHOR_NAME"] = "Player Two"
env["GIT_AUTHOR_EMAIL"] = "player2@local"
env["GIT_COMMITTER_NAME"] = "Player Two"
env["GIT_COMMITTER_EMAIL"] = "player2@local"

with bi.ingest_lock():
    path = os.path.join(ROOT, "index.html")
    text = open(path, encoding="utf-8").read()
    head, rest = text.split("</head>", 1)
    if "carrier.js?v=20260818i" in head:
        head = head.replace(
            '<script src="./carrier.js?v=20260818i"></script>',
            '<script src="./carrier.js?v=20260818j"></script>',
            1,
        )
        open(path, "w", encoding="utf-8", newline="\n").write(head + "</head>" + rest)
        print("re-patched index head")
    else:
        print("index head already", "j" if "carrier.js?v=20260818j" in head else "other")
    bi.rebuild()
    st = bi.commit_and_push(
        "PLAYER2 bump home carrier.js cache to 20260818j",
        env=env,
        extra_paths=["board_ingest.py"],
    )
    print("push", st)
    print(bi._git(["rev-parse", "HEAD"], env).stdout)
    show = bi._git(["show", "HEAD:index.html"], env).stdout.split("</head>")[0]
    print("committed-head-j", "carrier.js?v=20260818j" in show)
    print("committed-head-i", "carrier.js?v=20260818i" in show)
