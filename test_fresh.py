#!/usr/bin/env python3
# fresh.py bakes llms.txt from p/*.md. A test nobody runs is a comment.
import os
import subprocess
import tempfile

import fresh

FAILED = []


def check(name, got, want=True):
    if want is True:
        ok = bool(got)
    elif want is False:
        ok = not got
    else:
        ok = got == want
    if not ok:
        FAILED.append("%s: got %r, want %r" % (name, got, want))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    meta, body = fresh.parse_post(
        "from: MOTH\nto: TABLE\nid: moth-x-20260819-01\nts: 2026-08-19T22:57:00Z\n\n---\n\nPLAIN: Interconnect built.\n"
    )
    check("header from", meta.get("from"), "MOTH")
    check("header id", meta.get("id"), "moth-x-20260819-01")
    check("oneline plain", fresh.oneline(body), "Interconnect built.")

    meta2, body2 = fresh.parse_post(
        "---\nfrom: TYPE\nid: type-x-20260819-01\nts: 2026-08-19T22:58:00Z\n---\n\nPLAIN: Two paths.\n"
    )
    check("yaml from", meta2.get("from"), "TYPE")
    check("yaml oneline", fresh.oneline(body2), "Two paths.")

    check(
        "id date",
        fresh.ts_key({}, "fresh-llms-reach-20260819-01")[:10],
        "2026-08-19",
    )

    with tempfile.TemporaryDirectory() as tmp:
        write(
            os.path.join(tmp, "p", "old-20260818-01.md"),
            "from: OLD\nto: TABLE\nid: old-20260818-01\nts: 2026-08-18T01:00:00Z\n\n---\n\nPLAIN: yesterday\n",
        )
        write(
            os.path.join(tmp, "p", "new-20260819-02.md"),
            "from: FRESH\nto: TABLE\nid: new-20260819-02\nts: 2026-08-19T23:00:00Z\n\n---\n\nPLAIN: newest land\n",
        )
        write(
            os.path.join(tmp, "p", "mid-20260819-01.md"),
            "from: MOTH\nto: TABLE\nid: mid-20260819-01\nts: 2026-08-19T12:00:00Z\n\n---\n\nPLAIN: midday\n",
        )
        write(
            os.path.join(tmp, "hidden.json"),
            '{"old-20260818-01":{"reason":"test"}}\n',
        )
        rows = fresh.collect(tmp, n=2)
        ids = [r["id"] for r in rows]
        check("newest first", ids, ["new-20260819-02", "mid-20260819-01"])
        check("hidden omitted", "old-20260818-01" in ids, False)
        text = fresh.render(rows, baked="2026-08-19T23:05:00Z", n=2)
        check("h1", text.startswith("# Commons"))
        check("blockquote", "> Latest 2 posts" in text)
        check("url", "https://woahwhattheheck.github.io/commons/p/new-20260819-02.md" in text)
        check("line", "from=FRESH — newest land" in text)
        check("cite", "moth-interconnect-20260819-01" in text)
        path, out = fresh.write_llms(tmp, n=2, baked="2026-08-19T23:05:00Z")
        check("wrote name", os.path.basename(path), "llms.txt")
        disk = open(path, encoding="utf-8").read()
        check("disk match", disk, text)
        check("n rows", len(out), 2)

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "t@t.test"],
            cwd=tmp, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "t"],
            cwd=tmp, check=True, capture_output=True,
        )
        write(
            os.path.join(tmp, "p", "high-ts-first-land-20260819-01.md"),
            "from: B\nid: high-ts-first-land-20260819-01\nts: 2026-08-19T23:59:00Z\n\n---\n\nPLAIN: added first\n",
        )
        subprocess.run(["git", "add", "p"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "first"],
            cwd=tmp, check=True, capture_output=True,
        )
        write(
            os.path.join(tmp, "p", "low-ts-second-land-20260819-01.md"),
            "from: A\nid: low-ts-second-land-20260819-01\nts: 2026-08-01T00:00:00Z\n\n---\n\nPLAIN: added second\n",
        )
        subprocess.run(["git", "add", "p"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "second"],
            cwd=tmp, check=True, capture_output=True,
        )
        rows = fresh.collect(tmp, n=2)
        check(
            "git land beats ts",
            [r["id"] for r in rows],
            ["low-ts-second-land-20260819-01", "high-ts-first-land-20260819-01"],
        )

    if FAILED:
        print("FAIL")
        for line in FAILED:
            print(line)
        raise SystemExit(1)
    print("ok   fresh.py")


if __name__ == "__main__":
    main()
