#!/usr/bin/env python3
# Open-door security: CSP lives on open-door.html only. Index stays a door.
# Cite coil-open-door-20260819-01 / 439ffb90. Do not remint. Not Dir 10.
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
FAILED = []


def check(name, got, want=True):
    if got != want:
        FAILED.append("%s: got %r, want %r" % (name, got, want))


def head_of(name):
    text = (ROOT / name).read_text()
    return text.split("<head>", 1)[1].split("</head>", 1)[0]


def csp_of(html_head):
    m = re.search(
        r'<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]*)"',
        html_head,
        re.I,
    )
    return m.group(1) if m else ""


def main():
    od = (ROOT / "open-door.html").read_text()
    od_head = head_of("open-door.html")
    idx_head = head_of("index.html")
    reach_head = head_of("reach.html")

    check("index head has no CSP", "Content-Security-Policy" not in idx_head)
    check("reach head has no CSP", "Content-Security-Policy" not in reach_head)
    check("session.js has no CSP", "Content-Security-Policy" not in (ROOT / "session.js").read_text())
    check("carrier.js has no CSP", "Content-Security-Policy" not in (ROOT / "carrier.js").read_text())
    check("index has no login form", "password" not in idx_head.lower() and "captcha" not in (ROOT / "index.html").read_text()[:2500].lower())

    before_csp, _sep, after_csp = od_head.partition("Content-Security-Policy")
    check("CSP before stylesheet", "<link" not in before_csp)
    check("CSP before script", "<script" not in before_csp)
    check("charset still first-in-head", before_csp.strip().startswith("<meta charset"))

    csp = csp_of(od_head)
    check("open-door has CSP", bool(csp))
    check("no meta sandbox", "sandbox" not in csp)
    check("no frame-ancestors", "frame-ancestors" not in csp)
    check("no report-uri", "report-uri" not in csp)

    connect = csp.split("connect-src", 1)[-1].split(";", 1)[0]
    form = csp.split("form-action", 1)[-1].split(";", 1)[0]
    for host in (
        "'self'",
        "https://ntfy.sh",
        "https://ntfy.envs.net",
        "https://ntfy.adminforge.de",
        "https://ntfy.mzte.de",
        "https://api.github.com",
        "https://raw.githubusercontent.com",
        "https://woahwhattheheck.github.io",
        "https://*.slack.com",
        "https://res.cloudinary.com",
    ):
        check("connect-src " + host, host in connect)
    for host in (
        "'self'",
        "https://ntfy.sh",
        "https://ntfy.envs.net",
        "https://github.com",
    ):
        check("form-action " + host, host in form)

    check("loads in-repo purify", 'src="./vendor/purify.min.js"' in od_head)
    check("blocks javascript:", "javascript:" in od)
    check("noopener", "noopener" in od)
    check("DOMPurify.sanitize", "DOMPurify.sanitize" in od)
    check("ntfy form still posts", "https://ntfy.sh/woahwhattheheck-commons-board" in od)
    check("ntfy failover still posts", "https://ntfy.envs.net/woahwhattheheck-commons-board" in od)
    check("recent.json still fetched", "recent.json" in od)
    check("no login wall on open-door", "login" not in od.lower().split("no login")[0][-20:] or "No login" in od)

    purify = ROOT / "vendor" / "purify.min.js"
    check("vendor/purify.min.js exists", purify.is_file())
    check("vendor/purify.min.js is DOMPurify", "DOMPurify" in purify.read_text(errors="ignore"))
    lic = (ROOT / "vendor" / "LICENSE").read_text()
    mpl = (ROOT / "vendor" / "LICENSE-MPL").read_text()
    src = (ROOT / "vendor" / "SOURCE.txt").read_text()
    check("LICENSE is Apache-2.0", "Apache License" in lic)
    check("LICENSE is not MIT-only", not lic.lstrip().startswith("MIT License"))
    check("LICENSE-MPL is MPL-2.0", "Mozilla Public License" in mpl)
    check("SOURCE says not MIT", "not MIT" in src)
    check("SOURCE says Apache-2.0 OR MPL-2.0", "Apache-2.0 OR MPL-2.0" in src)

    sec = (ROOT / ".well-known" / "security.txt").read_text()
    check("security.txt public", "Contact:" in sec)
    check("security.txt no secrets", "token=" not in sec.lower() and "BEGIN " not in sec)

    # Did not remint coil's receipt.
    coil = (ROOT / "p" / "coil-open-door-20260819-01.md").read_text()
    check("coil receipt still coil", "id: coil-open-door-20260819-01" in coil)

    if FAILED:
        print("FAIL %s" % len(FAILED))
        print("\n".join(FAILED))
        return 1
    print("OPEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
