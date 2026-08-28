const fs = require("fs");
const path = require("path");

const src = fs.readFileSync(path.join(__dirname, "avatar.js"), "utf8");
const page = fs.readFileSync(path.join(__dirname, "avatars.html"), "utf8");
global.window = {};
global.localStorage = {
  store: {},
  reads: [],
  getItem(k) {
    this.reads.push(k);
    return Object.prototype.hasOwnProperty.call(this.store, k) ? this.store[k] : null;
  },
  setItem(k, v) { this.store[k] = String(v); },
  removeItem(k) { delete this.store[k]; }
};
eval(src);
const A = global.window.COMMONS_AVATAR;
if (!A) { console.error("FAIL: COMMONS_AVATAR missing"); process.exit(1); }

const a = A.hashClaim("POCKET");
const b = A.hashClaim("pocket");
const c = A.hashClaim("POCKET");
if (a !== b || a !== c) { console.error("FAIL: hash not stable", a, b, c); process.exit(1); }
const other = A.hashClaim("MARGIN");
if (other === a) { console.error("FAIL: different claims hashed equal"); process.exit(1); }

const face = A.defaultFace("POCKET");
if (face.initials !== "PO") { console.error("FAIL: initials", face.initials); process.exit(1); }
if (face.mark !== "circle" || face.chosen) { console.error("FAIL: default mark"); process.exit(1); }

const again = A.defaultFace("POCKET");
if (again.hue !== face.hue) { console.error("FAIL: default hue drifted"); process.exit(1); }

const saved = A.saveFace("POCKET", "square", 40);
if (!saved.ok || saved.face.mark !== "square") { console.error("FAIL: save", saved); process.exit(1); }
if (A.face("POCKET").hue !== 40) { console.error("FAIL: chosen hue"); process.exit(1); }

const bryce = A.saveFace("BRYCE", "pill", 10);
if (!bryce.ok || bryce.face.mark !== "pill" || bryce.face.hue !== 10) {
  console.error("FAIL: BRYCE must use the same open browser-local path", bryce);
  process.exit(1);
}
if (global.localStorage.reads.includes("commons-owner-pin")) {
  console.error("FAIL: avatar save consulted owner pin");
  process.exit(1);
}
const unseated = A.saveFace("", "diamond", 20);
if (!unseated.ok || unseated.face.claim !== "UNSEATED") {
  console.error("FAIL: blank claim did not use the open UNSEATED path", unseated);
  process.exit(1);
}
const arbitrary = A.saveFace("player / lane 7", "square", 30);
if (!arbitrary.ok || arbitrary.face.claim !== "PLAYER / LANE 7") {
  console.error("FAIL: arbitrary caller label was rejected or rewritten", arbitrary);
  process.exit(1);
}
const longLabel = "player-" + "x".repeat(80);
const longSaved = A.saveFace(longLabel, "pill", 40);
if (!longSaved.ok || longSaved.face.claim !== longLabel.toUpperCase()) {
  console.error("FAIL: long caller label was rejected or truncated", longSaved);
  process.exit(1);
}
if (/commons-owner-pin|owner pin|unless this phone\/PC is pinned|maxlength=/i.test(src + "\n" + page)) {
  console.error("FAIL: avatar surface still contains an owner-pin gate");
  process.exit(1);
}
if (!/data-avatar/.test(page)) {
  console.error("FAIL: avatar page does not pin the fresh avatar asset");
  process.exit(1);
}

console.log("PASS test_avatar.js");
