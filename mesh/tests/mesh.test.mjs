import { MemoryNode, sha256Hex } from "../worker/src/protocol.mjs";
import test from "node:test";
import assert from "node:assert/strict";

test("idempotent same hash", () => {
  const a = new MemoryNode("local-a");
  const env = { id: "mesh-test-idempotent-20260818", from: "PLAYER1", to: "TABLE", body: "inert", origin_node: "local-a", content_sha256: sha256Hex("inert"), hop_path: [] };
  const s1 = a.submit(env);
  const s2 = a.submit(env);
  assert.equal(s1.canonical_state, "MIRROR_RECEIVED");
  assert.equal(s1.idempotent, false);
  assert.equal(s2.idempotent, true);
});

test("conflict quarantines", () => {
  const a = new MemoryNode("local-a");
  const env = { id: "mesh-test-conflict-20260818", from: "PLAYER1", to: "TABLE", body: "a", origin_node: "local-a", content_sha256: sha256Hex("a"), hop_path: [] };
  a.submit(env);
  const bad = { ...env, body: "b", content_sha256: sha256Hex("b") };
  const st = a.submit(bad);
  assert.equal(st.canonical_state, "QUARANTINED_CONFLICT");
});

test("loop reject", () => {
  const a = new MemoryNode("local-a");
  const b = new MemoryNode("local-b");
  const env = { id: "mesh-test-loop-20260818", from: "PLAYER1", to: "TABLE", body: "loop", origin_node: "local-a", content_sha256: sha256Hex("loop"), hop_path: [] };
  a.submit(env);
  const item = a.read(env.id);
  b.submit(item, "local-a");
  const back = a.submit(b.read(env.id), "local-b");
  assert.equal(back.canonical_state, "REJECT_LOOP");
});
