const fs = require("fs");
const path = require("path");
function assert(cond, msg) {
  if (!cond) { console.error("FAIL " + msg); process.exit(1); }
  console.log("PASS " + msg);
}
const root = __dirname;
const discord = fs.readFileSync(path.join(root, "discord", "plugin.html"), "utf8");
const slack = fs.readFileSync(path.join(root, "slack", "plugin.html"), "utf8");
const door = fs.readFileSync(path.join(root, "door.js"), "utf8");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const start = fs.readFileSync(path.join(root, "start.html"), "utf8");
assert(door.indexOf('["discord/plugin.html", "Discord door"]') !== -1, "door.js catalogs Discord door");
assert(door.indexOf('["slack/plugin.html", "Slack door"]') !== -1, "door.js catalogs Slack door");
assert(index.indexOf("./discord/plugin.html") !== -1, "landing surfaces Discord door");
assert(index.indexOf("./slack/plugin.html") !== -1, "landing surfaces Slack door");
assert(start.indexOf("./discord/plugin.html") !== -1, "start surfaces Discord door");
assert(start.indexOf("./slack/plugin.html") !== -1, "start surfaces Slack door");
assert(discord.indexOf('href="../index.html"') !== -1, "Discord door links home");
assert(slack.indexOf('href="../index.html"') !== -1, "Slack door links home");
assert(discord.indexOf("discord.com/api/webhooks/") !== -1, "Discord door requires a Discord webhook host");
assert(slack.indexOf("hooks.slack.com/services/") !== -1, "Slack door requires a Slack webhook host");
assert(discord.indexOf("user token") !== -1, "Discord door refuses a user token");
assert(slack.indexOf("user token") !== -1, "Slack door refuses a user token");
assert(/xox\[pbaec\]-/i.test(slack), "Slack door rejects token-shaped paste");
assert(discord.indexOf("link-only send is legal") !== -1, "Discord door allows link-only send");
assert(slack.indexOf("link-only send is legal") !== -1, "Slack door allows link-only send");
assert(discord.indexOf("slack/plugin.html") !== -1, "Discord door points at Slack door");
assert(slack.indexOf("discord/plugin.html") !== -1, "Slack door points at Discord door");
assert(!/xox[pbaec]-[A-Za-z0-9]{8,}/.test(discord + slack), "plugins do not ship a live Slack token");
assert(discord.indexOf("hooks.slack.com") === -1, "Discord door does not accept a Slack webhook");
assert(slack.indexOf("discord.com/api/webhooks/") === -1, "Slack door does not accept a Discord webhook");
console.log("REACH_PLUGINS_OK");
