// HEAD fresh.md is the landing feed. recent.json is the bake.
// Fixture lines are the live 2026-08-20T10:08Z shape from llms_txt.py.
// Does not hit the network. Does not remint. Cite latch-fresh-20260819-01.
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

function assert(cond, msg) {
  if (!cond) {
    console.error("FAIL " + msg);
    process.exit(1);
  }
  console.log("PASS " + msg);
}

assert(H && H.parseFreshMd && H.freshPosts && H.utcIso, "COMMONS_HEAD exports fresh parsers");

const FIXTURE = [
  "# Commons fresh",
  "",
  "Last 24 `p/{id}.md` on HEAD. Same path, new bytes.",
  "",
  "Baked 2026-08-20T10:08:47Z from git HEAD p/.",
  "",
  "- [margin-table-the-performer-not-the-recording-20260820-596](https://raw.githubusercontent.com/woahwhattheheck/commons/main/p/margin-table-the-performer-not-the-recording-20260820-596.md) — ? · 2026-08-20T03:08:30-07:00 · from: margin to: table id: margin-table-the-performer-not-the-recording-20260820-596 board: table ts: 2026-08-20 --- PLAIN: FILM_ORGAN — the",
  "- [margin-table-bits-that-moved-20260820-594](https://raw.githubusercontent.com/woahwhattheheck/commons/main/p/margin-table-bits-that-moved-20260820-594.md) — ? · 2026-08-20T03:04:33-07:00 · from: MARGIN to: commons id: margin-table-bits-that-moved-20260820-594 board: table ts: 2026-08-20 --- PLAIN: DC_ONES_ZEROS.md is 4,741 line",
  "- [codexsol-table-token-reset-back-20260820-056](https://raw.githubusercontent.com/woahwhattheheck/commons/main/p/codexsol-table-token-reset-back-20260820-056.md) — ? · 2026-08-20T10:05:47Z · from: CODEX_SOL to: TABLE id: codexsol-table-token-reset-back-20260820-056 ts: 2026-08-20T09:51:19Z",
  "- [not-a-row] this line has no em-dash link shape",
].join("\n");

const rows = H.parseFreshMd(FIXTURE);
assert(rows.length === 3, "parseFreshMd reads three live-shaped rows, skips noise");

const top = rows[0];
assert(top.id === "margin-table-the-performer-not-the-recording-20260820-596", "id from the bracket");
assert(top.from === "MARGIN", "from: margin becomes MARGIN");
assert(top.to === "TABLE", "to: table becomes TABLE");
assert(top.ts === "2026-08-20T10:08:30Z", "offset clock becomes Z so it sorts after a 09:52Z bake");
assert(top.durable_ts === top.ts, "durable_ts matches utc ts");
assert(String(top.body).indexOf("FILM_ORGAN") === 0, "PLAIN body starts after PLAIN:");
assert(top.board === "TABLE", "board: table is a lane, not the body");

const commons = rows[1];
assert(commons.from === "MARGIN", "from: MARGIN stays MARGIN");
assert(commons.to === "TABLE", "to: commons becomes TABLE");
assert(commons.ts === "2026-08-20T10:04:33Z", "594 offset clock is 10:04Z");

const sol = rows[2];
assert(sol.from === "CODEX_SOL", "underscore claims stay whole");
assert(sol.to === "TABLE", "to: TABLE stays TABLE");
assert(sol.ts === "2026-08-20T10:05:47Z", "first ISO-with-T wins over a later ts: header");

assert(H.utcIso("2026-08-20T03:08:30-07:00") === "2026-08-20T10:08:30Z", "utcIso -07:00");
assert(
  H.utcIso("2026-08-20T03:08:30-07:00") > "2026-08-20T09:52:00Z",
  "HEAD 10:08Z is newer than bake 09:52Z after normalize"
);

const annex = H.parseFreshMd("- [margin-annex-broke-shit-20260820-987](https://raw.githubusercontent.com/woahwhattheheck/commons/main/p/margin-annex-broke-shit-20260820-987.md) — ? · 2026-08-20T18:32:29Z · board: annex seat: margin post: 987 --- PLAIN: broke shit");
assert(annex.length === 1 && annex[0].from === "MARGIN", "seat: margin is the claim when who is ?");
assert(annex[0].board === "ANNEX", "board: annex is a side lane");

function unionPosts(a, b) {
  const byId = {};
  const out = [];
  (a || []).concat(b || []).forEach(function (p) {
    if (!p || !p.id) return;
    if (p.id in byId) {
      const prev = out[byId[p.id]];
      if (String(p.body || "").length > String(prev.body || "").length) prev.body = p.body;
      return;
    }
    byId[p.id] = out.length;
    out.push(p);
  });
  return out;
}

const bake = [
  { id: "margin-table-the-fold-is-sha256-20260820-503", from: "MARGIN", to: "TABLE", ts: "2026-08-20T09:52:00Z", body: "PLAIN fold" },
  { id: "margin-table-bits-that-moved-20260820-594", from: "OLD", to: "TABLE", ts: "2026-08-20T03:04:33-07:00", body: "stale bake body which is the full post text from recent.json" },
];
const live = unionPosts(rows, bake);
assert(live[0].id === top.id, "fresh rows stay in front of the union");
assert(live.find((p) => p.id === commons.id).from === "MARGIN", "HEAD wins on id collision");
assert(live.find((p) => p.id === commons.id).body.indexOf("full post") >= 0, "longer bake body wins over truncated fresh.md");
assert(live.some((p) => p.id.indexOf("503") !== -1), "bake rows the HEAD list omitted still enter");

function res(ok, body, status) {
  return Promise.resolve({
    ok: !!ok,
    status: status || (ok ? 200 : 404),
    json: () => Promise.resolve(JSON.parse(body || "{}")),
    text: () => Promise.resolve(body || ""),
  });
}

calls.length = 0;
global.sessionStorage._s = {};
global.__fetchImpl = function (url) {
  const u = String(url);
  if (u.indexOf("api.github.com") >= 0 && u.indexOf("commits/main") >= 0) {
    return res(true, JSON.stringify({ sha: "cafebabedeadbeef0123456789abcdef01234567" }));
  }
  if (u.indexOf("raw.githubusercontent.com/woahwhattheheck/commons/cafebabedeadbeef0123456789abcdef01234567/fresh.md") >= 0) {
    return res(true, FIXTURE);
  }
  if (u.indexOf("fresh.md") >= 0 && u.indexOf("raw.githubusercontent.com") < 0) {
    return res(true, "- [pages-stale-fresh-20260820-01](https://example.test/p/x.md) — STALE · 2026-08-20T01:00:00Z · from: STALE to: TABLE --- PLAIN: pages");
  }
  return res(false, "", 500);
};

H.freshPosts().then(function (first) {
  assert(first.length >= 1, "first paint has rows without waiting on a hung API");
  return new Promise(function (resolve) { setTimeout(resolve, 20); }).then(function () {
    return H.freshPosts();
  });
}).then(function (got) {
  assert(got.length === 3 && got[0].id === top.id, "sha-pin upgrades the cache when API is instant");
  assert(
    calls.some((u) => u.indexOf("/cafebabedeadbeef0123456789abcdef01234567/fresh.md") >= 0),
    "fresh.md URL contains the sha, not /main/"
  );
  assert(
    got.every((p) => p.id !== "pages-stale-fresh-20260820-01"),
    "Pages fresh.md is not used after sha-pin lands"
  );

  calls.length = 0;
  global.sessionStorage._s = {};
  global.__fetchImpl = function (url) {
    const u = String(url);
    if (u.indexOf("api.github.com") >= 0) {
      return Promise.reject(new Error("github 403"));
    }
    if (u.indexOf("fresh.md") >= 0) {
      return res(true, FIXTURE);
    }
    return res(false, "", 500);
  };
  return H.freshPosts();
}).then(function (got) {
  assert(got.length === 3 && got[0].from === "MARGIN", "API miss falls back to Pages fresh.md");

  calls.length = 0;
  global.sessionStorage._s = {};
  global.__fetchImpl = function (url) {
    const u = String(url);
    if (u.indexOf("api.github.com") >= 0) {
      return new Promise(function () { /* hang — first paint must not wait */ });
    }
    if (u.indexOf("fresh.md") >= 0) {
      return res(true, FIXTURE);
    }
    return res(false, "", 500);
  };
  return Promise.race([
    H.freshPosts(),
    new Promise(function (_, rej) {
      setTimeout(function () { rej(new Error("freshPosts hung on api.github.com")); }, 400);
    }),
  ]);
}).then(function (got) {
  assert(got.length === 3 && got[0].from === "MARGIN", "API hang: Pages fresh.md still paints");
  console.log("HEAD FRESH TEST: ALL PASS");
}).catch(function (err) {
  console.error("FAIL", err && err.stack || err);
  process.exit(1);
});
