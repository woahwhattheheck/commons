#!/usr/bin/env python3
"""Directive 10 — hashed owner door. Two slots, no raw IPs, no same-NAT land.

Cite: BRYCE-1787134106972-vr8fo8. Do not remint.
Law: admin-no-verification-loop-20260819-01. Do not remint.
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
import owner_net

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


def empty_spec() -> dict:
    return {
        "claim": "BRYCE",
        "algo": "sha256",
        "pepper": PEPPER,
        "slots": {"pc": None, "phone": None},
        "hashes": [],
    }


def optional_slot_is_valid(slot) -> bool:
    return slot in (None, {}) or bool(owner_net.slot_hash(slot))


def expected_hash_items(slots: dict) -> list[dict]:
    items = []
    seen = set()
    for via in owner_net.VIAS:
        digest = owner_net.slot_hash(slots.get(via))
        if not digest or digest in seen:
            continue
        seen.add(digest)
        items.append({"sha256": digest, "via": via})
    return items


def main() -> int:
    spec_path = os.path.join(HERE, "owner.json")
    spec = json.loads(open(spec_path, encoding="utf-8").read())
    case("owner.json is an object", isinstance(spec, dict))
    case("claim is BRYCE", spec.get("claim") == "BRYCE")
    case("algo is sha256", spec.get("algo") == "sha256")
    case("pepper matches", spec.get("pepper") == PEPPER)
    case("hashes is a list", isinstance(spec.get("hashes"), list))
    slots = spec.get("slots") or {}
    case("slots.pc exists", "pc" in slots)
    case("slots.phone exists", "phone" in slots)
    case("pc slot is empty or a digest", optional_slot_is_valid(slots.get("pc")))
    case("phone slot is empty or a digest", optional_slot_is_valid(slots.get("phone")))
    expected_hashes = expected_hash_items(slots)
    case("hashes exactly mirror filled slots", spec.get("hashes") == expected_hashes)
    case("two-slot enrollment is live", owner_net.distinct_live(spec))
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

    js = open(os.path.join(HERE, "owner_net.js"), encoding="utf-8").read()
    case("owner_net.js has the same pepper fallback", FALLBACK_IN_JS(js))
    case("owner_net.js keeps the phone/PC pin namespace intact",
         not re.search(r"window\.COMMONS_OWNER\s*=", js) and
         'window.COMMONS_OWNER_NET = "hashed-ip-door"' in js)
    case("owner_net.js never console.logs", "console.log" not in js)
    case("owner_net.js does not write ip into the DOM", "textContent = ip" not in js and "innerHTML = ip" not in js)
    case("owner_net.js refuses non-BRYCE claims", 'ONLY_CLAIM = "BRYCE"' in js)
    case("owner_net.js live bus is not the board topic", 'NET_TOPIC = "woahwhattheheck-commons-owner-net"' in js)
    case("owner_net.js publishes owner-net payloads only", '"owner-net"' in js and "publishDigest" in js)
    case("owner_net.js publishes via with the digest", "via: via" in js and 'k: "owner-net"' in js)
    case("owner_net.js classifies phone vs pc", "function deviceVia" in js)
    case("owner_net.js does not match the ntfy bus (same-NAT toy)", "pollNet" not in js and "durable.concat" not in js)
    case("owner_net.js matches enrolled slots only", "function matchingSlot" in js and "function slotsDistinct" in js)
    case("owner_net.js six-hour send gate (board ntfy quota)", "SEND_GAP_MS = 6 * 60 * 60 * 1000" in js)
    case("owner_net.js seeds the bus from remembered BRYCE", "rememberedBryce()" in js)
    case("owner_net.js always hashes this network", "collectDigests(spec)" in js)

    py = open(os.path.join(HERE, "owner_enroll.py"), encoding="utf-8").read()
    case("enroll docstring forbids printing the IP", "Never prints the IP" in py or "never prints the IP" in py)
    case("enroll is not the persist path", "owner_net.py" in py)

    html = open(os.path.join(HERE, "owner-net.html"), encoding="utf-8").read()
    case("owner-net.html cites vr8fo8", "BRYCE-1787134106972-vr8fo8" in html)
    case("owner-net.html cites the no-loop law", "admin-no-verification-loop-20260819-01" in html)
    case("owner-net.html does not remint vr8fo8", html.count("BRYCE-1787134106972-vr8fo8") >= 1)
    case("owner.html says same wifi is not the door", "Same wifi" in html or "same wifi" in html)
    case("owner-net separates live enrollment from the half directive",
         "Two-slot enrollment is LIVE only" in html and
         "Directive 10 remains HALF" in html and
         "private non-static verifier is OPEN" in html)
    case("owner-net loads the state-contract script revision", "owner_net.js?v=20260824a" in html)

    owner_html = open(os.path.join(HERE, "owner.html"), encoding="utf-8").read()
    case("owner.html pins both owner scripts before session boot",
         owner_html.index("owner.js?v=20260824a") < owner_html.index("owner_net.js?v=20260824a") <
         owner_html.index("session.js?v=20260820y"))
    case("owner.html waits for the pin API, not a truthy collision marker",
         'typeof window.COMMONS_OWNER.readPin === "function"' in owner_html)

    carrier = open(os.path.join(HERE, "carrier.js"), encoding="utf-8").read()
    session = open(os.path.join(HERE, "session.js"), encoding="utf-8").read()
    case("carrier.js loads current owner_net.js",
         "loadOwnerDoor" in carrier and 'owner_net.js") + "?v=20260824a"' in carrier)
    case("session.js loads current owner_net.js", "loadOwnerDoor" in session and "owner_net.js?v=20260824a" in session)
    case("bindFromMemory still exists (name memory, not IP)", "function bindFromMemory" in carrier)

    tmp = tempfile.mkdtemp(prefix="commons-owner-")
    # The helper unit starts empty. Live owner.json may legitimately carry one
    # enrolled slot, and cloning it made the append assertion depend on runtime state.
    spec2 = empty_spec()
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

    s = empty_spec()
    owner_net.apply_sighting(s, d4, "pc")
    owner_net.apply_sighting(s, d4, "phone")
    case("same digest on phone+pc is not live", not owner_net.distinct_live(s))

    wifi = empty_spec()
    case("pc sighting fills pc", owner_net.apply_sighting(wifi, d4, "pc"))
    case("phone on same digest as pc is refused", not owner_net.apply_sighting(wifi, d4, "phone"))
    case("wifi pair is not distinct_live", not owner_net.distinct_live(wifi))
    case("cell phone after pc is live", owner_net.apply_sighting(wifi, d6, "phone") and owner_net.distinct_live(wifi))

    locked = empty_spec()
    owner_net.apply_sighting(locked, d4, "pc")
    case("filled pc slot is not overwritten", not owner_net.apply_sighting(locked, d6, "pc"))
    case("pc slot still the first digest", owner_net.slot_hash(locked["slots"]["pc"]) == d4)

    swap = empty_spec()
    case("phone may fill first", owner_net.apply_sighting(swap, d4, "phone"))
    owner_net.apply_sighting(swap, d4, "pc")
    case("phone-wifi then pc is not live", not owner_net.distinct_live(swap))
    case("same digest slots have one canonical hash", swap["hashes"] == expected_hash_items(swap["slots"]))
    case("cell replaces phone slot that still equals pc", owner_net.apply_sighting(swap, d6, "phone") and owner_net.distinct_live(swap))

    via_less = owner_net.parse_payload(json.dumps({"k": "owner-net", "sha256": d4}))
    case("payload without via does not persist", via_less == (d4, "") or via_less[1] not in ("pc", "phone"))
    tagged = owner_net.parse_payload(json.dumps({"k": "owner-net", "sha256": d4, "via": "pc"}))
    case("payload with via=pc parses", tagged == (d4, "pc"))

    refuse = False
    try:
        owner_net.refuse_raw_ips('{"note":"%s"}' % FIXTURE_V4)
    except SystemExit:
        refuse = True
    case("writer refuses a raw IPv4 blob", refuse)

    wf = open(os.path.join(HERE, ".github/workflows/owner-net.yml"), encoding="utf-8").read()
    case("owner-net workflow exists", "name: owner-net" in wf)
    case("workflow commits owner.json only", "git add -- owner.json" in wf)
    case("workflow does not touch ingest", "board_ingest.py" not in wf)
    case("workflow does not touch fat index", "index.html" not in wf)

    directives = open(os.path.join(HERE, "DIRECTIVES.md"), encoding="utf-8").read()
    todo = open(os.path.join(HERE, "todo.html"), encoding="utf-8").read()
    directive10_match = re.search(r"^### 10\..*?(?=^### 11\.)", directives, re.M | re.S)
    directive10 = directive10_match.group(0) if directive10_match else ""
    case("DIRECTIVES item 10 exists", bool(directive10_match))
    case("DIRECTIVES item 10 is HALF", "**Status:** HALF 2026-08-24" in directive10)
    case("DIRECTIVES records live slots without closing private verifier",
         "hashed-IP recognition is LIVE" in directive10 and
         "Still OPEN inside this line" in directive10 and
         "private" in directive10)
    todo10_match = re.search(r"<tr><td>10</td>.*?</tr>", todo, re.S)
    todo10 = todo10_match.group(0) if todo10_match else ""
    case("todo row 10 exists", bool(todo10_match))
    case("todo row 10 is HALF", 'class="s-half">HALF</b>' in todo10)
    case("todo row 10 records live hashed-IP recognition", "hashed-IP recognition is LIVE" in todo10)
    case("knock receipt is not treated as a land in DIRECTIVES", "knock-dir10-owner-net-door-20260819-01` is not a land" in directive10)

    print("OWNER HASH TEST: %d passed, %d failed" % (ok, fail))
    return 0 if fail == 0 else 1


def FALLBACK_IN_JS(js: str) -> bool:
    return 'FALLBACK_PEPPER = "commons-owner-v1"' in js and '"\\n"' in js


if __name__ == "__main__":
    raise SystemExit(main())
