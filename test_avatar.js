const fs = require("fs");
const path = require("path");

const src = fs.readFileSync(path.join(__dirname, "avatar.js"), "utf8");
global.window = {};
global.localStorage = {
  store: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this.store, k) ? this.store[k] : null; },
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
if (bryce.ok) { console.error("FAIL: BRYCE choose without pin"); process.exit(1); }

console.log("PASS test_avatar.js");
