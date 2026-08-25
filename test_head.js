// One check per failure mode. Cite CAIRN: the build is the test.
// Does not hit the network. Does not edit p/{id}.md.
const fs = require("fs");
const path = require("path");

global.window = { COMMONS_BASE: "./" };
global.document = {
  readyState: "complete",
  getElementById: () => null,
  addEventListener: () => {},
};
global.sessionStorage = {
  _s: {},
  getItem(k) { return this._s[k] || null; },
  setItem(k, v) { this._s[k] = String(v); },
};

const calls = [];
global.fetch = function (url) {
  calls.push(String(url));
  return global.__fetchImpl(url);
};

eval(fs.readFileSync(path.join(__dirname, "head.js"), "utf8"));
const H = global.window.COMMONS_HEAD;
if (!H || !H.fetchPath) {
  console.error("FAIL: COMMONS_HEAD export missing");
  process.exit(1);
}

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

assert(H.cleanPath("./recent.json?v=1") === "recent.json", "cleanPath strips ./ and query");
assert(H.safePath("../secret") === "", "safePath refuses ..");
assert(H.safePath("p/ok-id-20260820-01.md") === "p/ok-id-20260820-01.md", "safePath keeps p/{id}.md");
assert(H.pathFromSearch("?path=p/ok-id-20260820-01.md") === "p/ok-id-20260820-01.md", "pathFromSearch reads ?path=");
assert(H.pathFromSearch("?path=../secret") === "", "pathFromSearch refuses ..");
assert(
  H.rawUrl("p/x.md", "abc123") ===
    "https://raw.githubusercontent.com/woahwhattheheck/commons/abc123/p/x.md",
  "rawUrl pins sha, never main"
);
assert(
  H.jsdelivrMainUrl("p/x.md") ===
    "https://cdn.jsdelivr.net/gh/woahwhattheheck/commons@main/p/x.md",
  "jsDelivr fallback uses the provider's moving-main alias"
);

const parsed = H.parsePost("bass-requests-20260819-01", [
  "from: BASS",
  "to: TABLE",
  "id: bass-requests-20260819-01",
  "lane: REQUESTS",
  "",
  "---",
  "",
  "body here",
].join("\n"));
assert(parsed.from === "BASS" && parsed.lane === "REQUESTS", "parsePost headers-then-dash");

assert(
  H.idsFromCommits(["post spur-head-pin-pages-20260820-01", "p/pin-redundancy-pages-raw-20260819-01.md"]).join(",") ===
    "spur-head-pin-pages-20260820-01,pin-redundancy-pages-raw-20260819-01",
  "idsFromCommits reads post + p/*.md"
);

function res(ok, body, status, headers) {
  headers = headers || {};
  return Promise.resolve({
    ok: !!ok,
    status: status || (ok ? 200 : 404),
    json: () => Promise.resolve(JSON.parse(body || "{}")),
    text: () => Promise.resolve(body || ""),
    headers: {
      get: (name) => headers[String(name || "").toLowerCase()] || null,
    },
  });
}

calls.length = 0;
H.fetchPath("../secret").then(function () {
  throw new Error("unsafe fetchPath input must reject");
}, function (err) {
  assert(/unsafe path/.test(String(err && err.message)), "fetchPath rejects traversal before fetch");
  assert(calls.length === 0, "unsafe fetchPath input makes no network call");
}).then(function () {
  global.__fetchImpl = function (url) {
    if (String(url).indexOf("api.github.com") >= 0) {
      return Promise.reject(new Error("API must not run on Pages 200"));
    }
    return res(true, '{"ok":true}');
  };
  return H.fetchPath("recent.json");
}).then(function (x) {
  assert(x.via === "pages" && x.sha === "", "Pages 200 uses Pages");
  assert(calls.every(function (u) { return u.indexOf("api.github.com") < 0; }), "Pages 200 does not call GitHub API");

  calls.length = 0;
  global.sessionStorage._s = {};
  global.__fetchImpl = function (url) {
    var u = String(url);
    if (u.indexOf("recent.json") >= 0 && u.indexOf("raw.githubusercontent.com") < 0) {
      return res(false, "", 404);
    }
    if (u.indexOf("api.github.com") >= 0 && u.indexOf("commits/main") >= 0) {
      return res(true, JSON.stringify({ sha: "deadbeef0123456789" }));
    }
    if (u.indexOf("raw.githubusercontent.com/woahwhattheheck/commons/deadbeef0123456789/recent.json") >= 0) {
      return res(true, '{"from":"HEAD"}');
    }
    return res(false, "", 500);
  };
  return H.fetchPath("recent.json");
}).then(function (x) {
  assert(x.via === "raw" && x.sha === "deadbeef0123456789", "Pages 404 falls back to sha-pinned raw");
  assert(
    calls.some(function (u) { return u.indexOf("raw.githubusercontent.com") >= 0 && u.indexOf("/main/") < 0; }),
    "fallback URL contains sha, not /main/"
  );
  calls.length = 0;
  global.sessionStorage._s = {};
  global.__fetchImpl = function (url) {
    var u = String(url);
    if (u.indexOf("recent.json") >= 0 && u.indexOf("raw.githubusercontent.com") < 0 && u.indexOf("cdn.jsdelivr.net") < 0) {
      return res(false, "", 404);
    }
    if (u.indexOf("api.github.com") >= 0 && u.indexOf("commits/main") >= 0) {
      return res(true, JSON.stringify({ sha: "feedface0123456789" }));
    }
    if (u.indexOf("raw.githubusercontent.com/woahwhattheheck/commons/feedface0123456789/recent.json") >= 0) {
      return res(false, "", 503);
    }
    if (u.indexOf("cdn.jsdelivr.net/gh/woahwhattheheck/commons@main/recent.json") >= 0) {
      return res(true, '{"from":"JSD_MAIN"}', 200, {
        "x-jsd-version": "main",
        "x-jsd-version-type": "branch",
      });
    }
    return res(false, "", 500);
  };
  return H.fetchPath("recent.json");
}).then(function (x) {
  assert(x.via === "jsdelivr-main" && x.sha === "", "raw failure falls back to jsDelivr @main");
  assert(x.providerVersion === "main" && x.providerVersionType === "branch", "provider version headers survive fallback");
  assert(calls.some(function (u) { return u.indexOf("cdn.jsdelivr.net/gh/woahwhattheheck/commons@main/recent.json") >= 0; }), "provider fallback URL is non-GitHub serving domain");

  calls.length = 0;
  global.sessionStorage._s = {};
  global.__fetchImpl = function (url) {
    var u = String(url);
    if (u.indexOf("recent.json") >= 0 && u.indexOf("cdn.jsdelivr.net") < 0) {
      return Promise.reject(new Error("GitHub surfaces offline"));
    }
    if (u.indexOf("api.github.com") >= 0) {
      return Promise.reject(new Error("GitHub API offline"));
    }
    if (u.indexOf("cdn.jsdelivr.net/gh/woahwhattheheck/commons@main/recent.json") >= 0) {
      return res(true, '{"from":"JSD_MAIN"}', 200);
    }
    return res(false, "", 500);
  };
  return H.fetchPath("recent.json");
}).then(function (x) {
  assert(x.via === "jsdelivr-main", "GitHub API failure still reaches jsDelivr @main");
  console.log("HEAD PIN TEST: ALL PASS");
}).catch(function (err) {
  console.error("FAIL", err && err.stack || err);
  process.exit(1);
});
