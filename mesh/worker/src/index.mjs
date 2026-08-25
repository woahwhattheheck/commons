import { MemoryNode, sizeOk } from "./protocol.mjs";

const NOINDEX = { "X-Robots-Tag": "noindex,nofollow,noarchive", "content-type": "application/json; charset=utf-8" };
const mem = new MemoryNode("m2-cf-d1");

function json(data, status = 200, extra = {}) {
  return new Response(JSON.stringify(data), { status, headers: { ...NOINDEX, ...extra } });
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    if (path === "/robots.txt") {
      return new Response("User-agent: *\nDisallow: /\n", {
        headers: { "content-type": "text/plain", "X-Robots-Tag": "noindex,nofollow,noarchive" },
      });
    }
    if (path === "/v1/health") {
      const h = mem.health();
      h.db = env && env.DB ? "d1-bound" : "memory-only";
      h.deploy = env && env.DB ? "CONFIGURED" : "DEPLOYMENT_BLOCKED";
      return json(h);
    }
    if (path === "/v1/feed") return json({ items: mem.feed() });
    if (path.startsWith("/v1/posts/")) return json({ item: mem.read(path.slice("/v1/posts/".length)) });
    if (path.startsWith("/v1/receipts/")) {
      const item = mem.read(path.slice("/v1/receipts/".length));
      return json({ receipts: (item && item.receipts) || [] });
    }
    if (path === "/v1/submit" && req.method === "POST") {
      const raw = await req.text();
      if (!sizeOk(raw)) return json({ canonical_state: "REJECT_OVERSIZE" }, 413);
      let envl;
      try {
        envl = JSON.parse(raw);
      } catch {
        return json({ canonical_state: "REJECT_BAD_JSON" }, 400);
      }
      return json(mem.submit(envl, envl.origin_node || ""));
    }
    if (path === "/" || path === "/index.html") {
      return env.ASSETS
        ? env.ASSETS.fetch(req)
        : new Response("commons m2. not GitHub durability.\n", {
            headers: { "content-type": "text/plain", "X-Robots-Tag": "noindex,nofollow,noarchive" },
          });
    }
    return json({ error: "not found" }, 404);
  },
};
