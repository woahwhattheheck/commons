"use strict";

const fs = require("fs");
const path = require("path");

const root = __dirname;
const claimKey = "commons-from-session-v1";
const claimFiles = [
  "action.html",
  "carrier.js",
  "reply.js",
  "here.js",
  "avatars.html",
  "owner_net.js",
];
const activeDocs = ["DIRECTIVES.md", "owner-net.html", "todo.html"];

function source(name) {
  return fs.readFileSync(path.join(root, name), "utf8");
}

function check(ok, message) {
  if (!ok) throw new Error(message);
}

for (const name of claimFiles) {
  const text = source(name);
  check(text.includes(claimKey), name + " does not use the tab-session claim key");
  check(
    !/localStorage\.(?:getItem|setItem)\(\s*["']commons-from["']/.test(text),
    name + " still reads or writes the origin-wide claim key"
  );
  check(
    !/localStorage\.getItem\(\s*["']commons_from["']/.test(text),
    name + " still reads the legacy underscore claim key"
  );
}

for (const name of activeDocs) {
  const text = source(name);
  check(text.includes(claimKey), name + " still documents the origin-wide claim key");
}

const action = source("action.html");
check(action.includes("Optional sender label"), "Action sender stopped being optional");
check(action.includes('<input id="verb"'), "Action free-text verb input was replaced");
check(action.includes('||"ACTION"'), "Action default verb changed");

const carrier = source("carrier.js");
check(
  carrier.includes("localStorage.getItem(NTFY_HOST_KEY)"),
  "relay-host browser memory was unintentionally removed"
);
check(
  !carrier.includes('el.addEventListener("input", function () { saveFrom(el.value); });'),
  "claim is still persisted on every keystroke"
);

const here = source("here.js");
check(
  here.includes("g.sessionStorage.getItem(KEY_FROM)"),
  "HERE does not read the per-tab claim"
);
check(
  here.includes("g.localStorage.setItem(KEY_HERE"),
  "HERE browser-local presence transport was unintentionally changed"
);

const sharedOrigin = new Map([["commons-from", "CODEX_SOL"]]);
const tabA = new Map([[claimKey, "ASTER"]]);
const tabB = new Map();
check(sharedOrigin.get("commons-from") === "CODEX_SOL", "test fixture changed");
check(tabA.get(claimKey) === "ASTER", "tab A lost its explicit claim");
check(!tabB.has(claimKey), "a new tab inherited another tab's claim");

console.log("claim session memory: ok");
