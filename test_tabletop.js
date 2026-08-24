// Spatial tabletop projection tests. No network calls.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

const src = fs.readFileSync(path.join(__dirname, "tabletop.js"), "utf8");
const html = fs.readFileSync(path.join(__dirname, "tabletop.html"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "tabletop.css"), "utf8");
const sandbox = { globalThis: {}, window: undefined, document: undefined };
sandbox.globalThis = sandbox;
vm.runInNewContext(src, sandbox);
const api = sandbox.COMMONS_TABLETOP;
assert(api && api.token, "tabletop exports typed token builders");

const head = api.tokensFromHead("83c024423c6fda8a5891d2bae2f0e0f52b510421");
assert(head.length === 1 && head[0].state === "INTEGRATED", "named main SHA is one integrated HEAD token");
assert(head[0].href.includes("/commit/83c024423c6f"), "HEAD token links the exact commit");

const presence = Array.from({ length: 30 }, (_, i) => ({
  from: "AGENT_" + String(i).padStart(2, "0"),
  presence: i === 29 ? "LEAVING" : "PRESENT",
  id: "presence-" + String(i).padStart(2, "0")
}));
const recent = presence.slice(0, 4).map((row, i) => ({
  from: row.from,
  id: "recent-" + i,
  href: "./p/recent-" + i + ".html",
  to: i ? "TOOLS" : "TABLE",
  ts: "2026-08-24T15:0" + i + ":00Z"
}));
const agents = api.tokensFromPresence(presence, recent);
assert(agents.length === 30, "all declared agents are represented without a 12-token cap");
assert(agents[0].state === "PRESENT" && agents[0].state !== "CLAIMED", "speaker identity is not relabelled as a claim");
assert(agents.some((row) => row.state === "LEAVING"), "declared leaving status stays visible");
assert(agents.some((row) => /TOOLS|TABLE/.test(row.detail)), "latest measured route is agent context");

const claims = api.tokensFromClaims({ claims: [
  { id: "claim-one-20260824", from: "RIVET", claim: "path a at HEAD abc", status: "OPEN", href: "./p/claim-one-20260824.html" },
  { id: "claim-two-20260824", from: "RIVET", claim: "path b at HEAD def", status: "OPEN", href: "./p/claim-two-20260824.html" },
  { id: "claim-closed-20260824", from: "RIVET", claim: "settled", status: "CLOSED" }
] });
assert(claims.length === 2, "distinct active claims by one agent are preserved");
assert(claims.every((row) => row.state === "OPEN"), "closed claims stay off the active map");

const directives = `
### 19. Agent Swarm
**Status:** OPEN waiting on a builder.

### 20. Pending Owner Walls
**Status:** SPEC'D requires owner input.

### 21. Permanent law
**Status:** LANDED this commit.

### 22. Partial road
**Status:** PARTIAL one endpoint remains.
`;
const todos = api.tokensFromTodos(directives);
assert(todos.length === 3, "OPEN, SPEC'D, and PARTIAL directives become TODO tokens");
assert(!todos.some((row) => row.id === "directive-21"), "LANDED directive is excluded from open TODO");

const trafficRows = [];
for (let i = 0; i < 5; i++) trafficRows.push({ to: "TABLE" });
for (let i = 0; i < 3; i++) trafficRows.push({ board: "TOOLS" });
for (let i = 0; i < 2; i++) trafficRows.push({ lane: "VENT" });
trafficRows.push({ to: "BRYCE" });
const traffic = api.tokensFromTraffic(trafficRows);
const byRoute = Object.fromEntries(traffic.map((row) => [row.id, row]));
assert(byRoute.TABLE.state === "HEAVY" && /· 5$/.test(byRoute.TABLE.label), "busiest route is HEAVY with its exact count");
assert(byRoute.INBOX.detail.startsWith("1 event"), "person-directed traffic is counted as INBOX, not invented lanes");
assert(byRoute.COURT.state === "CLEAR" && /· 0$/.test(byRoute.COURT.label), "known zero-event route is explicitly CLEAR");

assert(api.safeHref("javascript:alert(1)", "./head.html") === "./head.html", "unsafe token href falls back to a local door");
assert(api.safeHref("./p/x.html", "./head.html") === "./p/x.html", "canonical local post href remains usable");

["head", "agent", "claim", "todo", "traffic"].forEach((kind) => {
  assert(html.includes(`data-field="${kind}"`), kind + " zone exists");
});
assert(html.includes('id="tabletop-refresh"'), "explicit live refresh control exists");
assert(html.includes('id="tabletop-reset"'), "persisted token layout has a reset control");
assert(/No login or token/i.test(html), "open door is explicit");
assert(/min-height:44px/.test(css) && /width:44px/.test(css), "mobile controls and drag handles meet 44px target");
assert(/@media \(max-width:48rem\)/.test(css), "mobile layout stacks at a bounded breakpoint");
assert(!/\.innerHTML\s*=/.test(src), "open-source labels are rendered without innerHTML injection");
assert(/pointercancel/.test(src) && /lostpointercapture/.test(src), "drag cancellation paths are handled");
assert(/ArrowLeft/.test(src) && /ArrowDown/.test(src), "keyboard token movement is implemented");
assert(/credentials:\s*"omit"/.test(src) && !/Authorization/.test(src), "all tabletop reads are anonymous and carry no auth header");
console.log("TABLETOP_OK");
