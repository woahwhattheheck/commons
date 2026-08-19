#!/usr/bin/env python3
"""
=============================================================================
LEAKAGE SUITE
=============================================================================

Drives a real bridge over a real socket and asserts that nothing
mechanism-bearing crosses it -- for EVERY allowlisted operation, on the happy
path AND on every forced-error path.

The scanner below is written INDEPENDENTLY of public_schema.scan on purpose.
If the bridge's own sanitizer were subtly wrong, a suite that reused it would
agree with the bug. This one does not import it.

    python test_leakage.py

Exit code 0 == every assertion held.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("ASTER_TEST_PORT", "7891"))
BASE = "http://127.0.0.1:%d" % PORT
STATE_DIR = os.path.join(HERE, ".test_private")

RESERVED_PORTS = {7881, 7882, 7883, 7890, 7899}
assert PORT not in RESERVED_PORTS, "test port collides with a reserved listener"


# ---------------------------------------------------------------------------
# Independent scanner
# ---------------------------------------------------------------------------

# Required by the boundary specification, hard-coded here rather than imported.
REQUIRED_TOKENS = [
    "titan", "gguf", "muhl_", "nring", "ring", "radix", "fan-in",
    "gate", "wire", "foundry", "genome", "lever", "preflight",
    ".mno", "c:\\", "traceback", 'file "',
]

LEAK_PATTERNS = [
    ("absolute_windows_path", re.compile(r"(?:^|[^A-Za-z0-9])[A-Za-z]:[\\/]")),
    ("absolute_unc_path", re.compile(r"\\\\[A-Za-z0-9_.$-]+\\")),
    ("absolute_posix_path", re.compile(
        r"(?i)(?:^|[\s\"'(\[,=])/(?:users|home|mnt|etc|var|usr|opt|tmp|proc|root|bin|sbin|dev)(?:/|\b)")),
    ("local_uri", re.compile(r"(?i)\b(?:file|smb|ftp)://")),
    ("stack_trace", re.compile(r"(?i)traceback")),
    ("stack_frame", re.compile(r'(?i)file "')),
    ("source_line", re.compile(r"(?i)\.py\"?,\s*line\s*\d+")),
]


def load_denylist():
    tokens = []
    path = os.path.join(HERE, "denylist.txt")
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                tokens.append(line.lower())
    assert tokens, "deny-list file is empty -- the suite would prove nothing"
    return tokens


DENY_TOKENS = load_denylist()

# Internal literals that live only in the private layer. If any of these ever
# appears in a response the opaque-handle boundary has failed.
PRIVATE_LITERALS = [
    "lever.frontload.width", "nring2.drive.depth", "gate.prune.dead",
    "wire.fanin.balance", "radix.schedule.order",
    "local:owner", "local:aster", "local:peer-01", "local:watch-01",
    "loom.mno", "frontload", "nring2_0017", "foundry_genome",
    "aster_home.jsonl", "audit.log", "salt.bin", "handles.json",
]


def find_leaks(text, where):
    hits = []
    low = text.lower()
    for tok in REQUIRED_TOKENS:
        if tok in low:
            hits.append("required-token %r" % tok)
    for tok in DENY_TOKENS:
        if tok in low:
            hits.append("denylist-token %r" % tok)
    for tok in PRIVATE_LITERALS:
        if tok.lower() in low:
            hits.append("private-literal %r" % tok)
    for label, pat in LEAK_PATTERNS:
        m = pat.search(text)
        if m:
            hits.append("%s %r" % (label, m.group(0)))
    return ["%s: %s" % (where, h) for h in hits]


# ---------------------------------------------------------------------------
# Assertion bookkeeping
# ---------------------------------------------------------------------------

class Suite:
    def __init__(self):
        self.passed = 0
        self.failed = []
        self.scans = 0

    def check(self, condition, label):
        self.passed += 1
        if not condition:
            self.failed.append(label)
            self.passed -= 1
            print("  FAIL  %s" % label)
        return bool(condition)

    def scan(self, text, where):
        """One assertion per scanned payload."""
        self.scans += 1
        hits = find_leaks(text, where)
        return self.check(not hits, "clean payload <%s>%s" % (
            where, "" if not hits else " -> " + "; ".join(hits[:4])))


S = Suite()


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

def call(verb, params=None, token=None, path="/rpc", method="POST"):
    """Returns (status, raw_body_text, parsed_or_None)."""
    body = None
    if method == "POST":
        body = json.dumps({"verb": verb, "params": params or {}}).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    if token is not None:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        status = exc.code
    try:
        parsed = json.loads(raw)
    except ValueError:
        parsed = None
    return status, raw, parsed


def port_free(port):
    try:
        with socket.create_connection(("127.0.0.1", port), 0.5):
            return False
    except OSError:
        return True


def wait_ready(proc, port, token_path, timeout=30.0):
    """
    Wait for OUR child to be serving.

    Both conditions are required. A socket alone is not proof: if some other
    process already held the port, an earlier version of this suite would have
    happily tested a stranger. Requiring the child's own freshly minted token
    file ties the readiness signal to the process we actually launched.
    """
    end = time.time() + timeout
    while time.time() < end:
        if proc.poll() is not None:
            out = ""
            try:
                out = proc.stdout.read() or ""
            except Exception:
                pass
            print("bridge exited early (rc=%s):\n%s" % (proc.returncode, out))
            return False
        if os.path.isfile(token_path):
            try:
                with socket.create_connection(("127.0.0.1", port), 0.5):
                    return True
            except OSError:
                pass
        time.sleep(0.15)
    print("bridge did not become ready within %.0fs" % timeout)
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 74)
    print("ASTER BRIDGE -- LEAKAGE SUITE")
    print("=" * 74)

    # fresh ephemeral state so the run is repeatable
    if os.path.isdir(STATE_DIR):
        for name in os.listdir(STATE_DIR):
            try:
                os.remove(os.path.join(STATE_DIR, name))
            except OSError:
                pass

    token_path = os.path.join(STATE_DIR, "aster_token.txt")

    if not port_free(PORT):
        print("REFUSING TO RUN: something is already listening on 127.0.0.1:%d."
              % PORT)
        print("Stop it first -- otherwise this suite would test that process,")
        print("not the bridge it is supposed to be proving.")
        return 3

    proc = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "aster_bridge.py"),
         "--port", str(PORT), "--state-dir", STATE_DIR],
        cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    try:
        if not wait_ready(proc, PORT, token_path):
            proc.kill()
            return 3

        with open(token_path, "r", encoding="utf-8") as fh:
            token = fh.read().strip()

        import public_schema as pub          # for the verb inventory only
        verbs = list(pub.VERB_NAMES)
        print("\nallowlisted operations: %d" % len(verbs))

        # ---- 1. loopback-only binding ---------------------------------
        print("\n[1] bind surface")
        ok_local = False
        try:
            with socket.create_connection(("127.0.0.1", PORT), 2.0):
                ok_local = True
        except OSError:
            pass
        S.check(ok_local, "listener reachable on 127.0.0.1")

        lan_ip = None
        try:
            lan_ip = socket.gethostbyname(socket.gethostname())
        except OSError:
            pass
        if lan_ip and lan_ip != "127.0.0.1":
            refused = False
            try:
                with socket.create_connection((lan_ip, PORT), 2.0):
                    refused = False
            except OSError:
                refused = True
            S.check(refused, "listener NOT reachable on non-loopback %s" % lan_ip)
        else:
            print("      (no distinct non-loopback address to probe)")

        try:
            out = subprocess.run(["netstat", "-ano"], capture_output=True,
                                 text=True, timeout=30).stdout
        except Exception:
            out = ""
        rows = [l for l in out.splitlines()
                if (":%d " % PORT) in l and "LISTENING" in l.upper()]
        S.check(bool(rows) and all("127.0.0.1:%d" % PORT in r for r in rows),
                "every listening row for :%d is bound to 127.0.0.1" % PORT)
        for r in rows:
            print("      %s" % r.strip())

        # ---- 2. authentication ----------------------------------------
        print("\n[2] authentication")
        st, raw, parsed = call("status", token=None)
        S.check(st == 401, "unauthenticated request rejected (401)")
        S.check(parsed and parsed.get("error", {}).get("code") == "E_AUTH",
                "unauthenticated response carries E_AUTH")
        S.scan(raw, "unauth")
        print("      unauthenticated -> %d %s" % (st, raw))

        st, raw, parsed = call("status", token="not-the-token")
        S.check(st == 401, "bad bearer token rejected (401)")
        S.scan(raw, "badtoken")

        st, raw, parsed = call("status", token=token)
        S.check(st == 200 and parsed.get("ok") is True,
                "valid bearer token accepted")

        # ---- 3. allowlist ---------------------------------------------
        print("\n[3] allowlist")
        for bogus in ["titan.dump", "__import__", "status ", "",
                      "optimize.list.extra", "../../etc/passwd"]:
            st, raw, parsed = call(bogus, token=token)
            S.check(st == 404 and parsed.get("error", {}).get("code") == "E_VERB",
                    "non-allowlisted verb refused: %r" % bogus)
            S.scan(raw, "verb:%r" % bogus)
        st, raw, parsed = call({"a": 1}, token=token)
        S.check(parsed and parsed.get("error", {}).get("code") == "E_VERB",
                "non-text verb refused without crashing")
        S.scan(raw, "verb:non-text")

        # ---- 4. happy path + every forced-error path -------------------
        print("\n[4] full sweep: every operation x every probe")

        st, raw, parsed = call("optimize.list", token=token)
        caps = parsed["data"]["capabilities"]
        cap_handle = caps[0]["handle"]
        cap_objective = caps[0]["objectives"][0]
        st, raw, parsed = call("players.list", token=token)
        player_handle = parsed["data"]["players"][0]["handle"]
        st, raw, parsed = call("task.submit",
                               {"objective": "summarise the shared surface"},
                               token=token)
        task_handle = parsed["data"]["task"]
        st, raw, parsed = call("optimize.request",
                               {"capability": cap_handle,
                                "objective": cap_objective}, token=token)
        receipt_handle = parsed["data"]["receipt"]

        GOOD = {
            "players.message": {"to": player_handle, "body": "hello"},
            "home.write": {"text": "durable note from aster"},
            "scratch.write": {"text": "ephemeral note"},
            "task.submit": {"objective": "reduce settle time"},
            "task.observe": {"task": task_handle},
            "optimize.request": {"capability": cap_handle,
                                 "objective": cap_objective},
            "receipt.get": {"receipt": receipt_handle},
        }

        probes = [
            ("normal", {}),
            ("probe_fault", {"probe_fault": True}),
            ("probe_taint", {"probe_taint": True}),
            ("probe_undeclared", {"probe_undeclared": True}),
        ]

        fault_example = None
        for verb in verbs:
            base = dict(GOOD.get(verb, {}))
            for label, extra in probes:
                params = dict(base)
                params.update(extra)
                st, raw, parsed = call(verb, params, token=token)
                S.scan(raw, "%s/%s" % (verb, label))
                if label == "probe_fault":
                    S.check(
                        parsed and parsed.get("error", {}).get("code") == "E_INTERNAL",
                        "%s + forced exception -> E_INTERNAL" % verb)
                    if fault_example is None:
                        fault_example = raw
                elif label in ("probe_taint", "probe_undeclared"):
                    S.check(
                        parsed and parsed.get("error", {}).get("code") == "E_SANITIZE",
                        "%s + %s -> E_SANITIZE (fail closed)" % (verb, label))
                    S.check("ok" in (parsed or {}) and parsed.get("ok") is False,
                            "%s + %s returns no data" % (verb, label))
                else:
                    S.check(parsed and parsed.get("ok") is True,
                            "%s happy path succeeds" % verb)

        print("\n      redacted internal fault:")
        print("      %s" % fault_example)

        # ---- 5. inbound content refusal --------------------------------
        print("\n[5] inbound content policy")
        for payload in [r"C:\Users\lucys\Desktop\loom.mno",
                        "please tune the frontload lever",
                        "Traceback (most recent call last):"]:
            st, raw, parsed = call("home.write", {"text": payload}, token=token)
            S.check(parsed.get("error", {}).get("code") == "E_CONTENT",
                    "protected content refused inbound: %r" % payload[:28])
            S.scan(raw, "inbound-refusal")
        st, raw, parsed = call("home.read", {"limit": 50}, token=token)
        S.scan(raw, "home.read after refused writes")
        S.check(parsed.get("ok") is True, "journal still readable and clean")

        # ---- 6. opaque handles ----------------------------------------
        print("\n[6] opaque handles")
        import re as _re
        pat = _re.compile(r"^(?:pl|tk|rc|cap|en|gn)_[0-9a-f]{16}$")
        S.check(all(pat.match(c["handle"]) for c in caps),
                "capability handles are opaque")
        S.check(pat.match(task_handle) and pat.match(receipt_handle)
                and pat.match(player_handle), "issued handles are opaque")
        st, raw, parsed = call("optimize.request",
                               {"capability": "cap_" + "0" * 16,
                                "objective": "latency"}, token=token)
        S.check(parsed.get("error", {}).get("code") == "E_STATE",
                "unknown capability handle -> E_STATE")
        S.scan(raw, "unknown-handle")

        # ---- 7. manifest ----------------------------------------------
        print("\n[7] public manifest")
        st, raw, parsed = call(None, token=token, path="/manifest", method="GET")
        S.check(st == 200 and "operations" in (parsed or {}),
                "manifest served to an authenticated caller")
        S.scan(raw, "manifest")
        S.check(len(parsed["operations"]) == len(verbs),
                "manifest publishes exactly the allowlist")
        st, raw, parsed = call(None, token=None, path="/manifest", method="GET")
        S.check(st == 401, "manifest also demands authentication")

        # ---- 8. the audit record never crosses -------------------------
        print("\n[8] audit isolation")
        audit_path = os.path.join(STATE_DIR, "audit.log")
        S.check(os.path.isfile(audit_path), "audit record written locally")
        with open(audit_path, "r", encoding="utf-8") as fh:
            audit_lines = [l for l in fh if l.strip()]
        S.check(len(audit_lines) > 0, "audit record has entries (%d)" % len(audit_lines))
        decisions = {}
        for line in audit_lines:
            try:
                decisions[json.loads(line).get("decision")] = 1 + decisions.get(
                    json.loads(line).get("decision"), 0)
            except ValueError:
                pass
        print("      audit entries: %d  decisions: %s"
              % (len(audit_lines), decisions))
        for probe_path in ["/audit", "/audit.log", "/.private/audit.log",
                           "/rpc?f=audit.log"]:
            st, raw, parsed = call(None, token=token, path=probe_path,
                                   method="GET")
            S.check(st in (404, 405), "no route serves the audit record: %s"
                    % probe_path)
            S.scan(raw, "audit-probe %s" % probe_path)
        S.check(not any(v in ("audit", "audit.read", "audit.log")
                        for v in verbs), "no allowlisted operation reads the audit")

        # ---- 9. oversized / malformed input ---------------------------
        print("\n[9] malformed input")
        st, raw, parsed = call("home.write", {"text": "x" * 9000}, token=token)
        S.check(parsed.get("error", {}).get("code") == "E_PARAM",
                "oversized text refused")
        S.scan(raw, "oversize")
        st, raw, parsed = call("home.write", {"nope": 1}, token=token)
        S.check(parsed.get("error", {}).get("code") == "E_PARAM",
                "undeclared inbound parameter refused")
        S.scan(raw, "unknown-param")
        req = urllib.request.Request(BASE + "/rpc", data=b"{not json",
                                     method="POST")
        req.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                st, raw = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            st, raw = e.code, e.read().decode()
        S.check(st == 400, "malformed JSON body refused")
        S.scan(raw, "bad-json")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("\n" + "=" * 74)
    print("assertions passed : %d" % S.passed)
    print("payload scans     : %d" % S.scans)
    print("failures          : %d" % len(S.failed))
    for f in S.failed:
        print("   - %s" % f)
    print("=" * 74)
    return 0 if not S.failed else 1


if __name__ == "__main__":
    sys.exit(main())
