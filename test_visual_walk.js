const fs = require("fs");
const path = require("path");

let src = fs.readFileSync(path.join(__dirname, "visual.js"), "utf8");
global.window = { matchMedia: () => ({ matches: false }) };
global.document = {
  readyState: "complete",
  getElementById: () => null,
  addEventListener: () => {},
  body: { classList: { contains: () => false, toggle: () => {}, add: () => {} } }
};
eval(src);
const V = global.window.COMMONS_VISUAL;
if (!V || !V.topicPoint) { console.error("FAIL: COMMONS_VISUAL.topicPoint missing"); process.exit(1); }

const a = V.topicPoint({ to: "TABLE" });
const b = V.topicPoint({ to: "table" });
const c = V.topicPoint({ to: "COURT" });
if (a.left !== b.left || a.top !== b.top) { console.error("FAIL: topicPoint not stable", a, b); process.exit(1); }
if (a.topic !== "TABLE") { console.error("FAIL: topic key", a.topic); process.exit(1); }
if (a.left === c.left && a.top === c.top) { console.error("FAIL: TABLE and COURT mapped to same point"); process.exit(1); }
if (a.left < 4 || a.left > 90 || a.top < 0.4 || a.top > 16) { console.error("FAIL: TABLE off plaza", a); process.exit(1); }

const home0 = V.seatPosition(0, 16);
const home1 = V.seatPosition(1, 16);
if (home0.left === home1.left && home0.top === home1.top) { console.error("FAIL: ring collapsed"); process.exit(1); }

console.log("PASS test_visual_walk.js");
