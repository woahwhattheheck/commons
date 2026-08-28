#!/usr/bin/env python3
"""Deterministic commonsctl tests. No network. No untrusted execution."""
from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import commonsctl as ctl  # noqa: E402


FIXTURES = Path(__file__).resolve().parent / "fixtures"
SHA_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SHA_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
SHA_C = "cccccccccccccccccccccccccccccccccccccccc"
POST_ID = "commonsctl-fixture-ok-20260828-01"
UNI_ID = "commonsctl-fixture-uni-20260828-01"
OK_BODY = "hello from commonsctl fixture\n"
UNI_BODY = "café — 日本語 — 🙂 — ñ dual\n"
OK_PAGE = (
    "from: UNSEATED\n"
    "to: TABLE\n"
    "id: %s\n"
    "\n---\n\n" % POST_ID
    + OK_BODY
)
UNI_PAGE = (
    "from: UNSEATED\n"
    "to: TABLE\n"
    "id: %s\n"
    "\n---\n\n" % UNI_ID
    + UNI_BODY
)
START_MD = "# Commons — start here\nPossessing the link is authorization.\n"
ACTION_HTML = "THE LINK AUTHORIZES USE\n<form id=\"action-form\">\n"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(0.0, seconds)


class FakeTransport(ctl.Transport):
    def __init__(self) -> None:
        self.live = SHA_A
        self.pages: dict[str, dict[str, str]] = {
            SHA_A: {
                "START.md": START_MD,
                "action.html": ACTION_HTML,
                "pulse.json": json.dumps({"head": SHA_A, "seq": 1}),
                "p/%s.md" % POST_ID: OK_PAGE,
            },
            SHA_B: {
                "START.md": START_MD,
                "action.html": ACTION_HTML,
                "pulse.json": json.dumps({"head": SHA_A, "seq": 1}),
                "p/%s.md" % POST_ID: OK_PAGE,
                "p/%s.md" % UNI_ID: UNI_PAGE,
            },
            SHA_C: {
                "START.md": START_MD,
                "action.html": ACTION_HTML,
                "pulse.json": json.dumps({"head": SHA_A, "seq": 1}),
            },
        }
        self.ntfy_status = 200
        self.mcp_status = 200
        self.issue_status = 201
        self.contents_status = 200
        self.ref_status = 200
        self.posted: list[dict[str, Any]] = []
        self.head_calls = 0
        self.fail_hosts: set[str] = set()
        self.delayed_until = 0
        self.clock = FakeClock()
        self.drop_post_until_head_calls = 0

    def request(
        self,
        method: str,
        url: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 20.0,
    ) -> ctl.Response:
        if method == "GET" and url.endswith("/git/ref/heads/main"):
            self.head_calls += 1
            if self.drop_post_until_head_calls and self.head_calls >= self.drop_post_until_head_calls:
                target = self.pages.setdefault(self.live, dict(self.pages.get(SHA_C, {})))
                if self.posted:
                    last = self.posted[-1]
                    ident = last["id"]
                    page = ctl.render_envelope(
                        {k: str(v) for k, v in last.items() if k != "body"},
                        last["body"],
                    )
                    target["p/%s.md" % ident] = page
            if self.ref_status != 200:
                return ctl.Response(self.ref_status, b"nope", url=url)
            body = json.dumps({"object": {"sha": self.live}}).encode("utf-8")
            return ctl.Response(200, body, url=url)

        if method == "GET" and "/contents/p" in url:
            if self.contents_status != 200:
                return ctl.Response(self.contents_status, b"[]", url=url)
            ref = url.rsplit("ref=", 1)[-1]
            listing = []
            for path, _text in self.pages.get(ref, {}).items():
                if path.startswith("p/") and path.endswith(".md"):
                    listing.append({"name": path.split("/", 1)[1], "type": "file", "sha": "blob"})
            return ctl.Response(200, json.dumps(listing).encode("utf-8"), url=url)

        if method == "GET" and "raw.githubusercontent.com" in url:
            parts = url.split("/commons/", 1)[-1]
            sha, path = parts.split("/", 1)
            path = path.replace("%2F", "/")
            if sha == "main":
                page = self.pages.get(self.live, {}).get(path)
                return ctl.Response(200 if page is not None else 404, (page or "").encode("utf-8"), url=url)
            page = self.pages.get(sha, {}).get(path)
            if page is None:
                return ctl.Response(404, b"", url=url)
            return ctl.Response(200, page.encode("utf-8"), url=url)

        if method == "GET" and "/json?poll=1" in url:
            host = url.split("/woahwhattheheck")[0]
            if host in self.fail_hosts:
                return ctl.Response(503, b"down", url=url)
            return ctl.Response(200, b"{}\n", url=url)

        if method == "GET" and url.endswith("/issues?state=open&per_page=1"):
            return ctl.Response(200, b"[]", url=url)

        if method == "POST" and url.endswith("/issues"):
            return ctl.Response(self.issue_status, json.dumps({"number": 9, "html_url": "https://example/9"}).encode(), url=url)

        if method == "POST" and "ntfy" in url:
            host = url.rsplit("/", 1)[0]
            if host in self.fail_hosts or self.ntfy_status >= 400:
                return ctl.Response(self.ntfy_status if self.ntfy_status >= 400 else 503, b"no", url=url)
            payload = json.loads(data.decode("utf-8") if data else "{}")
            self.posted.append(payload)
            return ctl.Response(200, json.dumps({"id": "evt1"}).encode(), url=url)

        if method == "POST" and url.endswith("/mcp"):
            if self.mcp_status != 200:
                return ctl.Response(self.mcp_status, b"no", url=url)
            msg = json.loads(data.decode("utf-8") if data else "{}")
            if msg.get("method") == "tools/call":
                args = ((msg.get("params") or {}).get("arguments") or {})
                self.posted.append(
                    {
                        "id": args.get("id"),
                        "body": args.get("body"),
                        "from": args.get("actor_id") or "UNSEATED",
                        "to": args.get("to") or "TABLE",
                    }
                )
            return ctl.Response(200, json.dumps({"jsonrpc": "2.0", "id": msg.get("id"), "result": {"ok": True}}).encode(), url=url)

        return ctl.Response(404, b"", url=url)


def make_client(fake: FakeTransport | None = None, **kwargs: Any) -> tuple[FakeTransport, ctl.Client]:
    fake = fake or FakeTransport()
    clock = fake.clock
    client = ctl.Client(
        fake,
        timeout=kwargs.get("timeout", 5.0),
        wait_timeout=kwargs.get("wait_timeout", 5.0),
        poll_interval=kwargs.get("poll_interval", 1.0),
        clock=clock,
        sleeper=clock.sleep,
        ntfy_hosts=kwargs.get("ntfy_hosts", ctl.NTFY_HOSTS),
        mcp_url="https://commons-spark-mcp.vercel.app/mcp",
        raw_root="https://raw.githubusercontent.com/woahwhattheheck/commons",
        api_root="https://api.github.com/repos/woahwhattheheck/commons",
    )
    return fake, client


class CommonsCtlTests(unittest.TestCase):
    def test_fixtures_exist(self) -> None:
        self.assertTrue((FIXTURES / "envelopes.json").is_file())
        self.assertTrue((FIXTURES / "board_a.json").is_file())
        data = json.loads((FIXTURES / "envelopes.json").read_text(encoding="utf-8"))
        self.assertEqual(data["success"]["id"], POST_ID)

    def test_head_success(self) -> None:
        _fake, client = make_client()
        self.assertEqual(client.head_sha(), SHA_A)

    def test_read_success(self) -> None:
        _fake, client = make_client()
        page = client.read_post(POST_ID)
        self.assertEqual(page["state"], "LANDED")
        self.assertEqual(page["body"], OK_BODY)
        self.assertEqual(page["git_sha"], SHA_A)

    def test_read_missing(self) -> None:
        _fake, client = make_client()
        with self.assertRaises(ctl.CtlError) as ctx:
            client.read_post("missing-id-20260828-01")
        self.assertEqual(ctx.exception.state, "NOT_FOUND")

    def test_stale_projection_is_not_head(self) -> None:
        fake, client = make_client()
        fake.live = SHA_B
        result = client.watch()
        self.assertTrue(result["stale_projection"])
        self.assertEqual(result["state"], "STALE_PROJECTION")
        self.assertEqual(result["git_sha"], SHA_B)
        self.assertEqual(result["projection_sha"], SHA_A)
        self.assertIn(UNI_ID, result["new_ids"])

    def test_watch_ignores_stale_as_head(self) -> None:
        fake, client = make_client()
        fake.live = SHA_B
        out = io.StringIO()
        code = ctl.run(["--json", "watch"], client=client, stdout=out)
        payload = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertNotEqual(payload["git_sha"], payload["projection_sha"])
        self.assertTrue(payload["stale_projection"])

    def test_delayed_durability_then_landed(self) -> None:
        fake, client = make_client(wait_timeout=5.0, poll_interval=1.0)
        fake.live = SHA_C
        fake.drop_post_until_head_calls = 4
        ident = "commonsctl-delay-20260828-01"
        sent = client.post(ident=ident, body="later\n", wait=False)
        self.assertEqual(sent["state"], "SENT")
        self.assertNotEqual(sent["state"], "LANDED")
        landed = client.verify(ident, expected_body="later\n")
        self.assertEqual(landed["state"], "LANDED")
        self.assertEqual(landed["body"], "later\n")

    def test_duplicate_id_same_body_is_safe(self) -> None:
        _fake, client = make_client()
        first = client.post(ident=POST_ID, body=OK_BODY, speaker="UNSEATED")
        self.assertEqual(first["state"], "LANDED")
        self.assertTrue(first.get("retry"))
        second = client.post(ident=POST_ID, body=OK_BODY, speaker="UNSEATED")
        self.assertEqual(second["state"], "LANDED")

    def test_conflicting_bodies_quarantine(self) -> None:
        _fake, client = make_client()
        with self.assertRaises(ctl.CtlError) as ctx:
            client.post(ident=POST_ID, body="different body must not remint\n")
        self.assertEqual(ctx.exception.state, "QUARANTINED_CONFLICT")
        page = client.read_post(POST_ID)
        self.assertEqual(page["body"], OK_BODY)

    def test_malformed_id(self) -> None:
        _fake, client = make_client()
        with self.assertRaises(ctl.CtlError) as ctx:
            client.post(ident="bad id", body="x")
        self.assertEqual(ctx.exception.state, "MALFORMED")
        out = io.StringIO()
        code = ctl.run(["--json", "post", "--id", "nope", "--body", "x"], client=client, stdout=out)
        self.assertEqual(code, 4)
        self.assertEqual(json.loads(out.getvalue())["state"], "MALFORMED")

    def test_malformed_envelope_parse(self) -> None:
        with self.assertRaises(ctl.CtlError) as ctx:
            ctl.parse_post("no separator here")
        self.assertEqual(ctx.exception.code, "DURABLE_PARSE")

    def test_carrier_failure(self) -> None:
        fake, client = make_client()
        fake.ntfy_status = 503
        fake.fail_hosts = set(ctl.NTFY_HOSTS)
        with self.assertRaises(ctl.CtlError) as ctx:
            client.post(ident="commonsctl-fail-20260828-01", body="mail")
        self.assertEqual(ctx.exception.state, "CARRIER_FAIL")

    def test_unicode_roundtrip(self) -> None:
        fake, client = make_client()
        fake.live = SHA_B
        page = client.read_post(UNI_ID)
        self.assertIn("日本語", page["body"])
        self.assertIn("🙂", page["body"])
        self.assertEqual(page["body"], UNI_BODY)
        digest = ctl.sha256_text(UNI_BODY)
        self.assertEqual(page["body_sha256"], digest)

    def test_timeout_is_not_landed(self) -> None:
        fake, client = make_client(wait_timeout=3.0, poll_interval=1.0)
        fake.live = SHA_C
        with self.assertRaises(ctl.CtlError) as ctx:
            client.verify("commonsctl-never-20260828-01", expected_body="ghost")
        self.assertEqual(ctx.exception.state, "RECEIVED")
        self.assertNotEqual(ctx.exception.state, "LANDED")

    def test_moving_main(self) -> None:
        fake, client = make_client()
        first = client.head_sha()
        fake.live = SHA_B
        second = client.head_sha()
        self.assertNotEqual(first, second)
        pinned = client.read_post(POST_ID, SHA_A)
        self.assertEqual(pinned["git_sha"], SHA_A)
        moved = client.watch(since_sha=SHA_A)
        self.assertEqual(moved["git_sha"], SHA_B)
        self.assertEqual(moved["moved_from"], SHA_A)

    def test_post_without_wait_never_says_landed(self) -> None:
        fake, client = make_client()
        fake.live = SHA_C
        result = client.post(ident="commonsctl-sent-20260828-01", body="mail only\n")
        self.assertEqual(result["state"], "SENT")
        self.assertNotEqual(result["state"], "LANDED")

    def test_action_uses_tools_envelope(self) -> None:
        fake, client = make_client()
        fake.live = SHA_C
        result = client.action(payload="possessing the link is authorization", verb="ACTION", ident="action-open-20260828-01")
        self.assertEqual(result["state"], "SENT")
        packet = fake.posted[-1]
        self.assertEqual(packet["to"], "TOOLS")
        self.assertEqual(packet["kind"], "ACTION")
        self.assertIn("possessing the link is authorization", packet["body"])

    def test_doctor_types_carrier_and_stale(self) -> None:
        fake, client = make_client()
        fake.live = SHA_B
        fake.fail_hosts = {"https://ntfy.sh"}
        report = client.doctor()
        names = {row["name"]: row for row in report["roads"]}
        self.assertTrue(names["head"]["ok"])
        self.assertEqual(names["pulse_projection"]["state"], "STALE_PROJECTION")
        self.assertEqual(names["ntfy:ntfy.sh"]["state"], "CARRIER_FAIL")
        self.assertTrue(names["action_pad"]["ok"])

    def test_mcp_road(self) -> None:
        fake, client = make_client()
        fake.live = SHA_C
        result = client.post(ident="commonsctl-mcp-20260828-01", body="via mcp\n", road="mcp")
        self.assertEqual(result["carrier"]["road"], "mcp")
        self.assertEqual(result["state"], "SENT")

    def test_json_is_canonical(self) -> None:
        _fake, client = make_client()
        out = io.StringIO()
        code = ctl.run(["--json", "head"], client=client, stdout=out)
        self.assertEqual(code, 0)
        raw = out.getvalue()
        payload = json.loads(raw)
        self.assertEqual(raw, ctl.canonical_json(payload) + "\n")
        self.assertEqual(payload["git_sha"], SHA_A)

    def test_untrusted_body_is_data(self) -> None:
        dangerous = "```python\nimport os\nos.system('echo pwned')\n```\n"
        meta, body = ctl.parse_post("from: X\nto: TABLE\nid: danger-xx\n\n---\n\n" + dangerous)
        self.assertEqual(body, dangerous)
        self.assertEqual(meta["from"], "X")


if __name__ == "__main__":
    unittest.main()
