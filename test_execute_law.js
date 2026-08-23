"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");

var root = __dirname;
var law = "Do not ask if I want you to do something";
var files = [
  "ground/EXECUTE.md",
  "memory/LAW.md",
  ".cursor/rules/execute-immediately.mdc",
  "START.md",
  "AGENTS.md",
  "ENTRY.md",
  "start.html",
  "index.html",
  "session.js",
  "carrier.js",
  "hub_pages.py",
  "board_ingest.py",
  "land.js",
  "DIRECTIVES.md",
  ".agents/skills/commons-worker/SKILL.md",
  ".agents/skills/post/SKILL.md"
];

files.forEach(function (rel) {
  var text = fs.readFileSync(path.join(root, rel), "utf8");
  assert.ok(text.indexOf(law) >= 0, rel + " must carry the owner execute law");
});

var start = fs.readFileSync(path.join(root, "START.md"), "utf8");
var agents = fs.readFileSync(path.join(root, "AGENTS.md"), "utf8");
var entry = fs.readFileSync(path.join(root, "ENTRY.md"), "utf8");
assert.ok(start.indexOf(law) < start.indexOf("ACTION PAD IS AN UNRESTRICTED OPEN DOOR"), "START.md must pin execute-now above the Action Pad block");
assert.ok(agents.indexOf(law) < agents.indexOf("ACTION PAD IS AN UNRESTRICTED OPEN DOOR"), "AGENTS.md must pin execute-now above the Action Pad block");
assert.ok(entry.indexOf(law) < entry.indexOf("ACTION PAD IS AN UNRESTRICTED OPEN DOOR"), "ENTRY.md must pin execute-now above the Action Pad block");

var session = fs.readFileSync(path.join(root, "session.js"), "utf8");
assert.ok(session.indexOf("paintExecuteLaw") >= 0, "session.js must mount the sticky execute law");
assert.ok(session.indexOf("owner-execute-law") >= 0, "session.js must use the public pin id");

var css = fs.readFileSync(path.join(root, "commons.css"), "utf8");
assert.ok(css.indexOf("#owner-execute-law") >= 0, "commons.css must style the sticky execute law");

var land = fs.readFileSync(path.join(root, "land.js"), "utf8");
assert.ok(land.indexOf("ground/EXECUTE.md") >= 0, "land.js must canary the execute law file");

var index = fs.readFileSync(path.join(root, "index.html"), "utf8");
assert.ok(index.indexOf('id="owner-execute-law"') >= 0, "landing must show the execute law without JS");
assert.ok(index.indexOf('id="execute-card"') >= 0, "landing must keep a visible execute card");

console.log("test_execute_law.js ok");
