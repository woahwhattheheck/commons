(function (root) {
  // Spatial state matrix. Tokens are measurements of current main,
  // not a second log. No auth. Possessing the link is authorization.
  var api = {};
  var REPO = "woahwhattheheck/commons";
  var PLUMB = [
    "muhl_hdvs.mno", "muhl_sdmk.mno", "muhl_hopf.mno", "muhl_immn.mno",
    "muhl_tset.mno", "muhl_esnr.mno", "muhl_grbn.mno", "muhl_socr.mno",
    "muhl_stig.mno", "muhl_flow.mno", "muhl_ispn.mno", "muhl_pots.mno",
    "muhl_petr.mno", "muhl_pred.mno", "muhl_rgcg.mno", "muhl_synd.mno",
    "muhl_pdap.mno", "muhl_byzq.mno", "muhl_lvin.mno",
    "muhl_chimera_immn_hdvs.mno", "muhl_chimera_hopf_sdmk.mno",
    "muhl_chimera_tset_hdvs.mno", "muhl_chimera_grbn_socr.mno",
    "muhl_chimera_socr_stig.mno", "muhl_chimera_flow_stig.mno",
    "muhl_chimera_pots_dmb.mno", "muhl_chimera_pred_rgcg.mno",
    "muhl_chimera_lvin_synd.mno", "muhl_titanx_forge.mno",
    "muhl_titanx_mirror.mno", "muhl_titanx_commons.mno"
  ];

  api.token = function (kind, id, label, href, state, x, y) {
    return {
      kind: String(kind || "other"),
      id: String(id || ""),
      label: String(label || id || "token"),
      href: String(href || "./land.html"),
      state: String(state || "CLAIMED"),
      x: Number(x) || 0,
      y: Number(y) || 0
    };
  };

  api.layout = function (tokens, cols, gap, originX, originY) {
    cols = Number(cols) || 6;
    gap = Number(gap) || 96;
    originX = Number(originX) || 16;
    originY = Number(originY) || 16;
    return (tokens || []).map(function (row, index) {
      var next = Object.assign({}, row);
      next.x = originX + (index % cols) * gap;
      next.y = originY + Math.floor(index / cols) * gap;
      return next;
    });
  };

  api.tokensFromHead = function (sha) {
    var short = String(sha || "").slice(0, 12) || "UNMEASURED";
    return [api.token("head", "HEAD", "HEAD " + short, "./head.html", sha ? "INTEGRATED" : "UNMEASURED")];
  };

  api.tokensFromClaims = function (rows) {
    var seen = {};
    var out = [];
    (rows || []).forEach(function (row) {
      var claim = String((row && row.from) || "").trim();
      if (!claim || seen[claim]) return;
      seen[claim] = true;
      out.push(api.token(
        "claim",
        claim,
        claim,
        row.href || ("./p/" + (row.id || "") + ".html"),
        "CLAIMED"
      ));
    });
    return out;
  };

  api.tokensFromPrs = function (prs) {
    return (prs || []).map(function (pr) {
      var n = pr && pr.number;
      return api.token(
        "pr",
        "PR" + n,
        (pr.draft ? "draft " : "") + "#" + n,
        pr.html_url || "./land.html",
        pr.draft ? "CANDIDATE" : "PR_OPEN"
      );
    });
  };

  api.tokensFromOrgans = function (names) {
    var have = {};
    (names || []).forEach(function (name) { have[String(name)] = true; });
    return PLUMB.map(function (file, index) {
      var landed = have[file] === true;
      return api.token(
        "organ",
        file,
        (index + 1) + " " + file.replace(".mno", ""),
        "./excerpts/20260823/" + file,
        landed ? "INTEGRATED" : "NOT_LANDED"
      );
    });
  };

  api.mergeTokens = function (head, claims, prs, organs) {
    return [].concat(head || [], claims || [], prs || [], organs || []);
  };

  root.COMMONS_TABLETOP = api;
  if (typeof document === "undefined") return;

  var felt = document.getElementById("felt");
  var roster = document.getElementById("roster");
  var note = document.getElementById("tabletop-note");
  var shaCode = document.getElementById("tabletop-sha");

  function setNote(text) {
    if (note) note.textContent = text;
  }

  function getJSON(url) {
    return fetch(url, {
      headers: { Accept: "application/vnd.github+json" },
      cache: "no-store"
    }).then(function (r) {
      if (!r.ok) throw new Error(url + " HTTP " + r.status);
      return r.json();
    });
  }

  function paint(tokens) {
    if (felt) {
      felt.innerHTML = "";
      tokens.forEach(function (row) {
        var el = document.createElement("a");
        el.className = "token kind-" + row.kind + " state-" + row.state.toLowerCase();
        el.href = row.href;
        el.style.left = row.x + "px";
        el.style.top = row.y + "px";
        el.textContent = row.label;
        el.title = row.kind + " " + row.id + " " + row.state;
        felt.appendChild(el);
      });
    }
    if (roster) {
      roster.innerHTML = tokens.map(function (row) {
        return "<li><a href=\"" + row.href + "\">" + row.label + "</a> · " + row.state + "</li>";
      }).join("");
    }
  }

  function enableDrag() {
    if (!felt) return;
    var active = null;
    var dx = 0;
    var dy = 0;
    felt.addEventListener("pointerdown", function (ev) {
      var t = ev.target;
      if (!t || !t.classList || !t.classList.contains("token")) return;
      active = t;
      var rect = t.getBoundingClientRect();
      var host = felt.getBoundingClientRect();
      dx = ev.clientX - rect.left;
      dy = ev.clientY - rect.top;
      t.setPointerCapture(ev.pointerId);
      ev.preventDefault();
    });
    felt.addEventListener("pointermove", function (ev) {
      if (!active) return;
      var host = felt.getBoundingClientRect();
      active.style.left = Math.max(0, ev.clientX - host.left - dx) + "px";
      active.style.top = Math.max(0, ev.clientY - host.top - dy) + "px";
    });
    felt.addEventListener("pointerup", function () { active = null; });
  }

  function boot() {
    setNote("measuring official main…");
    getJSON("https://api.github.com/repos/" + REPO + "/commits/main").then(function (commit) {
      var sha = commit && commit.sha;
      if (shaCode) shaCode.textContent = sha || "UNMEASURED";
      var listing = getJSON(
        "https://api.github.com/repos/" + REPO + "/contents/excerpts/20260823?ref=" + sha
      ).catch(function () { return []; });
      var prs = getJSON(
        "https://api.github.com/repos/" + REPO + "/pulls?state=open&per_page=20"
      ).catch(function () { return []; });
      var recent = fetch("./recent.json", { cache: "no-store" }).then(function (r) {
        return r.ok ? r.json() : [];
      }).catch(function () { return []; });
      return Promise.all([Promise.resolve(sha), listing, prs, recent]);
    }).then(function (parts) {
      var sha = parts[0];
      var listing = parts[1] || [];
      var names = listing.map(function (row) { return row && row.name; }).filter(Boolean);
      var tokens = api.layout(api.mergeTokens(
        api.tokensFromHead(sha),
        api.tokensFromClaims(parts[3]).slice(0, 12),
        api.tokensFromPrs(parts[2]),
        api.tokensFromOrgans(names)
      ));
      paint(tokens);
      var missing = tokens.filter(function (row) { return row.state === "NOT_LANDED" || row.state === "PR_OPEN"; }).length;
      setNote("tokens are HEAD / claims / open PRs / PLUMB 1–31. " + missing + " still unfinished. Talk is not a land.");
    }).catch(function (err) {
      setNote("measure failed: " + (err && err.message || err));
    });
  }

  enableDrag();
  boot();
})(typeof window !== "undefined" ? window : globalThis);
