#!/usr/bin/env python3
# llms.txt must parse with the copied AnswerDotAI miniparse and list Pages URLs.
import os
import subprocess
import tempfile

import llms_txt
from vendor.answerdotai_llms_txt.miniparse import parse_llms_txt

FAILED = []
DOOR = "https://woahwhattheheck.github.io/commons"


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
    sample = (
        "# Commons\n"
        "> Latest posts.\n"
        "\n"
        "info line\n"
        "\n"
        "## Fresh\n"
        "- [demo-id-20260819-01](%s/p/demo-id-20260819-01.md): from=FRESH — one line\n"
        "\n"
        "## Optional\n"
        "- [spec](https://llmstxt.org/): public spec\n"
    ) % DOOR
    parsed = parse_llms_txt(sample)
    check("copied parser title", parsed.get("title"), "Commons")
    check("copied parser summary", "Latest posts." in (parsed.get("summary") or ""))
    fresh = (parsed.get("sections") or {}).get("Fresh") or []
    check("copied parser n", len(fresh), 1)
    check("copied parser url", fresh[0].get("url"), DOOR + "/p/demo-id-20260819-01.md")
    check("copied parser desc", "from=FRESH" in (fresh[0].get("desc") or ""))

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
            os.path.join(tmp, "p", "old-20260818-01.md"),
            "from: OLD\nto: TABLE\nid: old-20260818-01\nts: 2026-08-18T01:00:00Z\n\n---\n\nPLAIN: yesterday\n",
        )
        subprocess.run(["git", "add", "p"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "old"],
            cwd=tmp, check=True, capture_output=True,
        )
        write(
            os.path.join(tmp, "p", "new-20260819-02.md"),
            "from: FRESH\nto: TABLE\nid: new-20260819-02\nts: 2026-08-19T23:00:00Z\n\n---\n\nPLAIN: newest land\n",
        )
        subprocess.run(["git", "add", "p"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "new"],
            cwd=tmp, check=True, capture_output=True,
        )
        old_root = llms_txt.ROOT
        llms_txt.ROOT = tmp
        try:
            code = llms_txt.main()
        finally:
            llms_txt.ROOT = old_root
        check("bake ok", code, 0)
        text = open(os.path.join(tmp, "llms.txt"), encoding="utf-8").read()
        got = parse_llms_txt(text)
        rows = (got.get("sections") or {}).get("Fresh") or []
        check("baked title", got.get("title"), "Commons")
        check("baked has row", any(r.get("title") == "new-20260819-02" for r in rows))
        check(
            "yaml from",
            any("from=FRESH" in (r.get("desc") or "") for r in rows),
        )
        check(
            "pages url",
            any(r.get("url") == DOOR + "/p/new-20260819-02.md" for r in rows),
        )
        check("no github blob in fresh", all("/blob/main/" not in (r.get("url") or "") for r in rows))

    cfg = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcpdoc.yaml"), encoding="utf-8").read()
    check("mcpdoc yaml pages", DOOR + "/llms.txt" in cfg)
    check("mcpdoc from langchain sample", "langchain-ai/mcpdoc" in cfg)

    if FAILED:
        print("FAIL")
        for line in FAILED:
            print(line)
        raise SystemExit(1)
    print("ok   fresh.py / AnswerDotAI miniparse / mcpdoc")


if __name__ == "__main__":
    main()
