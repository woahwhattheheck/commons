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

const exactMainSrc = fs.readFileSync(path.join(__dirname, "exact-main.js"), "utf8");
const src = fs.readFileSync(path.join(__dirname, "tabletop.js"), "utf8");
const html = fs.readFileSync(path.join(__dirname, "tabletop.html"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "tabletop.css"), "utf8");
const sandbox = { globalThis: {}, window: undefined, document: undefined };
sandbox.globalThis = sandbox;
vm.runInNewContext(exactMainSrc, sandbox);
vm.runInNewContext(src, sandbox);
const api = sandbox.COMMONS_TABLETOP;
assert(api && api.token, "tabletop exports typed token builders");
assert(sandbox.COMMONS_EXACT_MAIN && sandbox.COMMONS_EXACT_MAIN.resolveBrowser, "tabletop test loads the shared exact-main resolver first");

function pkt(payload) {
  return (payload.length + 4).toString(16).padStart(4, "0") + payload;
}

const advertisedHead = "1111111111111111111111111111111111111111";
const advertisedMain = "2222222222222222222222222222222222222222";
const advertisement = pkt("# service=git-upload-pack\n") + "0000" +
  pkt(advertisedMain + " HEAD\0multi_ack symref=HEAD:refs/heads/main agent=git/test\n") +
  pkt(advertisedMain + " refs/heads/main\n") + "0000";
assert(api.parseGitAdvertisement(advertisement) === advertisedMain, "explicit main and symbolic HEAD resolve one advertised commit");
const headOnlyAdvertisement = pkt("# service=git-upload-pack\n") + "0000" +
  pkt(advertisedHead + " HEAD\0symref=HEAD:refs/heads/main agent=git/test\n") + "0000";
assert(api.parseGitAdvertisement(headOnlyAdvertisement) === advertisedHead, "symbolic HEAD resolves main when an explicit main row is absent");
assert(api.parseGitAdvertisement(pkt("# service=git-upload-pack\n") + "0000") === "", "advertisement without main remains unresolved");

function parserRejects(value) {
  try { api.parseGitAdvertisement(value); } catch (_) { return true; }
  return false;
}

assert(parserRejects("000"), "truncated git pkt-line header is rejected");
assert(parserRejects("0008bad"), "truncated git pkt-line payload is rejected");
assert(parserRejects("0003"), "reserved git pkt-line length is rejected");
assert(api.parseGitAdvertisement(pkt(advertisedMain + " refs/heads/main-evil\n") + "0000") === "", "main-like ref names do not resolve main");
assert(parserRejects(pkt("not-a-sha refs/heads/main\n") + "0000"), "malformed main SHA is rejected");
const conflictingMain = pkt(advertisedHead + " refs/heads/main\n") +
  pkt(advertisedMain + " refs/heads/main\n") + "0000";
assert(parserRejects(conflictingMain), "conflicting duplicate main refs are rejected");
const byteCountedAdvertisement = pkt(advertisedHead + " refs/heads/f\xc3\xa9ature\n") +
  pkt(advertisedMain + " refs/heads/main\n") + "0000";
assert(api.parseGitAdvertisement(byteCountedAdvertisement) === advertisedMain, "pkt-line offsets remain byte-counted before a non-ASCII ref");

const head = api.tokensFromHead("83c024423c6fda8a5891d2bae2f0e0f52b510421");
assert(head.length === 1 && head[0].state === "INTEGRATED", "named main SHA is one integrated HEAD token");
assert(head[0].href.includes("/commit/83c024423c6f"), "HEAD token links the exact commit");
const frozenHead = api.tokensFromHead("83c024423c6fda8a5891d2bae2f0e0f52b510421", "FROZEN")[0];
assert(frozenHead.state === "FROZEN" && frozenHead.label.startsWith("SNAPSHOT "), "frozen commit is labelled SNAPSHOT/FROZEN, never HEAD/INTEGRATED");

const noSnapshot = api.snapshotFromSearch("?path=x");
assert(!noSnapshot.present && !noSnapshot.valid && noSnapshot.sha === "", "absent sha query selects live mode");
const frozenSnapshot = api.snapshotFromSearch("?sha=83C024423C6FDA8A5891D2BAE2F0E0F52B510421");
assert(frozenSnapshot.present && frozenSnapshot.valid && frozenSnapshot.sha === "83c024423c6fda8a5891d2bae2f0e0f52b510421", "valid frozen SHA normalizes uppercase without changing the commit");
const invalidSnapshot = api.snapshotFromSearch("?sha=main");
assert(invalidSnapshot.present && !invalidSnapshot.valid && invalidSnapshot.sha === "", "invalid explicit sha stays distinct from an absent live query");
assert(!api.snapshotFromSearch("?sha=bad&sha=83c024423c6fda8a5891d2bae2f0e0f52b510421").valid, "first duplicate sha parameter wins and invalid input fails closed");
assert(!api.snapshotFromSearch("?sha=%2083c024423c6fda8a5891d2bae2f0e0f52b510421").valid && !api.snapshotFromSearch("?sha=83c024423c6fda8a5891d2bae2f0e0f52b510421%20").valid, "frozen SHA whitespace fails closed instead of selecting a different address");
assert(api.snapshotFromSearch("?%73ha=83c024423c6fda8a5891d2bae2f0e0f52b510421").valid, "encoded sha key still selects the exact frozen commit");
assert(api.compareURL(frozenSnapshot.sha, advertisedMain).includes(frozenSnapshot.sha + "..." + advertisedMain), "strict two-SHA compare URL preserves both exact commits");
assert(api.compareURL("main", advertisedMain) === "", "compare URL rejects branch names and malformed SHAs");

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
assert(html.includes('id="tabletop-time"'), "freeze/return-live control exists");
assert(html.includes('id="tabletop-mode"'), "live versus frozen mode is written as text");
assert(html.includes('id="tabletop-compare"'), "frozen-to-current evidence link exists outside the control cluster");
assert(html.includes('id="tabletop-reset"'), "persisted token layout has a reset control");
assert(/No login or token/i.test(html), "open door is explicit");
assert(/min-height:44px/.test(css) && /width:44px/.test(css), "mobile controls and drag handles meet 44px target");
assert(/@media \(max-width:48rem\)/.test(css), "mobile layout stacks at a bounded breakpoint");
assert(!/\.innerHTML\s*=/.test(src), "open-source labels are rendered without innerHTML injection");
assert(/pointercancel/.test(src) && /lostpointercapture/.test(src), "drag cancellation paths are handled");
assert(/ArrowLeft/.test(src) && /ArrowDown/.test(src), "keyboard token movement is implemented");
assert(/credentials:\s*"omit"/.test(src) && !/Authorization/.test(src), "all tabletop reads are anonymous and carry no auth header");
assert(exactMainSrc.indexOf("api.github.com/repos/") < exactMainSrc.indexOf("cors.isomorphic-git.org"), "shared resolver keeps GitHub API primary and anonymous git smart-HTTP as fallback");
assert(exactMainSrc.includes("https://cors.isomorphic-git.org/github.com/"), "shared resolver uses the verified anonymous CORS git path");
assert(!exactMainSrc.includes("cors.isomorphic-git.org/https://"), "shared resolver avoids the rejected embedded-protocol proxy path");
assert(/rawURL\(sha,\s*"presence\.json"\)/.test(src) && /rawURL\(sha,\s*"DIRECTIVES\.md"\)/.test(src), "state reads remain pinned to the resolved exact SHA");
assert(html.indexOf("exact-main.js?v=20260824a") < html.indexOf("tabletop.js?v=20260824d"), "tabletop loads the shared resolver before its fresh controller asset");
assert(/selectedRef\(snapshot, force\)/.test(src) && /snapshot\.valid/.test(src), "frozen source reads select the URL SHA before any live resolver");
assert(/current main for drift/.test(src) && /result\("current main", resolveMain/.test(src), "optional frozen drift lookup is isolated as a noncritical result");
assert(/addEventListener\("popstate"/.test(src), "browser back and forward remeasure the addressed state");

async function testResolvers() {
  let selectedMainReads = 0;
  const frozenSelection = await api.selectRef(frozenSnapshot, () => {
    selectedMainReads += 1;
    return Promise.resolve({ sha: advertisedMain, via: "should not run" });
  });
  assert(frozenSelection.frozen && frozenSelection.sha === frozenSnapshot.sha && selectedMainReads === 0, "valid frozen view bypasses both live-main resolver roads for its source SHA");
  let invalidSelectionRejected = false;
  try {
    await api.selectRef(invalidSnapshot, () => {
      selectedMainReads += 1;
      return Promise.resolve({ sha: advertisedMain, via: "should not run" });
    });
  } catch (error) {
    invalidSelectionRejected = /invalid frozen SHA/.test(String(error && error.message));
  }
  assert(invalidSelectionRejected && selectedMainReads === 0, "invalid explicit frozen SHA performs zero live resolver reads and fails to UNKNOWN");
  const liveSelection = await api.selectRef(noSnapshot, () => {
    selectedMainReads += 1;
    return Promise.resolve({ sha: advertisedMain, via: "test live", observedAt: "2026-08-25T00:00:00Z" });
  }, true);
  assert(!liveSelection.frozen && liveSelection.sha === advertisedMain && selectedMainReads === 1, "absent sha selects live main exactly once");

  let gitCalls = 0;
  const apiResult = await api.resolveMain(
    () => Promise.resolve({ sha: advertisedHead }),
    () => { gitCalls += 1; return Promise.resolve(advertisement); }
  );
  assert(apiResult.sha === advertisedHead && apiResult.via === "GitHub commits API", "valid API response resolves main through the primary road");
  assert(gitCalls === 0, "valid API response does not call the git fallback");

  const fallbackResult = await api.resolveMain(
    () => Promise.reject(new Error("commits/main HTTP 403")),
    () => { gitCalls += 1; return Promise.resolve(advertisement); }
  );
  assert(gitCalls === 1, "API HTTP 403 calls the anonymous git fallback exactly once");
  assert(fallbackResult.sha === advertisedMain && fallbackResult.via === "anonymous git smart-HTTP fallback", "403 fallback returns the advertised exact main SHA and labels its road");

  const malformedApiResult = await api.resolveMain(
    () => Promise.resolve({ sha: "not-a-sha" }),
    () => Promise.resolve(headOnlyAdvertisement)
  );
  assert(malformedApiResult.sha === advertisedHead, "malformed API payload also fails over to a valid git advertisement");

  let bothFailed = false;
  try {
    await api.resolveMain(
      () => Promise.reject(new Error("commits/main HTTP 403")),
      () => Promise.resolve("0008bad")
    );
  } catch (error) {
    bothFailed = /GitHub API:.*HTTP 403.*git smart-HTTP:.*truncated/.test(String(error && error.message));
  }
  assert(bothFailed, "API and malformed fallback failures reject together so boot remains UNKNOWN");
  console.log("TABLETOP_OK");
}

testResolvers().catch((error) => {
  console.error(error);
  process.exit(1);
});
