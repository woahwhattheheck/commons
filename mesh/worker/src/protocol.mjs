import { createHash } from "node:crypto";

export const MAX_HOPS = 8;
export const NTFY_MAX_BYTES = 4096;

export function sha256Hex(text) {
  return createHash("sha256").update(String(text || ""), "utf8").digest("hex");
}

export function sizeOk(raw) {
  const n = Buffer.byteLength(typeof raw === "string" ? raw : JSON.stringify(raw), "utf8");
  return n <= NTFY_MAX_BYTES;
}

export class MemoryNode {
  constructor(nodeId) {
    this.node_id = nodeId;
    this.store = new Map();
    this.through_cursor = 0;
  }
  submit(env, fromNode = "") {
    const id = env.id || "";
    const body = env.body || "";
    if (!sizeOk(JSON.stringify(env))) {
      return { canonical_state: "REJECT_OVERSIZE", id };
    }
    const h = env.content_sha256 || sha256Hex(body);
    const path = Array.isArray(env.hop_path) ? [...env.hop_path] : [];
    if (path.includes(this.node_id)) return { canonical_state: "REJECT_LOOP", id };
    if (path.length >= MAX_HOPS) return { canonical_state: "REJECT_HOP_OVERFLOW", id };
    const got = this.store.get(id);
    if (got) {
      if (got.content_sha256 === h) {
        return { canonical_state: got.canonical_state || "MIRROR_RECEIVED", id, idempotent: true, content_sha256: h };
      }
      got.canonical_state = "QUARANTINED_CONFLICT";
      got.conflicts = got.conflicts || [];
      got.conflicts.push({ hash: h, from_node: fromNode, at: new Date().toISOString() });
      return { canonical_state: "QUARANTINED_CONFLICT", id };
    }
    const fresh = {
      ...env,
      content_sha256: h,
      hop_path: path.concat([this.node_id]),
      hop_count: path.length + 1,
      canonical_state: "MIRROR_RECEIVED",
      receipts: [...(env.receipts || []), { service: this.node_id, state: "MIRROR_RECEIVED", at: new Date().toISOString() }],
    };
    this.store.set(id, fresh);
    this.through_cursor += 1;
    return { canonical_state: "MIRROR_RECEIVED", id, idempotent: false, content_sha256: h };
  }
  read(id) {
    return this.store.get(id) || null;
  }
  feed() {
    return [...this.store.keys()].sort().map((k) => this.store.get(k));
  }
  health() {
    return { node_id: this.node_id, through_cursor: this.through_cursor, n: this.store.size };
  }
}
