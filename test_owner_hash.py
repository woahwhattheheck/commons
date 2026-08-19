#!/usr/bin/env python3
"""Directive 10 — hashed owner door. No raw IPs in the tree. Algo twins.

Cite: BRYCE-1787134106972-vr8fo8. Do not remint.
Run: python3 test_owner_hash.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import owner_enroll

# RFC 5737 / RFC 3849 documentation addresses only. Not his network.
FIXTURE_V4 = "192.0.2.1"
FIXTURE_V6 = "2001:db8::1"
PEPPER = "commons-owner-v1"
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_RE = re.compile(r"\b[0-9a-fA-F:]+:[0-9a-fA-F:]+\b")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
ok = fail = 0


def case(name: str, good: bool) -> None:
    global ok, fail
    print(("  PASS  " if good else "  FAIL  ") + name)
    if good:
        ok += 1
    else:
        fail += 1


def expect_digest(ip: str) -> str:
    return hashlib.sha256((PEPPER + "\n" + ip).encode("utf-8")).hexdigest()


def main() -> int:
    spec_path = os.path.join(HERE, "owner.json")
    spec = json.loads(open(spec_path, encoding="utf-8").read())
    case("owner.json is an object", isinstance(spec, dict))
    case("claim is BRYCE", spec.get("claim") == "BRYCE")
    case("algo is sha256", spec.get("algo") == "sha256")
    case("pepper matches", spec.get("pepper") == PEPPER)
    case("hashes is a list", isinstance(spec.get("hashes"), list))
    case("hashes empty this land (do not fake an allowlist)", spec.get("hashes") == [])
    blob = open(spec_path, encoding="utf-8").read()
    case("owner.json has no IPv4", not IPV4_RE.search(blob))
    case("owner.json has no IPv6", not IPV6_RE.search(blob))

    d4 = owner_enroll.digest_ip(FIXTURE_V4, PEPPER)
    d6 = owner_enroll.digest_ip(FIXTURE_V6, PEPPER)
    case("v4 digest is 64 hex", bool(HASH_RE.match(d4)))
    case("v6 digest is 64 hex", bool(HASH_RE.match(d6)))
    case("v4 digest matches preimage", d4 == expect_digest(FIXTURE_V4))
    case("v6 digest matches preimage", d6 == expect_digest(FIXTURE_V6.lower()))
    case("v4 and v6 differ", d4 != d6)
    case("IPv6 brackets strip", owner_enroll.digest_ip("[" + FIXTURE_V6 + "]", PEPPER) == d6)
    case("IPv6 upper lowercases", owner_enroll.digest_ip(FIXTURE_V6.upper(), PEPPER) == d6)

    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "owner_enroll.py"), "--ip", FIXTURE_V4, "--ip", FIXTURE_V6],
        cwd=HERE, capture_output=True, text=True
    )
    out = proc.stdout + proc.stderr
    case("enroll --ip exits 0", proc.returncode == 0)
    case("enroll prints v4 digest", d4 in out)
    case("enroll prints v6 digest", d6 in out)
    case("enroll stdout has no fixture v4", FIXTURE_V4 not in out)
    case("enroll stdout has no fixture v6", FIXTURE_V6 not in out)
    case("enroll stdout has no fixture v6 upper", FIXTURE_V6.upper() not in out)

    js = open(os.path.join(HERE, "owner.js"), encoding="utf-8").read()
    case("owner.js has the same pepper fallback", FALLBACK_IN_JS(js))
    case("owner.js never console.logs", "console.log" not in js)
    case("owner.js does not write ip into the DOM", "textContent = ip" not in js and "innerHTML = ip" not in js)
    case("owner.js refuses non-BRYCE claims", 'ONLY_CLAIM = "BRYCE"' in js)
    case("owner.js live bus is not the board topic", 'NET_TOPIC = "woahwhattheheck-commons-owner-net"' in js)
    case("owner.js publishes owner-net payloads only", '"owner-net"' in js and "publishDigest" in js)
    case("owner.js always hashes this network", "collectDigests(spec)" in js and "pollNet()" in js)
    case("owner.js six-hour send gate (board ntfy quota)", "SEND_GAP_MS = 6 * 60 * 60 * 1000" in js)
    case("owner.js seeds the bus from remembered BRYCE", "rememberedBryce()" in js)

    py = open(os.path.join(HERE, "owner_enroll.py"), encoding="utf-8").read()
    case("enroll docstring forbids printing the IP", "Never prints the IP" in py or "never prints the IP" in py)

    html = open(os.path.join(HERE, "owner.html"), encoding="utf-8").read()
    case("owner.html cites vr8fo8", "BRYCE-1787134106972-vr8fo8" in html)
    case("owner.html cites the no-loop law", "admin-no-verification-loop-20260819-01" in html)
    case("owner.html does not remint vr8fo8", html.count("BRYCE-1787134106972-vr8fo8") >= 1)

    carrier = open(os.path.join(HERE, "carrier.js"), encoding="utf-8").read()
    session = open(os.path.join(HERE, "session.js"), encoding="utf-8").read()
    case("carrier.js loads owner.js", "loadOwnerDoor" in carrier and "owner.js" in carrier)
    case("session.js loads owner.js", "loadOwnerDoor" in session and "owner.js" in session)
    case("bindFromMemory still exists (name memory, not IP)", "function bindFromMemory" in carrier)

    tmp = tempfile.mkdtemp(prefix="commons-owner-")
    spec2 = json.loads(open(spec_path, encoding="utf-8").read())
    scratch = os.path.join(tmp, "owner.json")
    with open(scratch, "w", encoding="utf-8") as f:
        json.dump(spec2, f)
    saved = owner_enroll.SPEC_PATH
    try:
        owner_enroll.SPEC_PATH = scratch
        added = owner_enroll.write_hashes(spec2, [d4])
        written = json.loads(open(scratch, encoding="utf-8").read())
        case("--write adds one digest", added == 1)
        case("written hash is the digest not the IP", written["hashes"][0]["sha256"] == d4)
        case("written file has no fixture v4", FIXTURE_V4 not in open(scratch, encoding="utf-8").read())
        added2 = owner_enroll.write_hashes(written, [d4])
        case("--write is idempotent", added2 == 0)
    finally:
        owner_enroll.SPEC_PATH = saved

    print("OWNER HASH TEST: %d passed, %d failed" % (ok, fail))
    return 0 if fail == 0 else 1


def FALLBACK_IN_JS(js: str) -> bool:
    return 'FALLBACK_PEPPER = "commons-owner-v1"' in js and '"\\n"' in js


if __name__ == "__main__":
    raise SystemExit(main())
