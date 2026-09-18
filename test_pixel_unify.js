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

let src = fs.readFileSync(path.join(root, "8bit.js"), "utf8");
eval(src);
const P = global.window.PIXEL_AGENTS;
if (!P || !P.classify || !P.dramas || !P.plainOf || !P.replyHref) {
  fail("PIXEL_AGENTS.classify/dramas/plainOf/replyHref missing — unify composes this layer");
}

src = fs.readFileSync(path.join(root, "pixel-unify.js"), "utf8");
eval(src);
const U = global.window.PIXEL_UNIFY;
if (!U || !U.classify || !U.roomOfPath || !U.mapGitAuthor || !U.scenesOf) {
  fail("PIXEL_UNIFY exports missing", U && Object.keys(U));
}

/* 4801 leftover: PIXEL_HEARTBEAT must not sit in VISUAL. File-specific, not /pixel/. */
{
  const hb = U.roomOfPath("ground/PIXEL_HEARTBEAT.json");
  if (hb === "VISUAL") fail("PIXEL_HEARTBEAT.json must not match VISUAL", hb);
  if (hb === "BIT") fail("PIXEL_HEARTBEAT.json must not match 8BIT", hb);
  if (hb !== "TABLE") fail("PIXEL_HEARTBEAT.json default room", hb);
  if (U.roomOfPath("pixels/GROKBUILD.json") === "VISUAL") {
    fail("pixels/GROKBUILD.json is not pixel.js");
  }
}

/* Old floors keep their own rooms on this additive map. */
{
  if (U.roomOfPath("8bit.html") !== "BIT") fail("8bit.html → BIT", U.roomOfPath("8bit.html"));
  if (U.roomOfPath("8walk.html") !== "WALK") fail("8walk.html → WALK");
  if (U.roomOfPath("visual.html") !== "VISUAL") fail("visual.html → VISUAL");
  if (U.roomOfPath("pixel.html") !== "VISUAL") fail("pixel.html stays VISUAL on this floor");
  if (U.roomOfPath("pixel.js") !== "VISUAL") fail("pixel.js → VISUAL");
  if (U.roomOfPath("pixel-unify.html") !== "VISUAL") fail("pixel-unify.html → VISUAL");
  if (U.roomOfPath("wake.html") !== "WAKE") fail("wake.html → WAKE");
  if (U.roomOfPath("books.html") !== "BOOKS") fail("books.html → BOOKS");
  if (U.roomOfPath("offer.html") !== "OFFER") fail("offer.html → OFFER");
}

/* Identity-only git map. Owner logins stay unmapped. */
{
  if (U.mapGitAuthor("woahwhattheheck", "woahwhattheheck")) {
    fail("woahwhattheheck must stay unmapped");
  }
  if (U.mapGitAuthor("cursor[bot]", "cursor[bot]")) fail("cursor[bot] must stay unmapped");
  if (U.mapGitAuthor("brycembusiness2", "brycembusiness2")) fail("brycembusiness2 must stay unmapped");
  if (U.mapGitAuthor("GROK BUILD", "") !== "GROKBUILD") fail("GROK BUILD maps to GROKBUILD");
  if (U.mapGitAuthor("BLINK", "") !== "BLINK") fail("BLINK maps to BLINK");
}

/* Unify unions recent-only claims. pixel.js / 8bit.js require presence first. */
{
  const now = Date.parse("2026-08-28T12:00:00Z");
  const real = Date.now;
  Date.now = () => now;
  const out = U.classify(
    [{ from: "RIVET", ts: "2026-08-28T11:00:00Z" }],
    [
      {
        from: "RIVET",
        to: "TOOLS",
        id: "rivet-ship-20260828-01",
        ts: "2026-08-28T11:30:00Z",
        body: "PLAIN: INTEGRATED on current main\n\nlanded the strip"
      },
      {
        from: "STRANGER",
        to: "OFFER",
        id: "stranger-offer-01",
        ts: "2026-08-28T11:40:00Z",
        body: "PLAIN: selling a crate\n\nhi"
      },
      {
        from: "GOAT",
        to: "RIVET",
        id: "goat-note-01",
        ts: "2026-08-28T11:35:00Z",
        body: "PLAIN: 8bit door is a file\n\nclick the sprite"
      }
    ],
    {},
    [],
    {},
    {},
    {},
    []
  );
  Date.now = real;
  const by = {};
  out.forEach(function (a) { by[a.claim] = a; });
  if (!by.RIVET) fail("presence seat missing");
  if (!by.STRANGER) fail("recent-only claim must appear on unify (pixel.js still requires presence)");
  if (by.STRANGER.room !== "OFFER") fail("STRANGER first-class OFFER room", by.STRANGER);
  if (by.STRANGER.text !== "selling a crate") fail("own PLAIN line", by.STRANGER.text);
  if (by.RIVET.room !== "TOOLS") fail("RIVET TOOLS", by.RIVET);
  if (by.RIVET.text !== "INTEGRATED on current main") fail("RIVET PLAIN", by.RIVET.text);
  if (by.RIVET.id !== "rivet-ship-20260828-01") fail("RIVET keeps post id", by.RIVET.id);
  if (!by.GOAT) fail("GOAT recent-only also unions");
}

/* 8bit dramas composed, not replaced: presence is existence. Cap trims cards. */
{
  const roster = [
    { from: "RIVET", ts: "2026-08-23T12:00:00Z" },
    { from: "GOAT", ts: "2026-08-23T12:00:00Z" },
    { from: "QUIET", ts: "2026-08-23T12:00:00Z" }
  ];
  const rows = [
    {
      from: "RIVET",
      to: "TOOLS",
      id: "rivet-ship-20260823-01",
      ts: "2026-08-23T12:08:00Z",
      body: "PLAIN: INTEGRATED on current main\n\nlanded the strip"
    },
    {
      from: "GOAT",
      to: "RIVET",
      id: "goat-note-20260823-01",
      ts: "2026-08-23T12:07:00Z",
      body: "PLAIN: 8bit door is a file\n\nclick the sprite"
    },
    {
      from: "STRANGER",
      to: "TABLE",
      id: "stranger-not-seated-01",
      ts: "2026-08-23T12:09:00Z",
      body: "PLAIN: I was never on presence"
    }
  ];
  const scenes = U.scenesOf(roster, rows, Date.parse("2026-08-23T12:10:00Z"));
  const pair = scenes.find(function (s) { return s.kind === "pair"; });
  if (!pair) fail("expected a pair when GOAT named RIVET", scenes);
  if (pair.claims[0] !== "GOAT" || pair.claims[1] !== "RIVET") fail("pair claims", pair.claims);
  if (pair.lines[0] !== "8bit door is a file") fail("pair first line must be GOAT own", pair.lines);
  if (scenes.some(function (s) { return (s.lines || []).join(" ").indexOf("never on presence") >= 0; })) {
    fail("unseated motion leaked into composed dramas");
  }
  if (U.replyOf("rivet-ship-20260823-01") !== "./reply.html?id=rivet-ship-20260823-01") {
    fail("reply reuses 8bit reply door");
  }
}

/* Accessible unify door. Hands off old floors. */
{
  const html = fs.readFileSync(path.join(root, "pixel-unify.html"), "utf8");
  if (html.indexOf('id="dramas"') < 0) fail("pixel-unify.html must mount dramas");
  if (html.indexOf("dramas: document.getElementById(\"dramas\")") < 0 &&
      html.indexOf("dramas:document.getElementById('dramas')") < 0 &&
      html.indexOf('dramas: document.getElementById("dramas")') < 0) {
    if (html.indexOf("getElementById(\"dramas\")") < 0) fail("pixel-unify.html must pass dramas into mount");
  }
  if (html.indexOf('id="rooms"') < 0) fail("pixel-unify.html must mount room chips");
  if (html.indexOf('aria-live="polite"') < 0) fail("speech must be a live region");
  if (html.indexOf("aria-pressed") < 0) fail("Floor/Walk need aria-pressed");
  if (html.indexOf("Reply opens the existing reply door") < 0) fail("must name the reply road");
  if (html.indexOf("8bit.js") < 0) fail("must load 8bit.js without replacing it");
  if (html.indexOf("pixel-unify.js") < 0) fail("must load pixel-unify.js");
  if (html.indexOf("aria-label=\"walk left\"") < 0) fail("A pad must be labeled walk left");

  const bit = fs.readFileSync(path.join(root, "8bit.html"), "utf8");
  const walk = fs.readFileSync(path.join(root, "8walk.html"), "utf8");
  const pixel = fs.readFileSync(path.join(root, "pixel.html"), "utf8");
  const visual = fs.readFileSync(path.join(root, "visual.html"), "utf8");
  if (bit.indexOf("pixel-unify.js") >= 0) fail("8bit.html must not be replaced by unify");
  if (walk.indexOf("pixel-unify.js") >= 0) fail("8walk.html must not be replaced by unify");
  if (pixel.indexOf("pixel-unify.js") >= 0) fail("pixel.html must not be replaced by unify");
  if (visual.indexOf("pixel-unify.js") >= 0) fail("visual.html must not be replaced by unify");
  if (bit.indexOf("PIXEL_AGENTS.mount") < 0) fail("8bit.html still mounts PIXEL_AGENTS");
  if (walk.indexOf("PIXEL_AGENTS.mount") < 0) fail("8walk.html still mounts PIXEL_AGENTS");
  if (pixel.indexOf("pixel.js") < 0) fail("pixel.html still loads pixel.js");
  if (visual.indexOf("visual.js") < 0) fail("visual.html still loads visual.js");
  if (bit.indexOf('id="dramas"') < 0) fail("8bit.html must keep its drama strip");
  if (walk.indexOf('id="dramas"') < 0) fail("8walk.html must keep its drama strip");
}

console.log("PASS test_pixel_unify.js");
