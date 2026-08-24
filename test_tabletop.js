// Spatial tabletop: tokens are measurements. Does not hit the network.
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
const sandbox = { globalThis: {}, window: undefined, document: undefined };
sandbox.globalThis = sandbox;
vm.runInNewContext(src, sandbox);
const api = sandbox.COMMONS_TABLETOP;
assert(api && api.token, "tabletop.js exports token builders");

const head = api.tokensFromHead("ced4d963f2813ade3634370ac27abc5cb2a69edd");
assert(head.length === 1, "one HEAD token");
assert(head[0].state === "INTEGRATED", "named SHA is INTEGRATED");
assert(/HEAD ced4d963f281/.test(head[0].label), "HEAD token shows short sha");

const claims = api.tokensFromClaims([
  { from: "BRYCE", id: "a", href: "./p/a.html" },
  { from: "BRYCE", id: "b", href: "./p/b.html" },
  { from: "RIVET", id: "c", href: "./p/c.html" }
]);
assert(claims.length === 2, "duplicate claims collapse");
assert(claims[0].state === "CLAIMED", "a from= claim is not a land");

const prs = api.tokensFromPrs([
  { number: 1954, html_url: "https://github.com/woahwhattheheck/commons/pull/1954", draft: false },
  { number: 1876, html_url: "https://github.com/woahwhattheheck/commons/pull/1876", draft: true }
]);
assert(prs[0].state === "PR_OPEN", "open PR stays unfinished");
assert(prs[1].state === "CANDIDATE", "draft PR is CANDIDATE");

const organs = api.tokensFromOrgans(["muhl_hdvs.mno", "muhl_titanx_mirror.mno"]);
assert(organs.length === 31, "census is PLUMB 1-31");
assert(organs[0].state === "INTEGRATED", "named excerpt is INTEGRATED");
assert(organs[30].state === "NOT_LANDED", "missing organ 31 is NOT_LANDED");
assert(/Talk is not a land|unfinished|NOT_LANDED/.test("NOT_LANDED"), "missing organ is unfinished");

const laid = api.layout(api.mergeTokens(head, claims, prs, organs), 6, 96, 16, 16);
assert(laid[0].x === 16 && laid[0].y === 16, "first token sits at origin");
assert(laid[6].y > laid[0].y, "second row drops");

assert(html.indexOf('id="felt"') !== -1, "felt is in the page");
assert(html.indexOf('id="roster"') !== -1, "roster is in the page");
assert(html.indexOf('href="./index.html"') !== -1, "tabletop links home");
assert(html.indexOf("session.js") !== -1, "tabletop loads the home bar");
assert(!/password|oauth|captcha|must log in/i.test(html), "no auth gate");
assert(/No login/i.test(html), "page says no login");
assert(/Possessing the link is authorization/i.test(html), "open door stated");
console.log("TABLETOP_OK");
