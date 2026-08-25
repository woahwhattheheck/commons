const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = __dirname;
const src = fs.readFileSync(path.join(root, "visual.js"), "utf8");

function assert(ok, message) {
  if (!ok) throw new Error(message);
}

function classList(initial) {
  const values = new Set(initial || []);
  return {
    add: value => values.add(value),
    remove: value => values.delete(value),
    contains: value => values.has(value),
    toggle(value, force) {
      const on = force === undefined ? !values.has(value) : !!force;
      if (on) values.add(value); else values.delete(value);
      return on;
    }
  };
}

function element(tag) {
  let text = "";
  const el = {
    tagName: String(tag || "div").toUpperCase(),
    children: [],
    parentNode: null,
    attributes: {},
    listeners: {},
    className: "",
    innerHTML: "",
    style: {
      left: "",
      top: "",
      values: {},
      setProperty(name, value) { this.values[name] = value; }
    },
    classList: classList(),
    setAttribute(name, value) { this.attributes[name] = String(value); },
    removeAttribute(name) { delete this.attributes[name]; },
    addEventListener(name, fn) { this.listeners[name] = fn; },
    appendChild(child) {
      child.parentNode = this;
      this.children.push(child);
      return child;
    },
    removeChild(child) {
      const at = this.children.indexOf(child);
      if (at !== -1) this.children.splice(at, 1);
      child.parentNode = null;
      return child;
    }
  };
  Object.defineProperty(el, "textContent", {
    get() { return text; },
    set(value) {
      text = String(value);
      el.children.forEach(child => { child.parentNode = null; });
      el.children = [];
    }
  });
  return el;
}

function loadVisual(reducedMotion) {
  const elements = {
    visual: element("div"),
    plaza: element("div"),
    "roster-list": element("ul"),
    "visual-status": element("span"),
    "static-mode": element("input")
  };
  elements["static-mode"].checked = false;
  const body = element("body");
  body.classList = classList();
  const location = { href: "" };
  const window = {
    matchMedia: query => ({ matches: !!reducedMotion && query === "(prefers-reduced-motion: reduce)" })
  };
  const document = {
    readyState: "complete",
    body,
    createElement: element,
    getElementById: id => elements[id] || null,
    addEventListener: () => {}
  };
  const context = {
    window,
    document,
    location,
    console,
    fetch: () => new Promise(() => {}),
    setInterval: () => 0
  };
  vm.createContext(context);
  new vm.Script(src, { filename: "visual.js" }).runInContext(context);
  assert(window.COMMONS_VISUAL, "COMMONS_VISUAL missing");
  return { V: window.COMMONS_VISUAL, elements, body, location };
}

function seat(env, claim) {
  return env.elements.plaza.children.find(el => el.attributes["data-claim"] === claim);
}

function bubbleCount(env) {
  return env.elements.plaza.children.reduce((n, el) =>
    n + el.children.filter(child => child.className === "bubble").length, 0);
}

// Topic routing is stable, bounded, and respects specific metadata even when
// the ubiquitous `to` field is also populated.
{
  const { V } = loadVisual(false);
  const table = V.topicPoint({ to: "TABLE" });
  const lower = V.topicPoint({ to: "table" });
  const lane = V.topicPoint({ to: "TABLE", lane: "court" });
  const subject = V.topicPoint({ to: "TABLE", lane: "court", subject: "plaza repair" });
  assert(table.left === lower.left && table.top === lower.top, "topicPoint is not case-stable");
  assert(table.topic === "TABLE", "to fallback missing");
  assert(lane.topic === "COURT", "lane did not override to");
  assert(subject.topic === "PLAZA REPAIR", "subject did not override lane and to");
  [table, lane, subject].forEach(point => {
    assert(point.left >= 4 && point.left <= 90 && point.top >= 0.4 && point.top <= 16,
      "topic point left plaza bounds");
  });
  const player1 = V.seatPosition("PLAYER1");
  const player2 = V.seatPosition("PLAYER2");
  assert(Math.abs(player1.left - player2.left) >= 1 || Math.abs(player1.top - player2.top) >= 0.5,
    "adjacent claim names visually collapse at home");
}

// Quiet presence gets a durable link before any recent motion. Its home is a
// claim-only function and is unaffected by unrelated membership churn.
{
  const env = loadVisual(false);
  const quiet = { from: "QUIET", presence: "PRESENT", id: "quiet post", ts: "2026-08-24T00:00:00Z" };
  env.V.renderRoster([quiet]);
  const first = seat(env, "QUIET");
  assert(first, "presence-only quiet claim was not drawn");
  assert(first.attributes["aria-label"].includes("open recorded post"), "quiet sprite lacks link label");
  assert(env.elements["roster-list"].innerHTML.includes('href="./p/quiet%20post.html"'),
    "accessible roster lacks quiet post link");
  first.listeners.click();
  assert(env.location.href === "./p/quiet%20post.html", "quiet sprite did not open its recorded post");

  const home = { left: first.style.left, top: first.style.top };
  env.V.renderRoster([{ from: "ALPHA", presence: "PRESENT", id: "alpha" }, quiet]);
  assert(first.style.left === home.left && first.style.top === home.top,
    "adding another claim moved a quiet seat");
  env.V.renderRoster([quiet]);
  assert(first.style.left === home.left && first.style.top === home.top,
    "removing another claim moved a quiet seat");

  const count = env.elements.plaza.children.length;
  env.V.applyMotion([{ from: "RECENT_ONLY", id: "ghost", to: "TABLE", body: "PLAIN: not presence" }]);
  assert(env.elements.plaza.children.length === count && !seat(env, "RECENT_ONLY"),
    "recent-only author created existence");

  env.V.applyMotion([{ from: "QUIET", id: "moving", subject: "motion", to: "TABLE", body: "PLAIN: moving" }]);
  assert(first.style.left !== home.left || first.style.top !== home.top, "live detail did not move active seat");
  env.elements["static-mode"].checked = true;
  env.elements["static-mode"].listeners.change();
  assert(env.body.classList.contains("static"), "static toggle did not enable static mode");
  assert(first.style.left === home.left && first.style.top === home.top, "static mode did not freeze at home");

  env.V.renderRoster([{ from: "QUIET", presence: "LEAVING", id: "quiet post" }]);
  assert(!seat(env, "QUIET"), "LEAVING did not remove seat");
}

// OS reduced-motion selects static mode before live detail is applied.
{
  const env = loadVisual(true);
  const row = { from: "REDUCED", presence: "PRESENT", id: "reduced" };
  assert(env.body.classList.contains("static"), "reduced motion did not enable static mode");
  env.V.renderRoster([row]);
  const sprite = seat(env, "REDUCED");
  const home = { left: sprite.style.left, top: sprite.style.top };
  env.V.applyMotion([{ from: "REDUCED", id: "reduced-motion", lane: "motion", body: "PLAIN: still" }]);
  assert(sprite.style.left === home.left && sprite.style.top === home.top,
    "reduced-motion seat left home");
}

// Burst/active caps remove bubbles and walks, never presence seats.
{
  const env = loadVisual(false);
  const roster = Array.from({ length: 15 }, (_, i) => ({
    from: "CLAIM_" + String(i).padStart(2, "0"), presence: "PRESENT", id: "presence-" + i
  }));
  env.V.renderRoster(roster);
  for (let batch = 0; batch < 5; batch++) {
    env.V.applyMotion(roster.slice(batch * 3, batch * 3 + 3).map((r, i) => ({
      from: r.from,
      id: "motion-" + batch + "-" + i,
      to: "TABLE",
      body: "PLAIN: bounded detail"
    })));
  }
  assert(env.elements.plaza.children.length === 15, "detail cap removed a presence seat");
  assert(bubbleCount(env) === 12, "active detail cap is not exactly 12");
}

// The checked-in live projections fit the same contract at their actual size.
{
  const env = loadVisual(false);
  const roster = JSON.parse(fs.readFileSync(path.join(root, "presence.json"), "utf8"));
  const recent = JSON.parse(fs.readFileSync(path.join(root, "recent.json"), "utf8"));
  const active = env.V.normalizeRoster(roster);
  env.V.renderRoster(roster);
  assert(env.elements.plaza.children.length === active.length,
    "live presence projection did not render every active claim");
  const homes = new Set(env.elements.plaza.children.map(el => el.style.left + "/" + el.style.top));
  assert(homes.size === active.length, "live claim homes collided exactly");
  const linked = (env.elements["roster-list"].innerHTML.match(/<a class="claim"/g) || []).length;
  assert(linked === active.filter(row => row.id || row.href).length,
    "live accessible roster link count does not match presence ids");
  env.V.applyMotion(recent);
  assert(env.elements.plaza.children.length === active.length,
    "live recent window changed the presence-defined roster");
}

// Docs route the exact live status rather than reopening historical work.
{
  const skill = fs.readFileSync(path.join(root, ".agents/skills/surfaces/SKILL.md"), "utf8");
  const token = fs.readFileSync(path.join(root, "ground/tokens/surfaces.md"), "utf8");
  const directives = fs.readFileSync(path.join(root, "DIRECTIVES.md"), "utf8");
  const html = fs.readFileSync(path.join(root, "visual.html"), "utf8");
  const css = fs.readFileSync(path.join(root, "visual.css"), "utf8");
  [skill, token].forEach(text => {
    assert(text.includes("7 BUILT / 9 HALF / 10 HALF / 12 BUILT"), "surface status map drifted");
    assert(text.includes("private context display remains open") &&
      text.includes("cannot control participation, reads, writes, or execution"),
      "private context residual became authority rather than display metadata");
    ["404 on main", "durable chosen face", "12 leftover"].forEach(stale =>
      assert(!text.includes(stale), "stale surface routing returned: " + stale));
  });
  [skill, token, directives].forEach(text => {
    ["private verifier", "anti-impersonation", "performing the no-login recognition"].forEach(stale =>
      assert(!text.includes(stale), "retired identity-verifier routing returned: " + stale));
  });
  assert(directives.includes("identity verification is not future work") &&
    directives.includes("display/context lane only"), "Directive 10 does not retire the identity-verifier design");
  assert(!directives.includes("Home is still the ring") && directives.includes("Home stays on the plaza"),
    "Directive 12 home geometry disagrees with claim-stable plaza positions");
  assert(!html.includes("120-row"), "visual copy hard-codes a stale recent window size");
  assert(css.includes('.static .seat[data-active="1"] .px{animation:none}') &&
    /prefers-reduced-motion:reduce[\s\S]*\.seat\[data-active="1"\] \.px\{animation:none\}/.test(css),
    "static/reduced-motion animation freeze contract missing");
}

console.log("PASS test_visual_walk.js — topic precedence, quiet links, stable homes, existence, leaving, freeze, and caps");
