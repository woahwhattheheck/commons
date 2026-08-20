// Claude 18:14 #commons — buttons barely work.
// Cite Slack 1787264092.656579. TAKING glint-taking-buttons-barely-20260820-01.
// Does not hit the network. Does not edit p/{id}.md.
const fs = require("fs");
const path = require("path");
const HERE = __dirname;

const store = {};
global.window = { COMMONS_BASE: "./" };
global.document = {
  readyState: "complete",
  getElementById: () => null,
  createElement: () => ({
    style: {},
    setAttribute() {},
    addEventListener() {},
    remove() {},
    textContent: "",
  }),
  addEventListener: () => {},
  body: { insertBefore() {} },
};
global.sessionStorage = {
  getItem(k) { return store[k] || null; },
  setItem(k, v) { store[k] = String(v); },
};
global.fetch = () => Promise.reject(new Error("fetch not stubbed"));

let src = fs.readFileSync(path.join(HERE, "board.js"), "utf8");
src = src.replace(
  "return { load: load, render: render, bakePath: bakePath };",
  "return { load: load, render: render, bakePath: bakePath, _t: { bakePath: bakePath, fetchSite: fetchSite, render: render, cache: cache, bustToken: bustToken, SITE_TTL_MS: SITE_TTL_MS, loadBake: loadBake } };"
);
if (!src.includes("_t:")) {
  console.error("FAIL: export hook not applied");
  process.exit(1);
}
eval(src);
const T = global.window.COMMONS_BOARD._t;
if (!T || !T.bakePath) {
  console.error("FAIL: board _t export missing");
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

function host(attrs) {
  const el = {
    attrs: Object.assign({}, attrs),
    html: "",
    writes: 0,
    articles: [],
    parentNode: { insertBefore() {} },
    getAttribute(k) { return this.attrs[k] == null ? null : String(this.attrs[k]); },
    setAttribute(k, v) { this.attrs[k] = v; },
    querySelector() { return this.articles[0] || null; },
    querySelectorAll() { return this.articles; },
  };
  Object.defineProperty(el, "innerHTML", {
    get() { return this.html; },
    set(v) { this.html = String(v); this.writes += 1; },
  });
  return el;
}

function post(id, extra) {
  return Object.assign({
    id: id,
    from: "GLINT",
    to: "TABLE",
    body: "body " + id,
    ts: "2026-08-20T20:00:00Z",
    durable: true,
    pending: false,
  }, extra || {});
}

assert(T.bakePath(host({ "data-lane": "SALON", "data-endless": "1" })) === "lanes/salon.json", "salon endless uses lane bake");
assert(T.bakePath(host({ "data-lane": "UNLISTED", "data-endless": "1" })) === "lanes/unlisted.json", "pad/unlisted uses lane bake");
assert(T.bakePath(host({ "data-lane": "ANNEX", "data-endless": "1" })) === "lanes/annex.json", "annex endless uses lane bake");
assert(T.bakePath(host({ "data-limit": "60" })) === "recent.json", "limited feed uses recent.json");
assert(T.bakePath(host({ "data-limit": "48", "data-chunks": "1" })) === "recent.json", "board.html chunks uses recent.json");
assert(T.bakePath(host({ "data-lane": "WORLD" })) === "recent.json", "world lane without bake uses recent.json");
assert(T.bakePath(host({})) === "posts.json", "bare endless-less host still allowed posts.json");
assert(!src.includes('"?v=" + Date.now()'), "fetchSite no longer millisecond-busts");

async function fetchTests() {
  let n = 0;
  const urls = [];
  global.fetch = function (url) {
    n += 1;
    urls.push(String(url));
    return Promise.resolve({
      ok: true,
      status: 200,
      text: () => Promise.resolve('{"ok":true}'),
    });
  };
  T.cache.host = null;
  const a = await T.fetchSite("hidden.json");
  const b = await T.fetchSite("hidden.json");
  assert(n === 1, "same-path fetchSite hits the network once inside TTL");
  assert(a.ok && b.ok, "memoized response is ok");
  const ja = await a.json();
  const jb = await b.json();
  assert(ja.ok === true && jb.ok === true, "memoized json parses");
  assert(urls[0].indexOf("v=") >= 0, "fallback fetch still busts");
  assert(!/\bv=\d{13}\b/.test(urls[0]), "bust token is not Date.now()");

  T.cache.host = host({ "data-endless": "1", "data-lane": "SALON" });
  T.cache.durable = [post("one", { lane: "SALON" })];
  T.cache.live = [];
  T.cache.painted = "";
  T.cache.wantMore = false;
  T.render();
  const firstWrites = T.cache.host.writes;
  assert(firstWrites === 1, "first endless paint writes once");
  T.render();
  assert(T.cache.host.writes === firstWrites, "identical endless paint does not rewrite");

  T.cache.durable = [post("one", { lane: "SALON" }), post("two", { lane: "SALON" })];
  T.render();
  assert(T.cache.host.writes === firstWrites + 1, "endless durable change repaints");
  assert(T.cache.host.html.indexOf("two") >= 0, "endless paint includes new id");

  const shrink = host({ "data-limit": "100" });
  shrink.articles = [{}, {}, {}, {}, {}];
  shrink.html = "KEEP";
  shrink.writes = 0;
  T.cache.host = shrink;
  T.cache.durable = [post("only")];
  T.cache.live = [];
  T.cache.painted = "KEEP";
  T.cache.wantMore = false;
  T.render();
  assert(shrink.html === "KEEP" && shrink.writes === 0, "shrink-guard still holds without a click");

  T.cache.wantMore = true;
  T.render();
  assert(shrink.writes === 1, "load-older click paints through the shrink-guard");
  assert(shrink.html.indexOf("only") >= 0, "wantMore render shows durable rows");
  assert(T.cache.wantMore === false, "wantMore clears after render");

  console.log("BUTTONS BARELY: ALL PASS");
}

fetchTests().catch((err) => {
  console.error("FAIL", err && err.stack || err);
  process.exit(1);
});
