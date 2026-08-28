/* Observatory renderer. Fetch the bake. No fake live ticks. No analytics. */
(function () {
  const SOURCE = "./observatory.json";

  function el(id) {
    return document.getElementById(id);
  }

  function text(value) {
    if (value === null || value === undefined || value === "") return "UNKNOWN";
    return String(value);
  }

  function pill(state) {
    const span = document.createElement("span");
    span.className = "state state-" + text(state);
    span.textContent = text(state);
    return span;
  }

  function evidenceNode(rows) {
    const wrap = document.createElement("details");
    wrap.className = "evidence";
    const sum = document.createElement("summary");
    sum.textContent = "evidence";
    wrap.appendChild(sum);
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(rows || [], null, 2);
    wrap.appendChild(pre);
    return wrap;
  }

  function fillList(node, items, render) {
    node.textContent = "";
    if (!items || !items.length) {
      const empty = document.createElement("li");
      empty.className = "empty";
      empty.textContent = "None observed.";
      node.appendChild(empty);
      return;
    }
    items.forEach(function (item) {
      node.appendChild(render(item));
    });
  }

  function cockpit(snap) {
    const lines = el("cockpit-lines");
    lines.textContent = "";
    (snap.cockpit && snap.cockpit.lines || []).forEach(function (line) {
      const li = document.createElement("li");
      li.textContent = line;
      lines.appendChild(li);
    });
    const counts = (snap.cockpit && snap.cockpit.counts) || {};
    const states = counts.states || {};
    const classes = counts.classifications || {};
    const metrics = [
      ["confirmed active", counts.confirmed_active],
      ["working", states.WORKING],
      ["blocked", states.BLOCKED],
      ["stale", states.STALE],
      ["local", classes.LOCAL],
      ["cloud", classes.CLOUD],
      ["browser", classes.BROWSER],
      ["automation", classes.AUTOMATION],
      ["unknown class", classes.UNKNOWN],
      ["presence claims", counts.presence_claims],
      ["collisions", counts.collisions],
      ["cash USD", snap.economy && snap.economy.collected_cash_usd]
    ];
    const box = el("metrics");
    box.textContent = "";
    metrics.forEach(function (pair) {
      const div = document.createElement("div");
      div.className = "metric";
      const strong = document.createElement("strong");
      strong.textContent = pair[1] === undefined || pair[1] === null ? "—" : String(pair[1]);
      const span = document.createElement("span");
      span.textContent = pair[0];
      div.appendChild(strong);
      div.appendChild(span);
      box.appendChild(div);
    });
    const status = el("snapshot-status");
    const sha = snap.head && snap.head.sha ? String(snap.head.sha).slice(0, 12) : "UNKNOWN";
    status.textContent = "Bake " + text(snap.schema) + " · head " + sha + " · stale_after=" + text(snap.stale_after_seconds) + "s. Not a live websocket.";
  }

  function sessions(snap) {
    const body = el("session-rows");
    body.textContent = "";
    const rows = snap.sessions || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="11">Zero sessions confirmed. Quiet presence is listed below.</td></tr>';
      return;
    }
    rows.forEach(function (row) {
      const tr = document.createElement("tr");
      function td(value, raw) {
        const cell = document.createElement("td");
        if (raw) cell.appendChild(value);
        else cell.textContent = text(value);
        tr.appendChild(cell);
      }
      td(row.label || row.session_id);
      td(pill(row.classification), true);
      td(pill(row.state), true);
      td(text(row.model) + " / " + text(row.harness));
      td((row.tools || []).join(", ") || "UNKNOWN");
      td(row.task_id);
      td((row.lease && row.lease.lease_id) ? (text(row.lease.lease_id) + " until " + text(row.lease.until)) : "descriptive only");
      td(row.blocker && row.blocker.type && row.blocker.type !== "UNKNOWN" ? (text(row.blocker.type) + " " + text(row.blocker.detail)) : "none");
      td(row.checkpoint);
      td(row.last_ts);
      const ev = document.createElement("td");
      ev.appendChild(evidenceNode(row.evidence));
      tr.appendChild(ev);
      body.appendChild(tr);
    });
  }

  function presence(snap) {
    const body = el("presence-rows");
    body.textContent = "";
    (snap.presence || []).forEach(function (row) {
      const tr = document.createElement("tr");
      [row.claim, row.presence, row.motion, row.id, row.ts].forEach(function (value) {
        const td = document.createElement("td");
        td.textContent = text(value);
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    if (!body.children.length) {
      body.innerHTML = '<tr><td colspan="5">No presence bake.</td></tr>';
    }
  }

  function work(snap) {
    const body = el("work-rows");
    body.textContent = "";
    const rows = snap.work_map || [];
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="7">No observed tasks.</td></tr>';
      return;
    }
    rows.forEach(function (row) {
      const tr = document.createElement("tr");
      const cells = [
        row.task_id,
        row.state,
        text(row.owner_claim || row.session_id),
        row.objective,
        (row.claimed_paths || []).join(", ") || "UNKNOWN",
        typeof row.checkpoint === "string" ? row.checkpoint : JSON.stringify(row.checkpoint || "UNKNOWN"),
        row.expected_next || "UNKNOWN"
      ];
      cells.forEach(function (value) {
        const td = document.createElement("td");
        td.textContent = text(value);
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
  }

  function findings(id, rows) {
    const node = el(id);
    fillList(node, rows, function (item) {
      const li = document.createElement("li");
      li.textContent = text(item.kind) + " — " + JSON.stringify(item, null, 0).slice(0, 280);
      li.appendChild(evidenceNode(item.evidence || item));
      return li;
    });
  }

  function timeline(snap, filter) {
    const node = el("timeline");
    const rows = (snap.timeline || []).filter(function (row) {
      if (filter.kind && text(row.kind).toUpperCase() !== filter.kind.toUpperCase()) return false;
      if (filter.session && text(row.session_id).toLowerCase().indexOf(filter.session.toLowerCase()) < 0) return false;
      if (filter.harness && text(row.harness).toLowerCase().indexOf(filter.harness.toLowerCase()) < 0) return false;
      if (filter.task && text(row.task_id).toLowerCase().indexOf(filter.task.toLowerCase()) < 0) return false;
      if (filter.path && text(row.path).toLowerCase().indexOf(filter.path.toLowerCase()) < 0) return false;
      if (filter.blocker && text(row.blocker).toLowerCase().indexOf(filter.blocker.toLowerCase()) < 0) return false;
      if (filter.provider && JSON.stringify(row).toLowerCase().indexOf(filter.provider.toLowerCase()) < 0) return false;
      if (filter.landing) {
        const blob = (text(row.kind) + " " + JSON.stringify(row)).toLowerCase();
        if (blob.indexOf(filter.landing.toLowerCase()) < 0) return false;
      }
      if (filter.cost) {
        const blob = JSON.stringify(row.cost || "").toLowerCase();
        if (blob.indexOf(filter.cost.toLowerCase()) < 0) return false;
      }
      if (filter.revenue) {
        const blob = JSON.stringify(row).toLowerCase();
        if (blob.indexOf(filter.revenue.toLowerCase()) < 0) return false;
      }
      if (filter.klass) {
        const blob = (text(row.classification) + " " + text(row.kind) + " " + text(row.state)).toUpperCase();
        if (blob.indexOf(filter.klass.toUpperCase()) < 0) return false;
      }
      return true;
    });
    fillList(node, rows, function (row) {
      const li = document.createElement("li");
      li.textContent = text(row.ts) + " · " + text(row.kind) + " · session " + text(row.session_id) + " · task " + text(row.task_id);
      li.appendChild(evidenceNode(row.evidence));
      return li;
    });
  }

  function briefing(snap) {
    const node = el("briefing");
    const brief = snap.briefing || {};
    const parts = [
      brief.architecture,
      brief.economic_truth,
      "commitments: " + (brief.active_commitments || []).join(", "),
      "blocked: " + (brief.blocked_work || []).join(", ")
    ];
    node.textContent = "";
    parts.forEach(function (line) {
      const p = document.createElement("p");
      p.textContent = text(line);
      node.appendChild(p);
    });
    (brief.statements || []).forEach(function (row) {
      const p = document.createElement("p");
      p.textContent = text(row.text);
      p.appendChild(evidenceNode(row.evidence));
      node.appendChild(p);
    });
  }

  function handoff(snap) {
    const node = el("handoff");
    if (!node) return;
    const brief = (snap.briefing && snap.briefing.handoff) || {};
    const lines = brief.read_this || (snap.cockpit && snap.cockpit.lines) || [];
    node.textContent = "";
    const intro = document.createElement("p");
    intro.textContent = "Continue via " + text(brief.continue_tool || "continue_from_observation") + ". Do not replay a finished prompt.";
    node.appendChild(intro);
    lines.forEach(function (line) {
      const p = document.createElement("p");
      p.textContent = text(line);
      node.appendChild(p);
    });
  }

  function economy(snap) {
    const e = snap.economy || {};
    el("economy").textContent =
      "collected_cash_usd=" + text(e.collected_cash_usd) +
      " · cash_state=" + text(e.cash_state) +
      " · bank_available=" + text(e.bank_available) +
      " · replies_observed=" + text(e.replies_observed) +
      " · contacts_sent=" + text(e.distinct_contacts_sent) +
      ". Drafts, invoices, checkout pages, and unverified interest are not revenue.";
  }

  function routes(snap) {
    fillList(el("routes"), snap.routes || [], function (row) {
      const li = document.createElement("li");
      li.textContent = text(row.session_id) + " · " + text(row.health) + " · " + text(row.reason);
      return li;
    });
  }

  function paint(snap, filter) {
    cockpit(snap);
    sessions(snap);
    presence(snap);
    work(snap);
    findings("collision-list", snap.collisions);
    findings("attention-list", snap.attention);
    timeline(snap, filter || {});
    briefing(snap);
    handoff(snap);
    economy(snap);
    routes(snap);
  }

  function fail(message) {
    el("snapshot-status").textContent = message;
    el("snapshot-status").className = "note error";
  }

  fetch(SOURCE, { cache: "no-store" }).then(function (res) {
    if (!res.ok) throw new Error("observatory.json HTTP " + res.status);
    return res.json();
  }).then(function (snap) {
    if (!snap || snap.schema !== "commons-observatory/v0.1") {
      fail("Malformed snapshot: schema is not commons-observatory/v0.1.");
      return;
    }
    window.COMMONS_OBSERVATORY = snap;
    paint(snap, {});
    el("timeline-filters").addEventListener("submit", function (ev) {
      ev.preventDefault();
      const data = new FormData(ev.target);
      paint(snap, { kind: data.get("kind"), session: data.get("session"), harness: data.get("harness"), klass: data.get("klass"), task: data.get("task"), path: data.get("path"), provider: data.get("provider"), landing: data.get("landing"), blocker: data.get("blocker"), cost: data.get("cost"), revenue: data.get("revenue") });
    });
    el("timeline-filters").addEventListener("reset", function () {
      setTimeout(function () { paint(snap, {}); }, 0);
    });
  }).catch(function (err) {
    fail("Could not load observatory.json (" + err.message + "). Open the JSON file directly. This is a bake, not a live socket.");
  });
})();
