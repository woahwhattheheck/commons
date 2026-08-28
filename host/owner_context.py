#!/usr/bin/env python3
"""host/owner_context.py — optional owner-context display host.

Directive 10 leftover: a host outside the static Pages tree may annotate
the owner's interface with a privacy-preserving network-context digest.
Display only. Never a gate. Never authority. Never publishes a raw IP.

Cite BRYCE-1787134106972-vr8fo8. Do not remint.
Law: admin-no-verification-loop-20260819-01. Do not remint.
Pinned boundary: identity verification is not future work under the
NO-AUTH law. from= stays a claim.

Two-slot hashed enrollment stays on owner_net.py / owner.json.
This module does not overwrite those slots.

  python3 host/owner_context.py doctor
  python3 host/owner_context.py simulate
  python3 host/owner_context.py serve --bind localhost:8789
  python3 host/owner_context.py --self-test

FINDER-FAILED / FINDER-UNVERIFIED plus the search space. Never 0.
no auth. no gate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import owner_enroll
import owner_net

KIND = "owner-context"
CONTRACT_V = 1
PEPPER_VERSION = "v1"
PEPPERS = {PEPPER_VERSION: "commons-owner-v1"}
RETENTION_SECONDS = 6 * 60 * 60
CACHE_MAX = 64
VIAS = ("pc", "phone")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
IPV4_BLOB = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_BLOB = re.compile(r"\b[0-9a-fA-F:]+:[0-9a-fA-F:]+\b")
DOC_V4_PREFIXES = ("192.0.2.", "198.51.100.", "203.0.113.")
DOC_V6_PREFIX = "2001:db8:"
DEFAULT_CANDIDATE = "https://commons-spark-mcp.vercel.app/owner-context"
AUTHORITY = False
DISPLAY_ONLY = True
FINDER_FAILED = "FINDER-FAILED"
FINDER_UNVERIFIED = "FINDER-UNVERIFIED"
CALIBRATION = (
    os.path.join("owner.json"),
    os.path.join("owner_net.py"),
    os.path.join("ground", "EXECUTE.md"),
)
SEARCH_SPACE = (
    os.path.join("host", "owner_context.py"),
    os.path.join("ground", "OWNER_CONTEXT.md"),
    os.path.join("ground", "OWNER_CONTEXT.json"),
    os.path.join("integrations", "owner_context", "service.py"),
    os.path.join("api", "owner_context.py"),
    os.path.join("owner.json"),
    os.path.join("owner_net.py"),
    os.path.join("owner_net.js"),
    os.path.join("owner-net.html"),
)
EXTERNAL_HOST_ACTION = (
    "Deploy the repo-controlled adapter onto an always-on host that can see "
    "the connecting peer. Preferred already-connected host: existing Vercel "
    "project commons-spark-mcp.vercel.app (vercel.json rewrite /owner-context "
    "-> api/owner_context.py). Confirm GET "
    "https://commons-spark-mcp.vercel.app/owner-context returns JSON "
    "k=owner-context authority=false gate=false with no raw IP. If that "
    "project does not auto-deploy this repo, trigger a production deploy of "
    "current main on the Vercel project already connected to "
    "woahwhattheheck/commons. Do not mint a new Vercel project. Alternative "
    "exact hosts: systemd integrations/owner_context/commons-owner-context.service "
    "; Docker integrations/owner_context/compose.yml ; Cloudflare Worker from "
    "integrations/owner_context/wrangler.toml.example (do not commit secrets). "
    "Then set owner.json context_host.public_url to the live HTTPS origin and "
    "re-run python3 host/owner_context.py doctor. GitHub Actions is not an "
    "always-on host. no auth. no gate. Display only."
)
ADAPTERS = {
    "local": [
        "python3 host/owner_context.py simulate",
        "python3 host/owner_context.py serve --bind localhost:8789",
    ],
    "systemd": [
        "sudo cp integrations/owner_context/commons-owner-context.service /etc/systemd/system/",
        "sudo systemctl enable --now commons-owner-context.service",
    ],
    "docker": [
        "docker compose -f integrations/owner_context/compose.yml up --build -d",
    ],
    "vercel": [
        "Existing host commons-spark-mcp.vercel.app. Merge vercel.json rewrite "
        "/owner-context -> api/owner_context.py onto current main.",
    ],
    "cloudflare": [
        "Copy integrations/owner_context/wrangler.toml.example to a gitignored "
        "wrangler.toml. wrangler deploy. Do not commit secrets.",
    ],
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime | None = None) -> str:
    return (ts or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def refuse_raw_ips(blob: str) -> None:
    text = str(blob or "")
    if IPV4_BLOB.search(text) or IPV6_BLOB.search(text):
        raise ValueError("owner-context blob would contain a raw IP — refusing")


def is_documentation_ip(ip: str) -> bool:
    n = owner_enroll.normalize_ip(ip)
    if any(n.startswith(p) for p in DOC_V4_PREFIXES):
        return True
    if n.lower().startswith(DOC_V6_PREFIX):
        return True
    return False


def normalize_via(raw) -> str:
    # Exact lowercase slot names only. Lookalikes (PC, phone , pc\\n) are not slots.
    v = str(raw or "")
    return v if v in VIAS else ""


def pepper_for(version: str = PEPPER_VERSION) -> str:
    return PEPPERS.get(str(version or ""), PEPPERS[PEPPER_VERSION])


def digest_ip(ip: str, version: str = PEPPER_VERSION) -> str:
    return owner_enroll.digest_ip(ip, pepper_for(version))


def extract_peer(headers, remote_addr: str = "") -> str:
    """Return a normalized IP for hashing, or empty. Caller must drop it."""
    headers = headers or {}

    def header(name: str) -> str:
        if hasattr(headers, "get"):
            got = headers.get(name) or headers.get(name.lower()) or headers.get(name.title())
            if got:
                return str(got)
            # email-message style
            try:
                got = headers.get(name, "")
            except TypeError:
                got = ""
            return str(got or "")
        return ""

    raw = header("CF-Connecting-IP") or header("X-Real-IP")
    if not raw:
        forwarded = header("X-Forwarded-For")
        if forwarded:
            raw = forwarded.split(",")[0]
    if not raw:
        raw = remote_addr or ""
    # host:port from BaseHTTPRequestHandler
    if raw.startswith("[") and "]" in raw:
        raw = raw[1:raw.index("]")]
    elif raw.count(":") == 1 and not raw.lower().startswith("2001:"):
        host, maybe_port = raw.rsplit(":", 1)
        if maybe_port.isdigit():
            raw = host
    ip = owner_enroll.normalize_ip(raw)
    if not owner_enroll.looks_like_ip(ip):
        return ""
    return ip


def matching_slot(spec: dict, digest: str) -> str:
    h = str(digest or "").strip().lower()
    if not HASH_RE.match(h):
        return ""
    slots = (spec or {}).get("slots") or {}
    pc = owner_net.slot_hash(slots.get("pc"))
    phone = owner_net.slot_hash(slots.get("phone"))
    if pc and h == pc:
        return "pc"
    if phone and h == phone:
        return "phone"
    return ""


class DigestCache:
    """Retention-bounded hash cache. Never stores a raw IP."""

    def __init__(self, retention_seconds: int = RETENTION_SECONDS, max_entries: int = CACHE_MAX):
        self.retention_seconds = int(retention_seconds)
        self.max_entries = int(max_entries)
        self.rows: dict[str, dict] = {}

    def prune(self, now: datetime | None = None) -> None:
        ts = (now or _now()).timestamp()
        dead = [
            key for key, row in self.rows.items()
            if ts - float(row.get("ts") or 0) > self.retention_seconds
        ]
        for key in dead:
            self.rows.pop(key, None)
        if len(self.rows) > self.max_entries:
            ordered = sorted(self.rows.items(), key=lambda item: float(item[1].get("ts") or 0))
            for key, _ in ordered[: len(self.rows) - self.max_entries]:
                self.rows.pop(key, None)

    def put(self, digest: str, slot: str, now: datetime | None = None) -> None:
        h = str(digest or "").strip().lower()
        if not HASH_RE.match(h):
            return
        stamp = now or _now()
        self.rows[h] = {"ts": stamp.timestamp(), "slot": normalize_via(slot), "iso": _iso(stamp)}
        self.prune(stamp)

    def get(self, digest: str, now: datetime | None = None) -> dict | None:
        self.prune(now)
        h = str(digest or "").strip().lower()
        return self.rows.get(h)


CACHE = DigestCache()


def load_spec(root: str | None = None) -> dict:
    path = os.path.join(root or ROOT, "owner.json")
    spec = owner_net.load_spec(path)
    host = spec.get("context_host")
    if not isinstance(host, dict):
        spec["context_host"] = {
            "k": KIND,
            "v": CONTRACT_V,
            "pepper_version": PEPPER_VERSION,
            "retention_seconds": RETENTION_SECONDS,
            "display_only": True,
            "authority": False,
            "gate": False,
            "public_url": "",
            "candidates": [DEFAULT_CANDIDATE],
            "status": "CODE_LANDED",
        }
    return spec


def context_payload(
    digest: str = "",
    slot: str = "",
    via_hint: str = "",
    available: bool = False,
    reason: str = "",
    host_name: str = "local",
    pepper_version: str = PEPPER_VERSION,
) -> dict:
    payload = {
        "k": KIND,
        "v": CONTRACT_V,
        "display_only": True,
        "authority": False,
        "gate": False,
        "claim_still": True,
        "available": bool(available),
        "pepper_version": str(pepper_version or PEPPER_VERSION),
        "sha256": digest if HASH_RE.match(str(digest or "")) else "",
        "slot": normalize_via(slot),
        "via_hint": normalize_via(via_hint),
        "host": str(host_name or "local"),
        "retention_seconds": RETENTION_SECONDS,
        "reason": str(reason or ""),
        "fresh": True,
    }
    refuse_raw_ips(json.dumps(payload))
    return payload


def annotate_context(
    headers=None,
    remote_addr: str = "",
    spec: dict | None = None,
    via_hint: str = "",
    host_name: str = "local",
    supplied_digest: str = "",
    now: datetime | None = None,
) -> dict:
    """Hash the peer, never the client-supplied digest, and annotate a slot."""
    spec = spec if spec is not None else load_spec()
    via_hint = normalize_via(via_hint)
    # Client-supplied digest is ignored for matching. Spoofing is not authority.
    _ = str(supplied_digest or "")
    ip = extract_peer(headers, remote_addr)
    if not ip:
        return context_payload(
            available=False,
            reason="no-peer",
            via_hint=via_hint,
            host_name=host_name,
        )
    digest = digest_ip(ip, PEPPER_VERSION)
    ip = ""  # drop
    slot = matching_slot(spec, digest)
    CACHE.put(digest, slot, now=now)
    return context_payload(
        digest=digest,
        slot=slot,
        via_hint=via_hint,
        available=True,
        host_name=host_name,
    )


def simulate(ip: str = "192.0.2.1", via: str = "pc", spec: dict | None = None, host_name: str = "simulate") -> dict:
    via = normalize_via(via)
    headers = {"X-Real-IP": ip}
    return annotate_context(headers=headers, spec=spec, via_hint=via, host_name=host_name)


def _read_qs_via(path: str) -> str:
    query = parse_qs(urlparse(path).query or "")
    values = query.get("via") or []
    return normalize_via(values[0] if values else "")


def _read_body_hint(body: bytes) -> tuple[str, str]:
    if not body:
        return "", ""
    try:
        obj = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeError):
        return "", ""
    if not isinstance(obj, dict):
        return "", ""
    return normalize_via(obj.get("via")), str(obj.get("sha256") or "")


CORS = (
    ("Access-Control-Allow-Origin", "*"),
    ("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD"),
    ("Access-Control-Allow-Headers", "*"),
    ("Access-Control-Max-Age", "600"),
    ("Cache-Control", "no-store"),
    ("X-Commons-Owner-Context", "display-only"),
)


def handle_http(
    method: str,
    path: str,
    headers=None,
    body: bytes = b"",
    remote_addr: str = "",
    spec: dict | None = None,
    host_name: str = "local",
) -> tuple[int, list[tuple[str, str]], bytes]:
    method = str(method or "GET").upper()
    parsed = urlparse(path or "/")
    route = (parsed.path or "/").rstrip("/") or "/"
    headers_out = list(CORS) + [("Content-Type", "application/json; charset=utf-8")]

    if method == "OPTIONS":
        blob = b""
        return 204, headers_out, blob

    if method not in ("GET", "POST", "HEAD"):
        # Display resource stays reachable. Any method still annotates. The door stays open.
        method = "GET"

    via_hint = _read_qs_via(path)
    body_via, supplied = _read_body_hint(body or b"")
    via_hint = via_hint or body_via

    if route in ("/doctor", "/owner-context/doctor"):
        payload = doctor(spec=spec, probe=False, host_name=host_name)
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        refuse_raw_ips(blob.decode("utf-8"))
        return 200, headers_out, blob

    if route in ("/health", "/owner-context/health"):
        payload = {
            "k": KIND,
            "ok": True,
            "display_only": True,
            "authority": False,
            "gate": False,
        }
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return 200, headers_out, blob

    if route not in ("/", "/context", "/owner-context", "/digest"):
        # Unknown path still returns the display JSON. Never 404-as-lock.
        pass

    payload = annotate_context(
        headers=headers,
        remote_addr=remote_addr,
        spec=spec,
        via_hint=via_hint,
        host_name=host_name,
        supplied_digest=supplied,
    )
    blob = json.dumps(payload, sort_keys=True).encode("utf-8")
    refuse_raw_ips(blob.decode("utf-8"))
    return 200, headers_out, blob


class OwnerContextHandler(BaseHTTPRequestHandler):
    spec = None
    host_name = "local"

    def _dispatch(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else b""
        remote = ""
        if self.client_address:
            remote = str(self.client_address[0] or "")
        status, headers, blob = handle_http(
            method,
            self.path,
            self.headers,
            body,
            remote,
            spec=self.spec,
            host_name=self.host_name,
        )
        self.send_response(status)
        for key, value in headers:
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        if method != "HEAD" and blob:
            self.wfile.write(blob)

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_OPTIONS(self) -> None:
        self._dispatch("OPTIONS")

    def do_HEAD(self) -> None:
        self._dispatch("HEAD")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def log_message(self, format, *args) -> None:  # noqa: A002
        return

    def log_request(self, code="-", size="-") -> None:
        return

    def log_error(self, format, *args) -> None:  # noqa: A002
        sys.stderr.write("owner-context error\n")


def serve(bind: str = "127.0.0.1:8789", spec: dict | None = None, host_name: str = "local") -> int:
    host, port_s = (bind or "127.0.0.1:8789").rsplit(":", 1)
    port = int(port_s)
    handler = OwnerContextHandler
    handler.spec = spec if spec is not None else load_spec()
    handler.host_name = host_name
    httpd = ThreadingHTTPServer((host, port), handler)
    print("owner-context display host on %s:%d (display only, no gate)" % (host, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def _exists(root: str, rel: str) -> bool:
    return os.path.isfile(os.path.join(root, rel))


def _read(root: str, rel: str) -> str:
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def measure_from_rows(facts: dict) -> dict:
    facts = facts or {}
    missing = [path for path in SEARCH_SPACE if not facts.get(path)]
    if missing:
        return {
            "state": FINDER_FAILED,
            "missing": missing,
            "search_space": list(SEARCH_SPACE),
            "note": "FINDER-FAILED plus the search space. Never 0.",
        }
    return {
        "state": "PRESENT",
        "missing": [],
        "search_space": list(SEARCH_SPACE),
        "note": "owner-context leftover files present",
    }


def classify(row: dict) -> dict:
    row = row or {}
    if row.get("state") == FINDER_FAILED:
        return {"state": "NOT_LANDED", "note": row.get("note") or FINDER_FAILED}
    if row.get("live"):
        return {"state": "LIVE", "note": "doctor-probed live display host"}
    if row.get("code_landed"):
        return {"state": "CODE_LANDED", "note": "adapter on tree; live URL is doctor-probed"}
    return {"state": FINDER_UNVERIFIED, "note": FINDER_UNVERIFIED}


def _probe_url(url: str, timeout: float = 8.0) -> dict:
    url = str(url or "").strip()
    if not url.startswith("https://"):
        return {"url": url, "http": 0, "live": False, "reason": "not-https"}
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "commons-owner-context-doctor"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = int(getattr(resp, "status", 200) or 200)
    except Exception as exc:  # noqa: BLE001 — doctor must not crash
        return {"url": url, "http": 0, "live": False, "reason": type(exc).__name__}
    try:
        refuse_raw_ips(raw)
    except ValueError:
        return {"url": url, "http": status, "live": False, "reason": "raw-ip"}
    try:
        obj = json.loads(raw)
    except ValueError:
        return {"url": url, "http": status, "live": False, "reason": "not-json"}
    live = (
        isinstance(obj, dict)
        and obj.get("k") == KIND
        and obj.get("authority") is False
        and obj.get("gate") is False
        and obj.get("display_only") is True
        and status == 200
    )
    return {"url": url, "http": status, "live": live, "reason": "" if live else "contract"}


def doctor(
    root: str | None = None,
    spec: dict | None = None,
    probe: bool = True,
    host_name: str = "local",
    env: dict | None = None,
) -> dict:
    root = root or ROOT
    spec = spec if spec is not None else load_spec(root)
    env = env if env is not None else os.environ
    facts = {path: _exists(root, path) for path in SEARCH_SPACE}
    measured = measure_from_rows(facts)
    cal_miss = [path for path in CALIBRATION if not _exists(root, path)]
    if cal_miss:
        measured = {
            "state": FINDER_UNVERIFIED,
            "missing": cal_miss,
            "search_space": list(CALIBRATION),
            "note": "calibration miss. FINDER-UNVERIFIED. Never 0.",
        }
    sim = simulate(spec=spec, host_name="simulate")
    host_cfg = spec.get("context_host") if isinstance(spec.get("context_host"), dict) else {}
    public_url = str(env.get("OWNER_CONTEXT_PUBLIC_URL") or host_cfg.get("public_url") or "").strip()
    candidates = []
    if public_url:
        candidates.append(public_url)
    for item in host_cfg.get("candidates") or [DEFAULT_CANDIDATE]:
        url = str(item or "").strip()
        if url and url not in candidates:
            candidates.append(url)
    probes = []
    live_url = ""
    if probe:
        for url in candidates:
            row = _probe_url(url)
            probes.append(row)
            if row.get("live") and not live_url:
                live_url = url
    code_landed = measured.get("state") == "PRESENT" and sim.get("k") == KIND
    live = bool(live_url)
    if live:
        state = "LIVE"
        action = ""
    elif code_landed:
        state = "CODE_LANDED"
        action = EXTERNAL_HOST_ACTION
    else:
        state = "NOT_LANDED"
        action = EXTERNAL_HOST_ACTION
    report = {
        "k": KIND,
        "display_only": True,
        "authority": False,
        "gate": False,
        "code_landed": code_landed,
        "local_sim": "PASS" if sim.get("available") else "FAIL",
        "slots_distinct": owner_net.distinct_live(spec),
        "public_url": live_url,
        "configured_public_url": public_url,
        "live": live,
        "state": state,
        "EXTERNAL_HOST_ACTION": action,
        "adapters": ADAPTERS,
        "probes": probes,
        "measure": measured,
        "host": host_name,
        "no_auth": True,
        "no_gate": True,
        "titan": "NOT_WRITTEN",
    }
    refuse_raw_ips(json.dumps(report))
    return report


def deployment_adapter(kind: str) -> dict:
    key = str(kind or "").strip().lower()
    commands = ADAPTERS.get(key)
    if not commands:
        return {
            "kind": key,
            "ok": False,
            "EXTERNAL_HOST_ACTION": EXTERNAL_HOST_ACTION,
        }
    needs_external = key in ("vercel", "cloudflare", "systemd", "docker")
    return {
        "kind": key,
        "ok": True,
        "commands": list(commands),
        "EXTERNAL_HOST_ACTION": EXTERNAL_HOST_ACTION if needs_external else "",
        "display_only": True,
        "authority": False,
        "gate": False,
    }


def _self_test() -> int:
    spec = {
        "claim": "BRYCE",
        "algo": "sha256",
        "pepper": "commons-owner-v1",
        "slots": {
            "pc": {"sha256": digest_ip("192.0.2.1")},
            "phone": {"sha256": digest_ip("2001:db8::1")},
        },
        "hashes": [],
        "context_host": {
            "k": KIND,
            "public_url": "",
            "candidates": [],
            "display_only": True,
            "authority": False,
            "gate": False,
        },
    }
    owner_net.refresh_hashes(spec)
    one = simulate("192.0.2.1", "pc", spec=spec)
    two = simulate("2001:db8::1", "phone", spec=spec)
    assert one["slot"] == "pc" and two["slot"] == "phone"
    assert one["authority"] is False and one["gate"] is False
    mixed = simulate("192.0.2.1", "phone", spec=spec)
    assert mixed["slot"] == "pc" and mixed["via_hint"] == "phone"
    status, _headers, blob = handle_http("GET", "/owner-context", {"X-Real-IP": "192.0.2.1"}, spec=spec)
    assert status == 200
    refuse_raw_ips(blob.decode("utf-8"))
    report = doctor(spec=spec, probe=False)
    assert report["state"] in ("CODE_LANDED", "NOT_LANDED", "LIVE")
    print("owner-context self-test PASS")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Optional owner-context display host. Display only.")
    parser.add_argument("command", nargs="?", default="doctor", choices=("doctor", "simulate", "serve", "adapter"))
    parser.add_argument("--bind", default=os.environ.get("OWNER_CONTEXT_BIND", "127.0.0.1:8789"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--probe", action="store_true", default=None)
    parser.add_argument("--no-probe", action="store_true")
    parser.add_argument("--adapter", default="local")
    parser.add_argument("--ip", default="")
    parser.add_argument("--via", default="pc")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--root", default="")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    if args.self_test or args.command == "doctor" and "--self-test" in (argv or sys.argv[1:]):
        if args.self_test:
            return _self_test()
    root = args.root or ROOT
    spec = load_spec(root)
    if args.command == "simulate":
        ip = args.ip or "192.0.2.1"
        if not is_documentation_ip(ip):
            print("simulate only accepts documentation-range fixtures", file=sys.stderr)
            return 2
        payload = simulate(ip, args.via, spec=spec)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "adapter":
        print(json.dumps(deployment_adapter(args.adapter), indent=2, sort_keys=True))
        return 0
    if args.command == "serve":
        return serve(args.bind, spec=spec)
    probe = True
    if args.no_probe:
        probe = False
    if args.probe:
        probe = True
    report = doctor(root=root, spec=spec, probe=probe)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("code_landed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
