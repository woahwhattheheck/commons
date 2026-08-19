#!/usr/bin/env python3
"""
=============================================================================
ASTER BRIDGE  --  IP-sterilized local adapter
=============================================================================

An external party ("Aster") is given capability verbs and opaque handles.
It is never given mechanism.

    inbound  ->  auth  ->  allowlist  ->  parameter contract  ->  adapter
    adapter  ->  fail-closed sanitizer  ->  final gate  ->  outbound

TWO LAYERS, DELIBERATELY SEPARATED INTO TWO FILES

    public_schema.py    what Aster sees. Verbs, opaque handles, constant
                        error codes. No local logic lives there.
    private_adapter.py  what actually runs here. Internal identifiers, the
                        handle vault, the audit record. Never serialized.

This file is the only thing that joins them, and it joins them in one
direction: an adapter result must be re-proven by the public contract before
any of it crosses. An adapter that starts emitting something new does not
widen the surface -- it fails the call.

    LOOPBACK ONLY. BEARER TOKEN REQUIRED. NO PUBLIC URL. NO UPLOAD.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import public_schema as pub
from public_schema import ALLOWLIST, ERRORS, SanitizeError
import private_adapter as priv
from private_adapter import Adapter, AdapterError, OP_TABLE

BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 7891

# Local listeners this bridge must never occupy.
RESERVED_PORTS = {7881, 7882, 7883, 7890, 7899}

MAX_BODY = 256 * 1024
RATE_WINDOW = 60.0
RATE_LIMIT = 480

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

def load_token(state_dir):
    """Read the local bearer secret, minting one on first run."""
    import secrets
    path = os.path.join(state_dir, "aster_token.txt")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tok = fh.read().strip()
        if len(tok) >= 32:
            return tok, path, False
    except OSError:
        pass
    tok = secrets.token_urlsafe(36)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(tok + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return tok, path, True


# ---------------------------------------------------------------------------
# Bridge core
# ---------------------------------------------------------------------------

class Bridge:

    def __init__(self, state_dir=None):
        self.adapter = Adapter(state_dir)
        self.audit = self.adapter.audit
        self.token, self.token_path, self.token_new = load_token(
            self.adapter.dir)
        self.rate = []
        self.lock = threading.Lock()
        self.calls = 0

    # -- auth ------------------------------------------------------------

    def authorized(self, header):
        import hmac as _hmac
        if not header or not header.startswith("Bearer "):
            return False
        offered = header[7:].strip()
        if not offered:
            return False
        return _hmac.compare_digest(offered, self.token)

    def rate_ok(self):
        now = time.time()
        with self.lock:
            self.rate = [t for t in self.rate if now - t < RATE_WINDOW]
            if len(self.rate) >= RATE_LIMIT:
                return False
            self.rate.append(now)
            return True

    # -- dispatch --------------------------------------------------------

    def run_op(self, verb, params):
        """
        Execute one allowlisted operation. The three diagnostic probes are
        handled HERE so the redaction and fail-closed paths are reachable
        from outside and can be tested rather than merely asserted.
        """
        if params.get("probe_fault"):
            # Deliberately raises with a location- and vocabulary-bearing
            # message. Nothing of it may reach the caller.
            raise RuntimeError(priv.FAULT_TEXT)

        fn = getattr(self.adapter, OP_TABLE[verb])
        result = fn(params)

        if params.get("probe_taint"):
            fields = ALLOWLIST[verb]["result"][1]
            first = next(iter(fields))
            result[first] = priv.TAINT

        if params.get("probe_undeclared"):
            result["_internal"] = priv.TAINT

        return result

    def handle(self, verb_raw, raw_params, caller):
        """
        Returns (http_status, envelope_dict).

        Every exit from this function is either a proven result or a constant
        error code. There is no path that returns adapter text.
        """
        self.calls += 1
        redactions = 0

        # -- allowlist ---------------------------------------------------
        if not isinstance(verb_raw, str) or verb_raw not in ALLOWLIST:
            # The verb is NEVER echoed unless it is allowlisted -- echoing
            # caller-supplied text would reflect arbitrary content outward.
            self.audit.write(event="call", verb=None, caller=caller,
                             decision="deny", code="E_VERB", redactions=0)
            return 404, self.error(None, "E_VERB")

        try:
            params = pub.bind_params(verb_raw, raw_params)
        except SanitizeError as exc:
            hits = 1 if exc.code == "E_CONTENT" else 0
            self.audit.write(event="call", verb=verb_raw, caller=caller,
                             decision="deny", code=exc.code,
                             redactions=hits, detail=exc.detail)
            return 400, self.error(verb_raw, exc.code)

        # -- local execution ---------------------------------------------
        try:
            raw = self.run_op(verb_raw, params)
        except AdapterError as exc:
            self.audit.write(event="call", verb=verb_raw, caller=caller,
                             decision="deny", code=exc.code, redactions=0,
                             detail=exc.detail)
            return 409, self.error(verb_raw, exc.code)
        except Exception as exc:
            # The real exception text is recorded LOCALLY and discarded from
            # the response. Type name only -- never the message, never a
            # location, never a frame.
            self.audit.write(event="call", verb=verb_raw, caller=caller,
                             decision="fault", code="E_INTERNAL",
                             redactions=0, exc_type=type(exc).__name__)
            return 500, self.error(verb_raw, "E_INTERNAL")

        # -- fail-closed sanitizer ---------------------------------------
        try:
            redactions = pub.count_hits(ALLOWLIST[verb_raw]["result"], raw)
            data = pub.sanitize_result(verb_raw, raw)
        except SanitizeError as exc:
            self.audit.write(event="call", verb=verb_raw, caller=caller,
                             decision="withhold", code="E_SANITIZE",
                             redactions=max(redactions, 1), detail=exc.detail)
            return 500, self.error(verb_raw, "E_SANITIZE")
        except Exception as exc:
            self.audit.write(event="call", verb=verb_raw, caller=caller,
                             decision="withhold", code="E_SANITIZE",
                             redactions=max(redactions, 1),
                             exc_type=type(exc).__name__)
            return 500, self.error(verb_raw, "E_SANITIZE")

        self.audit.write(event="call", verb=verb_raw, caller=caller,
                         decision="allow", code="OK", redactions=redactions)
        return 200, {"ok": True, "verb": verb_raw, "ts": priv.now_stamp(),
                     "data": data}

    @staticmethod
    def error(verb, code):
        # `verb` is echoed ONLY when it is a known operation name. Caller
        # supplied text is never reflected outward, and a non-text verb can
        # never reach the allowlist membership test.
        safe = verb if (isinstance(verb, str) and verb in ALLOWLIST) else None
        return {"ok": False,
                "verb": safe,
                "ts": priv.now_stamp(),
                "error": {"code": code, "message": ERRORS[code]}}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "aster-bridge"
    sys_version = ""           # never advertise the runtime build

    bridge = None              # set by serve()

    def log_message(self, fmt, *args):
        pass                   # local console stays clean; the audit is the record

    # -- emit ------------------------------------------------------------

    def _emit(self, status, obj, verb_for_audit=None):
        """
        FINAL GATE. The fully serialized body is scanned one last time. If
        anything at all trips, the body is discarded and replaced with a
        constant refusal. This is belt-and-braces on top of the field-level
        sanitizer: a careless edit to a key name or a constant cannot open a
        hole without also failing the call.
        """
        body = json.dumps(obj, ensure_ascii=False)
        hits = pub.scan(body)
        if hits:
            self.bridge.audit.write(event="final_gate", verb=verb_for_audit,
                                    decision="withhold", code="E_SANITIZE",
                                    redactions=len(hits), detail=str(hits))
            obj = Bridge.error(None, "E_SANITIZE")
            body = json.dumps(obj, ensure_ascii=False)
            status = 500
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _deny(self, status, code):
        # A refused request may still have an unread body on the socket.
        # Close rather than risk the next request reading its remnant.
        self.close_connection = True
        self._emit(status, Bridge.error(None, code))

    def _caller(self):
        return "aster"

    def _auth_or_deny(self):
        if not self.bridge.authorized(self.headers.get("Authorization")):
            self.bridge.audit.write(event="auth", verb=None,
                                    caller=self.client_address[0],
                                    decision="deny", code="E_AUTH",
                                    redactions=0)
            self._deny(401, "E_AUTH")
            return False
        if not self.bridge.rate_ok():
            self.bridge.audit.write(event="rate", verb=None,
                                    caller=self._caller(), decision="deny",
                                    code="E_LIMIT", redactions=0)
            self._deny(429, "E_LIMIT")
            return False
        return True

    # -- routes ----------------------------------------------------------

    def do_GET(self):
        if not self._auth_or_deny():
            return
        route = self.path.split("?", 1)[0]
        if route == "/manifest":
            self.bridge.audit.write(event="manifest", verb=None,
                                    caller=self._caller(), decision="allow",
                                    code="OK", redactions=0)
            self._emit(200, pub.manifest())
            return
        if route == "/health":
            self._emit(200, {"ok": True, "verb": None,
                             "ts": priv.now_stamp(), "data": {"live": True}})
            return
        self._deny(404, "E_METHOD")

    def do_POST(self):
        if not self._auth_or_deny():
            return
        route = self.path.split("?", 1)[0]
        if route != "/rpc":
            self._deny(404, "E_METHOD")
            return

        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._deny(400, "E_PARAM")
            return
        if length < 0 or length > MAX_BODY:
            self._deny(413, "E_PARAM")
            return

        try:
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            self._deny(400, "E_PARAM")
            return
        if not isinstance(payload, dict):
            self._deny(400, "E_PARAM")
            return

        verb = payload.get("verb")
        audit_verb = verb if (isinstance(verb, str) and verb in ALLOWLIST) else None
        status, envelope = self.bridge.handle(
            verb, payload.get("params"), self._caller())
        self._emit(status, envelope, audit_verb)

    def do_PUT(self):
        if self._auth_or_deny():
            self._deny(405, "E_METHOD")

    do_DELETE = do_PUT
    do_PATCH = do_PUT

    def do_HEAD(self):
        # Headers only -- a HEAD must never carry a body.
        self.send_response(401 if not self.bridge.authorized(
            self.headers.get("Authorization")) else 405)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_error(self, code, message=None, explain=None):
        # Replace the default diagnostic HTML page with a constant envelope.
        try:
            self._deny(int(code), "E_METHOD")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def startup_checks(port, host):
    """Refuse to start in any configuration that could widen the surface."""
    problems = []
    if host != BIND_HOST:
        problems.append("bind host must be %s" % BIND_HOST)
    if port in RESERVED_PORTS:
        problems.append("port %d is reserved for another local listener" % port)
    if not pub.DENYLIST_LOADED:
        problems.append("deny-list did not load; refusing to serve")
    return problems


def serve(port=DEFAULT_PORT, state_dir=None, ready=None):
    problems = startup_checks(port, BIND_HOST)
    if problems:
        for p in problems:
            print("REFUSED: %s" % p)
        return 2

    bridge = Bridge(state_dir)
    Handler.bridge = bridge

    httpd = ThreadingHTTPServer((BIND_HOST, port), Handler)
    httpd.daemon_threads = True

    bound_host, bound_port = httpd.socket.getsockname()[:2]
    print("ASTER BRIDGE  http://%s:%d/" % (bound_host, bound_port))
    print("  bound address    : %s  (loopback only)" % bound_host)
    print("  operations       : %d allowlisted" % len(ALLOWLIST))
    print("  deny-list tokens : %d" % len(pub.DENY_TOKENS))
    print("  state folder     : hardened=%s" % bridge.adapter.harden_status)
    print("  bearer token     : %s" %
          ("MINTED on this run" if bridge.token_new else "existing"))
    print("  token location   : the host reads it locally; it is not printed")
    print("  audit            : append-only, host-only, never served")
    sys.stdout.flush()

    if ready:
        ready()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


# ---------------------------------------------------------------------------
# Local emitters. These write files ON THE HOST for the owner. They are not
# served and they are not reachable from the bridge.
# ---------------------------------------------------------------------------

_JSON_SCHEMA_TYPE = {
    "handle": "string", "text": "string", "stamp": "string",
    "enum": "string", "flag": "boolean", "count": "integer",
    "list": "array", "shape": "object",
}


def _to_json_schema(node):
    out = {"type": _JSON_SCHEMA_TYPE[node["type"]]}
    if node["type"] == "enum":
        out["enum"] = node["values"]
    elif node["type"] == "list":
        out["items"] = _to_json_schema(node["items"])
    elif node["type"] == "shape":
        out["properties"] = {k: _to_json_schema(v)
                             for k, v in node["fields"].items()}
        out["additionalProperties"] = False
    elif node["type"] == "text":
        out["maxLength"] = node.get("max_length")
    return out


def emit_manifest(path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(pub.manifest(), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def emit_openai_tools(path):
    """
    The same allowlist rendered as OpenAI-style function tools, for pasting
    into a custom-tool configuration. Written locally; never served, because
    JSON Schema type words are not part of the sanitized outbound vocabulary.
    """
    tools = []
    man = pub.manifest()
    for verb, op in man["operations"].items():
        props, required = {}, []
        for name, decl in op["params"].items():
            node = _to_json_schema(decl)
            node["description"] = decl.get("note", "")
            props[name] = node
            if decl.get("required"):
                required.append(name)
        tools.append({
            "type": "function",
            "function": {
                "name": verb.replace(".", "_"),
                "description": op["summary"],
                "parameters": {"type": "object", "properties": props,
                               "required": required,
                               "additionalProperties": False},
            },
        })
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"tools": tools}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description="Aster bridge (loopback only)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--state-dir", default=None)
    ap.add_argument("--emit-manifest", action="store_true")
    ap.add_argument("--emit-openai", action="store_true")
    ap.add_argument("--show-token", action="store_true",
                    help="print the bearer token to THIS console (owner step)")
    args = ap.parse_args(argv)

    if args.emit_manifest or args.emit_openai:
        if args.emit_manifest:
            print(emit_manifest(os.path.join(HERE, "ASTER_TOOL_MANIFEST.json")))
        if args.emit_openai:
            print(emit_openai_tools(os.path.join(HERE, "ASTER_OPENAI_TOOLS.json")))
        return 0

    if args.show_token:
        b = Bridge(args.state_dir)
        print(b.token)
        return 0

    return serve(args.port, args.state_dir)


if __name__ == "__main__":
    sys.exit(main())
