"""COMMONS_MIRROR_MESH_0 core. Provider-neutral. No credentials."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

MAX_HOPS = 8
NTFY_MAX_BYTES = 4096
NTFY_RETENTION = "official ntfy default is ~12h and 4096-byte messages; not a 72h recovery mirror"
STATES = (
    "MIRROR_RECEIVED",
    "FORWARDED",
    "DURABLE_PAGE",
    "PUBLICATION_PENDING",
    "CONFLICT",
    "QUARANTINED_CONFLICT",
    "REJECT_LOOP",
    "REJECT_HOP_OVERFLOW",
    "REJECT_OVERSIZE",
)


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def content_sha256(body: str) -> str:
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


def size_ok(raw: str | bytes) -> bool:
    if isinstance(raw, bytes):
        return len(raw) <= NTFY_MAX_BYTES
    return len((raw or "").encode("utf-8")) <= NTFY_MAX_BYTES


def envelope(
    *,
    id,
    frm,
    to,
    body,
    origin_node,
    lane="",
    supersedes="",
    hop_path=None,
    receipts=None,
):
    hop_path = list(hop_path or [])
    return {
        "id": id,
        "from": frm,
        "to": to,
        "body": body,
        "lane": lane or "",
        "supersedes": supersedes or "",
        "content_sha256": content_sha256(body),
        "origin_node": origin_node,
        "observed_at": utcnow(),
        "hop_count": len(hop_path),
        "hop_path": hop_path,
        "receipts": list(receipts or []),
    }


class Node:
    def __init__(self, node_id):
        self.node_id = node_id
        self.store = {}
        self.conflicts = {}
        self.outbox = {}
        self.through_cursor = 0
        self.generated_at = utcnow()

    def health(self):
        return {
            "node_id": self.node_id,
            "through_cursor": self.through_cursor,
            "generated_at": utcnow(),
            "n": len(self.store),
            "ntfy_retention": NTFY_RETENTION,
            "note": "local/mesh node. not GitHub durability.",
        }

    def read(self, mid):
        return self.store.get(mid)

    def feed(self):
        return [self.store[k] for k in sorted(self.store)]

    def submit(self, env, *, from_node=""):
        mid = env.get("id") or ""
        body = env.get("body") or ""
        if not size_ok(json.dumps(env, ensure_ascii=True)):
            return {"canonical_state": "REJECT_OVERSIZE", "id": mid}
        h = env.get("content_sha256") or content_sha256(body)
        path = list(env.get("hop_path") or [])
        if self.node_id in path:
            return {"canonical_state": "REJECT_LOOP", "id": mid}
        if len(path) >= MAX_HOPS:
            return {"canonical_state": "REJECT_HOP_OVERFLOW", "id": mid}
        got = self.store.get(mid)
        if got:
            if got["content_sha256"] == h:
                rec = {"service": self.node_id, "state": "IDEMPOTENT", "at": utcnow()}
                got.setdefault("receipts", []).append(rec)
                return {
                    "canonical_state": got.get("canonical_state") or "MIRROR_RECEIVED",
                    "id": mid,
                    "idempotent": True,
                    "content_sha256": h,
                }
            got["canonical_state"] = "QUARANTINED_CONFLICT"
            row = {"hash": h, "from_node": from_node, "at": utcnow()}
            got.setdefault("conflicts", []).append(row)
            self.conflicts.setdefault(mid, []).append(row)
            return {"canonical_state": "QUARANTINED_CONFLICT", "id": mid}
        fresh = dict(env)
        fresh["content_sha256"] = h
        fresh["hop_path"] = path + [self.node_id]
        fresh["hop_count"] = len(fresh["hop_path"])
        fresh["canonical_state"] = "MIRROR_RECEIVED"
        fresh.setdefault("receipts", []).append(
            {"service": self.node_id, "state": "MIRROR_RECEIVED", "at": utcnow()}
        )
        self.store[mid] = fresh
        self.outbox[mid] = fresh
        self.through_cursor += 1
        return {
            "canonical_state": "MIRROR_RECEIVED",
            "id": mid,
            "idempotent": False,
            "content_sha256": h,
        }

    def forward(self, mid, other):
        env = self.store.get(mid)
        if not env:
            return {"canonical_state": "MISSING", "id": mid}
        if env.get("canonical_state") == "QUARANTINED_CONFLICT":
            return {"canonical_state": "QUARANTINED_CONFLICT", "id": mid}
        st = other.submit(env, from_node=self.node_id)
        if st.get("canonical_state") == "MIRROR_RECEIVED" and not st.get("idempotent"):
            env["canonical_state"] = "FORWARDED"
            env.setdefault("receipts", []).append(
                {"service": self.node_id, "state": "FORWARDED", "to": other.node_id, "at": utcnow()}
            )
        return st

    def mark_pending(self, mid):
        env = self.store.get(mid)
        if not env:
            return {"canonical_state": "MISSING", "id": mid}
        env["canonical_state"] = "PUBLICATION_PENDING"
        env.setdefault("receipts", []).append(
            {"service": self.node_id, "state": "PUBLICATION_PENDING", "at": utcnow()}
        )
        return {"canonical_state": "PUBLICATION_PENDING", "id": mid}

    def mark_durable(self, mid, github_receipt):
        env = self.store.get(mid)
        if not env:
            return {"canonical_state": "MISSING", "id": mid}
        env["canonical_state"] = "DURABLE_PAGE"
        self.outbox.pop(mid, None)
        env.setdefault("receipts", []).append(
            {"service": "github", "state": "DURABLE_PAGE", "at": utcnow(), "receipt": github_receipt}
        )
        return {"canonical_state": "DURABLE_PAGE", "id": mid}

    def capsule(self):
        items = self.feed()
        blob = json.dumps(items, sort_keys=True, ensure_ascii=True)
        return {
            "node_id": self.node_id,
            "high_water": self.through_cursor,
            "n": len(items),
            "manifest_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
            "generated_at": utcnow(),
            "items": items,
        }


class FileNode(Node):
    """Restart-persistent local node. Not a public M3 host."""

    def __init__(self, node_id, path):
        super().__init__(node_id)
        self.path = path
        self._load()

    def _load(self):
        if not os.path.isfile(self.path):
            return
        data = json.loads(open(self.path, encoding="utf-8").read())
        self.store = data.get("store") or {}
        self.conflicts = data.get("conflicts") or {}
        self.outbox = data.get("outbox") or {}
        self.through_cursor = int(data.get("through_cursor") or 0)

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        payload = {
            "store": self.store,
            "conflicts": self.conflicts,
            "outbox": self.outbox,
            "through_cursor": self.through_cursor,
            "saved_at": utcnow(),
        }
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(payload, ensure_ascii=True, indent=2))
            f.write("\n")

    def submit(self, env, *, from_node=""):
        st = super().submit(env, from_node=from_node)
        self._save()
        return st


def run_fixture():
    a = Node("local-a")
    b = Node("local-b")
    env = envelope(
        id="mirror-fixture-idempotent-20260818",
        frm="PLAYER1",
        to="TABLE",
        body="MIRROR_MESH_0 local fixture. inert.",
        origin_node="local-a",
    )
    s1 = a.submit(env)
    s2 = a.submit(env)
    assert s1["canonical_state"] == "MIRROR_RECEIVED" and not s1.get("idempotent")
    assert s2.get("idempotent") is True
    fwd = a.forward(env["id"], b)
    assert fwd["canonical_state"] == "MIRROR_RECEIVED"
    loop = b.forward(env["id"], a)
    assert loop["canonical_state"] == "REJECT_LOOP"
    bad = dict(env)
    bad["body"] = "altered"
    bad["content_sha256"] = content_sha256(bad["body"])
    conflict = a.submit(bad)
    assert conflict["canonical_state"] == "QUARANTINED_CONFLICT"
    pending = b.mark_pending(env["id"])
    assert pending["canonical_state"] == "PUBLICATION_PENDING"
    durable = b.mark_durable(env["id"], "p/%s.html" % env["id"])
    assert durable["canonical_state"] == "DURABLE_PAGE"
    huge = envelope(
        id="mirror-fixture-oversize-20260818",
        frm="PLAYER1",
        to="TABLE",
        body="x" * 5000,
        origin_node="local-a",
    )
    over = a.submit(huge)
    assert over["canonical_state"] == "REJECT_OVERSIZE"
    cap = b.capsule()
    assert cap["n"] == 1 and cap["manifest_sha256"]
    import tempfile
    tdir = tempfile.mkdtemp()
    pth = os.path.join(tdir, "m3.json")
    f1 = FileNode("local-file", pth)
    f1.submit(env)
    f2 = FileNode("local-file", pth)
    assert f2.read(env["id"]) is not None
    e2 = envelope(
        id="mirror-fixture-concurrent-b-20260818",
        frm="PLAYER1",
        to="TABLE",
        body="second distinct event",
        origin_node="local-a",
    )
    c1 = a.submit(e2)
    assert c1["canonical_state"] == "MIRROR_RECEIVED"
    assert a.read(env["id"])["id"] != a.read(e2["id"])["id"]
    cap2 = a.capsule()
    assert cap2["n"] >= 2
    print("mirror_mesh_fixture ok", json.dumps({
        "a": a.health(),
        "b": b.health(),
        "loop": loop,
        "conflict": conflict,
        "capsule": {"n": cap["n"], "sha256": cap["manifest_sha256"]},
        "oversize": over,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_fixture())
