import assert from "node:assert/strict";
import http from "node:http";
import { once } from "node:events";
import { test } from "node:test";
import { createReadTransport, createRpcDispatcher } from "./read-transport.mjs";

const counts = new Map();
const fixtureHead = "a".repeat(40);
const server = http.createServer(async (req, res) => {
  const pathname = new URL(req.url, "http://localhost").pathname;
  counts.set(pathname, (counts.get(pathname) || 0) + 1);
  res.setHeader("content-type", "application/json");
  if (pathname === "/limited") {
    res.writeHead(429, { "retry-after": "2" }); res.end('{"error":"rate_limited"}'); return;
  }
  if (pathname === "/absent") { res.writeHead(404); res.end("{}"); return; }
  if (pathname === "/large-declared") {
    res.writeHead(200, { "content-length": String(32 * 1024 * 1024 + 1) }); res.end(); return;
  }
  if (pathname === "/large-stream") {
    const chunk = Buffer.alloc(1024 * 1024, 65);
    for (let i = 0; i < 33 && !res.destroyed; i++) {
      if (!res.write(chunk)) await new Promise(resolve => {
        const done = () => { res.off("drain", done); res.off("close", done); resolve(); };
        res.once("drain", done); res.once("close", done);
      });
    }
    res.end(); return;
  }
  if (pathname === "/feed-sized") { res.end('"' + "a".repeat(18680051) + '"'); return; }
  if (pathname.endsWith("/commits/main")) { res.end(JSON.stringify({ sha: fixtureHead })); return; }
  if (pathname.endsWith("harnesses/catalog.json")) {
    res.end(JSON.stringify({ harnesses: [], capabilities: [], roads: [] })); return;
  }
  if (pathname.endsWith("posts.json") || pathname.endsWith("recent.json")) {
    await new Promise(resolve => setTimeout(resolve, 15));
    res.end(JSON.stringify(Array.from({ length: 30 }, (_, i) => ({ id: "fixture-" + i, subject: "sample " + i, body: "synthetic" })))); return;
  }
  res.end('{"value":"synthetic"}');
});
server.listen(0, "127.0.0.1");
await once(server, "listening");
const base = "http://127.0.0.1:" + server.address().port;
process.env.COMMONS_RAW_BASE = base;
process.env.COMMONS_PAGES_BASE = base;
process.env.COMMONS_GITHUB_API_BASE = base;
process.env.COMMONS_GITHUB_RAW_BASE = base;
process.env.COMMONS_GITHUB_SMART_HTTP_BASE = base;
delete process.env.COMMONS_GITHUB_TOKEN;
const { handleRpc } = await import("./server.mjs");
const call = async (name, args) => (await handleRpc({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } })).result;

try {
  await test("cached observations remain usable during provider cooldown", async () => {
    const transport = createReadTransport();
    const first = await transport.fetchState(base + "/cached-during-throttle");
    assert.equal(first.ok, true);
    await transport.fetchState(base + "/limited");
    const cached = await transport.fetchState(base + "/cached-during-throttle");
    assert.equal(cached.ok, true);
    assert.equal(cached.cache.status, "hit");
    const fresh = await transport.fetchState(base + "/cached-during-throttle", {}, { fresh: true });
    assert.equal(fresh.error, "provider_cooldown");
    const stillCached = await transport.fetchState(base + "/cached-during-throttle");
    assert.equal(stillCached.cache.status, "hit");
    assert.equal(counts.get("/cached-during-throttle"), 1);
  });
  await test("five feed queries and pagination reuse one real HTTP read", async () => {
    for (let i = 0; i < 5; i++) {
      const result = await call("search_posts", { query: "sample", offset: i, limit: 2 });
      assert.equal(result.isError, false);
      assert.equal(result.structuredContent.posts[0].id, "fixture-" + i);
      assert.equal(result.structuredContent.cache.status, i === 0 ? "miss" : "hit");
      assert.ok(result.structuredContent.observed_at);
    }
    assert.equal(counts.get("/posts.json"), 1);
  });
  await test("concurrent identical GETs are single-flight", async () => {
    const results = await Promise.all(Array.from({ length: 5 }, () => call("read_recent", { limit: 1 })));
    assert.equal(counts.get("/recent.json"), 1);
    assert.equal(results.filter(r => r.structuredContent.cache.status === "coalesced").length, 4);
  });
  await test("explicit fresh bypasses cached feed and is advertised", async () => {
    const out = await call("search_posts", { query: "sample", fresh: true });
    assert.equal(out.structuredContent.cache.status, "fresh");
    assert.equal(counts.get("/posts.json"), 2);
    const listing = await handleRpc({ jsonrpc: "2.0", id: 2, method: "tools/list" });
    assert.equal(listing.result.tools.find(t => t.name === "search_posts").inputSchema.properties.fresh.type, "boolean");
  });
  await test("head identity is reused; fresh repeats head and immutable-body observation", async () => {
    const first = await call("discover_commons_capabilities", {});
    const second = await call("discover_commons_capabilities", {});
    assert.equal(first.structuredContent.git_sha, fixtureHead);
    assert.equal(second.structuredContent.head_cache.status, "hit");
    assert.ok(second.structuredContent.publication_terms);
    assert.equal(counts.get("/repos/woahwhattheheck/commons/commits/main"), 1);
    assert.equal(counts.get("/woahwhattheheck/commons/" + fixtureHead + "/harnesses/catalog.json"), 1);
    await call("discover_commons_capabilities", { fresh: true });
    assert.equal(counts.get("/repos/woahwhattheheck/commons/commits/main"), 2);
    assert.equal(counts.get("/woahwhattheheck/commons/" + fixtureHead + "/harnesses/catalog.json"), 2);
  });
  await test("current 18.7 MB feed size fits the bounded streaming reader", async () => {
    const transport = createReadTransport();
    const result = await transport.fetchState(base + "/feed-sized");
    assert.equal(result.ok, true);
    assert.equal(result.body.length, 18680053);
    assert.ok(transport.stats().bytes <= 64 * 1024 * 1024);
  });
  await test("oversized declared and chunked bodies abort at 32 MiB", async () => {
    const transport = createReadTransport();
    for (const endpoint of ["/large-declared", "/large-stream"]) {
      const result = await transport.fetchState(base + endpoint);
      assert.equal(result.ok, false);
      assert.match(result.error, /exceeded max_bytes/);
      assert.equal(result.body, undefined);
    }
    assert.equal(transport.stats().entries, 0);
  });
  await test("provider Retry-After defers repeated and fresh reads until deadline", async () => {
    let clock = Date.now();
    const transport = createReadTransport({ clock: () => clock });
    const before = counts.get("/limited") || 0;
    const first = await transport.fetchState(base + "/limited");
    assert.equal(first.status, 429);
    const deferred = await transport.fetchState(base + "/limited", {}, { fresh: true });
    assert.equal(deferred.error, "provider_cooldown");
    assert.equal(counts.get("/limited"), before + 1);
    clock += 2001;
    await transport.fetchState(base + "/limited");
    assert.equal(counts.get("/limited"), before + 2);
  });
  await test("404 is not retained as permanent absence", async () => {
    const transport = createReadTransport(), before = counts.get("/absent") || 0;
    await transport.fetchState(base + "/absent"); await transport.fetchState(base + "/absent");
    assert.equal(counts.get("/absent"), before + 2);
    assert.equal(transport.stats().entries, 0);
  });
  await test("authenticated responses and mutations are never cached or replayed", async () => {
    const transport = createReadTransport();
    for (const init of [{ headers: { authorization: "Bearer synthetic-fixture" } }, { method: "POST", body: "{}" }]) {
      await transport.fetchState(base + "/private", init);
      await transport.fetchState(base + "/private", init);
      assert.equal(transport.stats().entries, 0);
    }
    assert.equal(counts.get("/private"), 4);
  });
  await test("cache entry and byte budgets evict; TTL expires", async () => {
    let clock = Date.now();
    const transport = createReadTransport({ maxEntries: 2, maxCacheBytes: 100, clock: () => clock });
    for (const suffix of ["a", "b", "c"]) await transport.fetchState(base + "/small-" + suffix);
    assert.ok(transport.stats().entries <= 2); assert.ok(transport.stats().bytes <= 100);
    const before = counts.get("/small-c"); clock += 10001;
    assert.equal((await transport.fetchState(base + "/small-c")).cache.status, "miss");
    assert.equal(counts.get("/small-c"), before + 1);
  });
  await test("a delayed older request cannot replace an explicit fresh observation", async () => {
    let releaseOld, request = 0;
    // Capture each request's body independently of completion order.
    const delayedTransport = createReadTransport({ fetchImpl: async () => {
      const body = ++request === 1 ? "old" : "new";
      if (body === "old") await new Promise(resolve => { releaseOld = resolve; });
      return new Response(body, { headers: { "content-type": "text/plain" } });
    } });
    const old = delayedTransport.fetchState(base + "/race");
    const fresh = await delayedTransport.fetchState(base + "/race", {}, { fresh: true });
    assert.equal(fresh.text, "new");
    releaseOld(); assert.equal((await old).text, "old");
    assert.equal((await delayedTransport.fetchState(base + "/race")).text, "new");
  });
  await test("metadata and reads complete while writes preserve order", async () => {
    let finishWrite;
    const events = [], wait = new Promise(resolve => { finishWrite = resolve; });
    const dispatch = createRpcDispatcher(async message => {
      events.push(message);
      if (message === "write1") await wait;
      return message;
    }, { isMetadata: m => m === "ping", isRead: m => m === "read" });
    const first = dispatch("write1"), second = dispatch("write2");
    assert.equal(await dispatch("ping"), "ping");
    assert.equal(await dispatch("read"), "read");
    assert.equal(events.includes("write2"), false);
    finishWrite(); await first; await second;
    assert.ok(events.indexOf("write1") < events.indexOf("write2"));
  });
} finally {
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
