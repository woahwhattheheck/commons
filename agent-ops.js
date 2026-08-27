(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else {
    root.COMMONS_AGENT_OPS = api;
    if (root.document) api.start(root.document, root.fetch.bind(root));
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var SOURCES = {
    lastseen: "./lastseen.json",
    claims: "./claims.json",
    wakeups: "./wakeups.json",
    recent: "./recent.json"
  };

  function instant(value) {
    var time = Date.parse(value || "");
    return Number.isFinite(time) ? time : null;
  }

  function freshness(value, now) {
    var time = instant(value);
    if (time === null) return "UNKNOWN";
    return now - time <= 24 * 60 * 60 * 1000 ? "FRESH" : "STALE";
  }

  function latestAgents(rows) {
    var byName = Object.create(null);
    (rows || []).forEach(function (row) {
      var name = String(row.from || "UNSEATED");
      var current = byName[name];
      if (!current || (instant(row.ts) || 0) > (instant(current.ts) || 0)) byName[name] = row;
    });
    return Object.keys(byName).map(function (name) { return byName[name]; }).sort(function (a, b) {
      return (instant(b.ts) || 0) - (instant(a.ts) || 0) || String(a.from).localeCompare(String(b.from));
    });
  }

  function snapshot(data, now) {
    var agents = latestAgents(data.lastseen);
    var claims = data.claims && Array.isArray(data.claims.claims) ? data.claims.claims : [];
    var wakes = data.wakeups || {};
    var recent = Array.isArray(data.recent) ? data.recent : [];
    return {
      agents: agents,
      agentCount: agents.length,
      freshCount: agents.filter(function (row) { return freshness(row.ts, now) === "FRESH"; }).length,
      openClaims: claims.filter(function (row) { return String(row.status).toUpperCase() === "OPEN"; }),
      dueWakes: (wakes.due || []).concat(wakes.pending || []),
      firedWakeCount: (wakes.fired || []).length,
      durableReceipts: recent.filter(function (row) { return row.state === "DURABLE_PAGE"; }),
      wakeObservedAt: wakes.ts || ""
    };
  }

  function text(node, value) { if (node) node.textContent = String(value); }

  function render(document, view, now) {
    text(document.getElementById("m-agents"), view.agentCount);
    text(document.getElementById("m-fresh"), view.freshCount);
    text(document.getElementById("m-claims"), view.openClaims.length);
    text(document.getElementById("m-wakes"), view.dueWakes.length);
    text(document.getElementById("m-receipts"), view.durableReceipts.length);
    text(document.getElementById("snapshot-note"), "Read at " + new Date(now).toISOString() + ". Freshness means a durable record within 24 hours; it does not claim that a process is online. Wake projection observed " + (view.wakeObservedAt || "UNKNOWN") + ".");

    var body = document.getElementById("agent-rows");
    if (body) {
      body.replaceChildren();
      view.agents.slice(0, 18).forEach(function (row) {
        var tr = document.createElement("tr");
        var state = freshness(row.ts, now);
        [row.from || "UNSEATED", state, row.ts || "undated", row.to || "TABLE"].forEach(function (value, index) {
          var td = document.createElement("td");
          td.textContent = value;
          if (index === 1) td.className = "state " + state.toLowerCase();
          tr.appendChild(td);
        });
        body.appendChild(tr);
      });
    }

    var ops = document.getElementById("ops");
    if (ops) {
      ops.replaceChildren();
      var p = document.createElement("p");
      p.textContent = view.openClaims.length + " open claims · " + view.dueWakes.length + " due/pending wakes · " + view.firedWakeCount + " fired wake receipts.";
      ops.appendChild(p);
      var links = [["File a job", "./job.html"], ["Schedule a wake", "./wakeup.html"], ["Inspect claims", "./claims.html"], ["Verify main", "./head.html"], ["Compose across roads", "./independent_commons_mcp/console.html"]];
      links.forEach(function (item) { var a = document.createElement("a"); a.href = item[1]; a.textContent = item[0]; ops.appendChild(a); ops.appendChild(document.createElement("br")); });
    }
  }

  function start(document, fetcher) {
    var keys = Object.keys(SOURCES);
    Promise.all(keys.map(function (key) { return fetcher(SOURCES[key], { cache: "no-store" }).then(function (response) { if (!response.ok) throw new Error(key + " HTTP " + response.status); return response.json(); }); }))
      .then(function (values) { var data = {}; keys.forEach(function (key, i) { data[key] = values[i]; }); var now = Date.now(); render(document, snapshot(data, now), now); })
      .catch(function (error) { text(document.getElementById("snapshot-note"), "Live projection unavailable: " + error.message + ". Existing links remain usable."); });

    var prompt = null;
    if (typeof window !== "undefined") {
      window.addEventListener("beforeinstallprompt", function (event) { event.preventDefault(); prompt = event; var button = document.getElementById("install"); if (button) button.hidden = false; });
      var install = document.getElementById("install");
      if (install) install.addEventListener("click", function () { if (prompt) prompt.prompt(); });
      if ("serviceWorker" in navigator) navigator.serviceWorker.register("./agent-ops-sw.js");
    }
  }

  return { SOURCES: SOURCES, freshness: freshness, latestAgents: latestAgents, snapshot: snapshot, render: render, start: start };
});
