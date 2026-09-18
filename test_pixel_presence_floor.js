const fs = require("fs");
const path = require("path");

const root = __dirname;

function fail(msg, extra) {
  console.error("FAIL:", msg, extra || "");
  process.exit(1);
}

global.window = {
  matchMedia: () => ({ matches: false }),
  addEventListener: () => {},
  setInterval: () => 0
};

const pixelSrc = fs.readFileSync(path.join(root, "pixel.js"), "utf8");
if (pixelSrc.trim() === "PLACEHOLDER_WILL_FAIL") {
  fail("pixel.js wiped to PLACEHOLDER_WILL_FAIL — restore PIXEL_HERE");
}
if (pixelSrc.indexOf("function classify") < 0) fail("pixel.js lost classify");
eval(pixelSrc);
const P = global.window.PIXEL_HERE;
if (!P || !P.classify || !P.mapGitAuthor) {
  fail("PIXEL_HERE.classify/mapGitAuthor missing", P && Object.keys(P));
}

function byClaim(rows) {
  const o = {};
  (rows || []).forEach(function (a) { o[a.claim] = a; });
  return o;
}

/* Regression from blink-pixel-presence-floor-20260902-01: hearts / peers / gitBy
   claims missing from presence.json still get a seat. Do not remint that post. */
{
  const now = Date.parse("2026-09-02T03:00:00Z");
  const real = Date.now;
  Date.now = () => now;
  const out = P.classify(
    [],
    [],
    {},
    [],
    {
      DJ: {
        from: "DJ",
        path: "pixels/DJ.json",
        verb: "play heartbeat",
        ts: "2026-09-02T02:57:26Z"
      }
    },
    {
      GOAT: {
        from: "GOAT",
        ts: "2026-09-02T02:59:50Z",
        vis: "visible",
        path: "pixel.html"
      }
    },
    {
      GROKBUILD: {
        path: "pixel.js",
        ts: "2026-09-02T02:56:00Z",
        url: "https://github.com/woahwhattheheck/commons"
      }
    }
  );
  Date.now = real;
  const by = byClaim(out);
  if (!by.DJ) fail("heart DJ missing from presence.json must still get a seat", out);
  if (String(by.DJ.src).indexOf("pixels/") < 0) fail("DJ src is the committed heartbeat", by.DJ);
  if ((by.DJ.facts || []).some(function (f) { return String(f).indexOf("presence.json PRESENT") >= 0; })) {
    fail("derived DJ seat must not invent presence.json PRESENT", by.DJ.facts);
  }
  if (!by.GOAT) fail("peer GOAT missing from presence.json must still get a seat");
  if (by.GOAT.room !== "HERE") fail("live peer sits HERE", by.GOAT);
  if (!by.GROKBUILD) fail("gitBy GROKBUILD missing from presence.json must still get a seat");
  if (by.GROKBUILD.room !== "SALON") fail("git path pixel.js maps to SALON", by.GROKBUILD);
}

/* Presence seats still work. Recent-only still does not invent a pixel.js seat. */
{
  const out = P.classify(
    [{ from: "RIVET", ts: "2026-09-02T01:00:00Z", presence: "PRESENT" }],
    [
      {
        from: "STRANGER",
        to: "OFFER",
        id: "stranger-offer-01",
        ts: "2026-09-02T02:40:00Z",
        body: "hi"
      }
    ],
    {},
    [],
    {},
    {},
    {}
  );
  const by = byClaim(out);
  if (!by.RIVET) fail("presence RIVET missing");
  if ((by.RIVET.facts || []).join(" ").indexOf("presence.json PRESENT") < 0) {
    fail("real presence still records presence.json PRESENT", by.RIVET.facts);
  }
  if (by.STRANGER) fail("recent-only still requires presence or heart/peer/git; unify unions that");
}

/* Identity-only GIT_MAP. No invented remaps. Compose BLINK maps, do not drop them. */
{
  if (P.mapGitAuthor("woahwhattheheck", "woahwhattheheck")) fail("woahwhattheheck must stay unmapped");
  if (P.mapGitAuthor("cursor[bot]", "cursor[bot]")) fail("cursor[bot] must stay unmapped");
  if (P.mapGitAuthor("brycembusiness2", "brycembusiness2")) fail("brycembusiness2 must stay unmapped");
  if (P.mapGitAuthor("commons-llms", "commons-llms")) fail("commons-llms must stay unmapped");
  if (P.mapGitAuthor("GROK BUILD", "") !== "GROKBUILD") fail("GROK BUILD maps to GROKBUILD");
  if (P.mapGitAuthor("BLINK", "") !== "BLINK") fail("BLINK maps");
  if (P.mapGitAuthor("DJ", "") !== "DJ") fail("DJ maps");
  if (P.mapGitAuthor("DIGIT", "") !== "DIGIT") fail("compose must keep BLINK DIGIT map");
  if (P.mapGitAuthor("FABLE", "") !== "FABLE") fail("compose must keep BLINK FABLE map");
  if (P.mapGitAuthor("QUILL", "") !== "QUILL") fail("compose must keep BLINK QUILL map");
  if (P.mapGitAuthor("SOL", "") !== "SOL") fail("compose must keep BLINK SOL map");
  if (P.mapGitAuthor("CAIRN", "") !== "CAIRN") fail("CAIRN identity self-map");
}

/* Door: law note + repaired cache pin. Hands off 8bit / 8walk. */
{
  const html = fs.readFileSync(path.join(root, "pixel.html"), "utf8");
  if (html.indexOf("Hearts / peers / gitBy claims missing from presence.json still get a seat") < 0) {
    fail("pixel.html law note missing");
  }
  if (html.indexOf("pixel.js?v=20260902b") < 0) fail("pixel.html must pin the repaired pixel.js");
  if (html.indexOf("pixel.js?v=20260902a") >= 0) fail("stale 20260902a pin still loaded");
  ["8bit.html", "8walk.html", "8bit.js"].forEach(function (fn) {
    const t = fs.readFileSync(path.join(root, fn), "utf8");
    if (t.indexOf("20260902b") >= 0) fail(fn + " must stay hands-off");
  });
}

console.log("PASS test_pixel_presence_floor.js");
