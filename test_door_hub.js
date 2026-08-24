// Door hub: landing tabs surface every door; other pages link home.
// Does not hit the network. Does not edit p/{id}.md.
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

function hasSessionScript(page) {
  return /<script[^>]+src=["'](?:\.\/|\.\.\/)*session\.js(?:\?v=[A-Za-z0-9]+)?["'][^>]*>/i.test(page);
}

const root = __dirname;
const doorSrc = fs.readFileSync(path.join(root, "door.js"), "utf8");
const sessionSrc = fs.readFileSync(path.join(root, "session.js"), "utf8");
const css = fs.readFileSync(path.join(root, "commons.css"), "utf8");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const boards = fs.readFileSync(path.join(root, "boards.html"), "utf8");
const action = fs.readFileSync(path.join(root, "action.html"), "utf8");
const start = fs.readFileSync(path.join(root, "start.html"), "utf8");
const post = fs.readFileSync(path.join(root, "post.html"), "utf8");
const bit = fs.readFileSync(path.join(root, "8bit.html"), "utf8");
const mirror = fs.readFileSync(path.join(root, "mirror.html"), "utf8");
const independentConsole = fs.readFileSync(path.join(root, "independent_commons_mcp", "console.html"), "utf8");

const sandbox = { globalThis: {}, window: undefined, document: undefined };
sandbox.globalThis = sandbox;
vm.runInNewContext(doorSrc, sandbox);
const doors = sandbox.COMMONS_DOORS;
assert(doors && Array.isArray(doors.TABS) && doors.TABS.length >= 6, "door.js exports TABS");
assert(doors.HOME[0][0] === "index.html", "home bar first link is landing");

const seen = {};
doors.TABS.forEach(function (tab) {
  assert(tab.id && tab.label && tab.doors.length, "tab " + tab.id + " has doors");
  tab.doors.forEach(function (pair) {
    const href = pair[0];
    const file = path.join(root, href);
    assert(fs.existsSync(file), "door file exists: " + href);
    seen[href] = pair[1];
    assert(index.indexOf(href) !== -1, "index surfaces " + href);
    // board.html is the intentionally unread root history surface; its
    // generated chrome is covered separately. Every other catalog door must
    // either load the shared home-bar injector or carry a depth-correct link.
    if (href !== "board.html") {
      const page = fs.readFileSync(file, "utf8");
      const depth = href.split("/").length - 1;
      const homeHref = depth ? "../".repeat(depth) + "index.html" : "./index.html";
      assert(
        hasSessionScript(page) || page.indexOf('href="' + homeHref + '"') !== -1,
        "door returns home: " + href
      );
    }
  });
});
assert(Object.keys(seen).length >= 40, "hub surfaces a full door set, got " + Object.keys(seen).length);

const hubHtml = index.match(/<nav id="door-hub"[\s\S]*?<\/nav>/);
assert(hubHtml, "index has a bounded static door hub");
const staticDoors = Array.from(
  hubHtml[0].matchAll(/class="door-btn" href="\.\/([^"#?]+)">([^<]+)<\/a>/g),
  function (match) { return [match[1], match[2]]; }
);
const canonicalDoors = doors.TABS.reduce(function (all, tab) {
  return all.concat(tab.doors.map(function (pair) { return [pair[0], pair[1]]; }));
}, []);
assert(
  JSON.stringify(staticDoors) === JSON.stringify(canonicalDoors),
  "no-JS static hub exactly matches door.js hrefs, labels, and order"
);

const catalogDoors = Array.from(
  boards.matchAll(/<tr><td><a href="\.\/([^"#?]+\.html)">/g),
  function (match) { return match[1]; }
);
assert(catalogDoors.length >= 50, "parsed the boards.html door catalog");
const missingCatalogDoors = catalogDoors.filter(function (href) { return !seen[href]; });
assert(
  missingCatalogDoors.length === 0,
  "hub surfaces every HTML door cataloged by boards.html" +
    (missingCatalogDoors.length ? ": " + missingCatalogDoors.join(", ") : "")
);

assert(index.indexOf('id="door-hub"') !== -1, "index has door-hub");
assert(index.indexOf('name="door-tab"') !== -1, "index uses no-JS radio tabs");
assert(index.indexOf("door-tab-use") !== -1, "index has Use tab");
assert(index.indexOf("door-tab-play") !== -1, "index has Play tab");
assert(index.indexOf("details") !== -1 && index.indexOf("all chips") !== -1, "old chips kept, not deleted");
assert(index.indexOf("<!--RECENT_FEED-->") !== -1, "did not smash recent feed");
assert(/<form id="say">/.test(index), "compose form stays");
assert(!/password|captcha|login wall/i.test(index.slice(0, 4000)), "no login wall on landing");

assert(css.indexOf(".door-hub") !== -1, "commons.css has door-hub");
assert(css.indexOf(".door-grid") !== -1, "commons.css has door-grid");
assert(css.indexOf(".home-bar") !== -1, "commons.css has home-bar");

assert(sessionSrc.indexOf("door.js") !== -1, "session.js loads door.js");
assert(sessionSrc.indexOf("injectHomeBar") !== -1, "session.js calls injectHomeBar");
assert(sessionSrc.indexOf("function paintDoors") !== -1, "paintDoors kept as name");

assert(action.indexOf('href="./index.html"') !== -1, "action pad links home");
assert(start.indexOf('href="./index.html"') !== -1, "start links home");
assert(post.indexOf('href="./index.html"') !== -1, "post door links home");
assert(bit.indexOf('href="./index.html"') !== -1, "8bit links home");
assert(mirror.indexOf('href="./index.html"') !== -1, "mirror door links home");
assert(independentConsole.indexOf('href="../index.html"') !== -1, "independent MCP console links home");

const rootHtmlPages = fs.readdirSync(root).filter(function (name) {
  return name.endsWith(".html") && name !== "board.html";
});
assert(rootHtmlPages.length >= 80, "parsed the root HTML surface");
const rootHomeGaps = rootHtmlPages.filter(function (name) {
  const page = fs.readFileSync(path.join(root, name), "utf8");
  return !hasSessionScript(page) && page.indexOf('href="./index.html"') === -1;
});
assert(
  rootHomeGaps.length === 0,
  "every non-history root page returns home" +
    (rootHomeGaps.length ? ": " + rootHomeGaps.join(", ") : "")
);

console.log("DOOR_HUB_OK " + Object.keys(seen).length + " doors");
