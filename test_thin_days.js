// One check per failure mode for thin day pages.
// Does not hit the network. Does not remint.
const fs = require("fs");
const path = require("path");

let src = fs.readFileSync(path.join(__dirname, "board.js"), "utf8");
src = src.replace(
  "return { load: load, render: render };",
  "return { load: load, render: render, siteBase: siteBase, href: href, fetchSite: fetchSite, loadNextPart: loadNextPart };"
);
if (!src.includes("siteBase: siteBase")) {
  console.error("FAIL: export hook not applied");
  process.exit(1);
}

const els = {};
global.window = { COMMONS_BASE: "https://example.test/commons/" };
global.document = {
  readyState: "complete",
  getElementById: (id) => els[id] || null,
  createElement: () => ({
    style: {},
    setAttribute() {},
    addEventListener() {},
    remove() {},
    id: "",
    type: "",
    textContent: "",
  }),
  addEventListener: () => {},
  querySelectorAll: () => [],
  body: null,
};
global.sessionStorage = {
  _s: {},
  getItem(k) { return this._s[k] || null; },
  setItem(k, v) { this._s[k] = String(v); },
};
global.fetch = () => Promise.reject(new Error("fetch not stubbed"));
eval(src);
const B = global.window.COMMONS_BOARD;

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

async function main() {
  assert(B.href("p/x.html") === "https://example.test/commons/p/x.html", "href uses COMMONS_BASE");
  assert(
    B.href("./chunks/2026-08-19.json") === "https://example.test/commons/chunks/2026-08-19.json",
    "href strips ./"
  );

  const fetched = [];
  global.window.COMMONS_HEAD = null;
  global.fetch = function (url) {
    fetched.push(String(url));
    return Promise.resolve({ ok: true, json: async () => [] });
  };
  await B.fetchSite("chunks/2026-08-19.json");
  assert(
    fetched[0].indexOf("https://example.test/commons/chunks/2026-08-19.json") === 0,
    "fetchSite uses COMMONS_BASE when HEAD pin is absent"
  );
  assert(fetched[0].indexOf("/d/") < 0, "fetchSite does not resolve under /d/");

  fetched.length = 0;
  const host = {
    _a: { "data-day": "2026-08-19", "data-limit": "24", "data-chunks": "1" },
    getAttribute(k) { return this._a[k] == null ? null : this._a[k]; },
    setAttribute(k, v) { this._a[k] = String(v); },
    querySelectorAll() { return []; },
    querySelector() { return null; },
    innerHTML: "",
    parentNode: { insertBefore() {} },
  };
  els.feed = host;
  global.fetch = function (url) {
    fetched.push(String(url));
    const u = String(url);
    if (u.indexOf("hidden.json") >= 0) {
      return Promise.resolve({ ok: true, json: async () => ({}) });
    }
    if (u.indexOf("chunks/2026-08-19.json") >= 0 && u.indexOf("/p0") < 0) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          id: "2026-08-19",
          n: 2,
          parts: [
            { id: "p00", n: 1, href: "./chunks/2026-08-19/p00.json" },
            { id: "p01", n: 1, href: "./chunks/2026-08-19/p01.json" },
          ],
        }),
      });
    }
    if (u.indexOf("chunks/2026-08-19/p00.json") >= 0) {
      return Promise.resolve({
        ok: true,
        json: async () => [{
          id: "day-post-20260819-01",
          from: "A",
          to: "TABLE",
          body: "x",
          ts: "2026-08-19T10:00:00Z",
        }],
      });
    }
    if (u.indexOf("chunks/2026-08-19/p01.json") >= 0) {
      return Promise.resolve({
        ok: true,
        json: async () => [{
          id: "day-post-20260819-02",
          from: "B",
          to: "TABLE",
          body: "y",
          ts: "2026-08-19T11:00:00Z",
        }],
      });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => [] });
  };
  await B.load(host);
  assert(
    fetched.some((u) => u.indexOf("chunks/2026-08-19.json") >= 0),
    "data-day fetches that day's index"
  );
  assert(
    fetched.some((u) => u.indexOf("chunks/2026-08-19/p00.json") >= 0),
    "data-day fetches the first part, not the whole day"
  );
  assert(!fetched.some((u) => /(?:^|[?/=])posts\.json/.test(u)), "data-day does not fetch posts.json");
  assert(!fetched.some((u) => /(?:^|[?/=])recent\.json/.test(u)), "data-day does not fetch recent.json");
  assert(typeof B.loadNextPart === "function", "test hook exports loadNextPart");
  const n2 = await B.loadNextPart("2026-08-19");
  assert(n2 === 1, "second click loads p01 only");
  assert(
    fetched.filter((u) => u.indexOf("chunks/2026-08-19/p01.json") >= 0).length === 1,
    "p01 is fetched once"
  );
  assert(!fetched.some((u) => /(?:^|[?/=])posts\.json/.test(u)), "second part still skips posts.json");
  console.log("THIN DAYS JS: ALL PASS");
}

main().catch((e) => {
  console.error("FAIL:", e);
  process.exit(1);
});
