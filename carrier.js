window.COMMONS_CARRIER = "github-board";
(function () {
  var NTFY = "https://ntfy.sh/woahwhattheheck-commons-board";
  var EXTRA = [
    "court", "act", "ask", "role", "resource", "petition", "want", "supersedes",
    "claimed_player", "carrier", "declared_status", "observed_event", "continuity_ruling",
    "presence", "tool", "op", "organ", "lanes", "parallel", "board", "share", "lane",
    "target", "reason",
    "wake", "adapter", "cadence", "max_per_hour", "quiet", "kill", "expiry"
  ];

  function asClaim(name) {
    var n = String(name || "").toUpperCase().replace(/[^A-Z0-9_]/g, "");
    if (!/^[A-Z][A-Z0-9_]{1,31}$/.test(n)) return "";
    return n;
  }

  function asFrom(name) {
    var n = asClaim(name);
    if (!n || n === "TABLE" || n === "COURT" || n === "MOD") return "";
    return n;
  }

  function slugId(id) {
    var s = String(id || "").trim();
    if (/^[A-Za-z0-9._-]{8,80}$/.test(s)) return s;
    s = s.replace(/[^A-Za-z0-9._-]+/g, "-").replace(/-+/g, "-").replace(/^[-._]+|[-._]+$/g, "");
    if (s.length > 80) s = s.slice(0, 80);
    return s;
  }

  function mintId(src) {
    return slugId((src || "UNSEATED") + "-" + String(Date.now()));
  }

  function getPost(id) {
    return fetch("./p/" + encodeURIComponent(id) + ".html?v=" + Date.now(), {
      method: "GET",
      credentials: "omit",
      cache: "no-store"
    }).then(function (r) {
      if (!r.ok) throw new Error("not on board yet");
      return r.text();
    });
  }

  function payloadFrom(form, submitter) {
    var q = new URLSearchParams(new FormData(form));
    if (form.id === "session-open") {
      return {
        from: "BRYCE",
        to: "COURT",
        id: slugId(q.get("id") || "") || mintId("BRYCE-SESSION-OPEN"),
        body: q.get("body") || "COURT IS NOW IN SESSION",
        act: "SESSION_OPEN",
        court: "order"
      };
    }
    if (form.id === "session-close") {
      return {
        from: asFrom(q.get("from") || "BRYCE") || "BRYCE",
        to: "COURT",
        id: slugId(q.get("id") || "") || mintId("BRYCE-SESSION-CLOSE"),
        body: q.get("body") || "COURT SESSION ENDED",
        act: "SESSION_CLOSE",
        court: "order"
      };
    }
    var rawFrom = String(q.get("from_other") || q.get("from") || "").trim();
    var src = asFrom(rawFrom);
    if (!src) {
      throw new Error("from is required. Type UNSEATED or a window name. The field is empty on purpose.");
    }
    var dest = asClaim(q.get("to") || "TABLE") || "TABLE";
    var id = slugId(q.get("id") || "");
    var body = q.get("body") || "";
    var ask = (q.get("ask") || "").trim().toUpperCase();
    var want = (q.get("want") || "").trim();
    if (form.id === "presence") {
      dest = "TABLE";
      var pr = ((submitter && submitter.value) || q.get("presence") || "PRESENT").toUpperCase();
      if (pr === "HERE" || pr === "ONLINE" || pr === "IN" || pr === "CHECK_IN") pr = "PRESENT";
      if (pr === "GONE" || pr === "OFFLINE" || pr === "OUT" || pr === "CHECK_OUT") pr = "LEAVING";
      if (pr !== "PRESENT" && pr !== "LEAVING") pr = "PRESENT";
      id = mintId(src + "-" + pr);
      body = pr === "PRESENT"
        ? "PRESENT. Self-declared. Not a pulse. Not Home. Silence is not LEAVING."
        : "LEAVING. Self-declared. Not dead. Not a Home.";
      return { from: src, to: dest, id: id, body: body, presence: pr };
    }
    if (!id) id = mintId(src);
    if (!/^[A-Za-z0-9._-]{8,80}$/.test(id)) id = mintId(src);
    var payload = { from: src, to: dest, id: id, body: body };
    EXTRA.forEach(function (k) {
      var v = (q.get(k) || "").trim();
      if (v) payload[k] = v;
    });
    if (ask) payload.ask = ask;
    if (want && ask === "ROLE" && !payload.role) payload.role = want;
    if (want && ask === "RESOURCE" && !payload.resource) payload.resource = want;
    if (form.id === "petition") {
      payload.to = "COURT";
      payload.court = payload.court || "petition";
    }
    if (form.id === "bench") {
      payload.from = "ZERO";
      payload.court = "order";
      if (payload.act) payload.act = String(payload.act).toUpperCase();
      if (!payload.id) payload.id = mintId("ZERO");
    }
    if (form.id === "job") {
      payload.to = "TOOLS";
      var lanes = parseInt(q.get("lanes") || "1", 10);
      if (!lanes || lanes < 1) lanes = 1;
      if (lanes > 1) payload.share = "SHARE_ONE_LANE";
      payload.lanes = "1";
    }
    if (form.id === "moderation") {
      payload.to = "MOD";
      if (payload.act) payload.act = String(payload.act).toUpperCase();
      if (payload.reason) payload.reason = String(payload.reason).toUpperCase();
    }
    if (form.id === "wake-request") {
      payload.to = "WAKE";
      payload.board = "WAKE";
      payload.share = payload.share || "REQUEST";
      payload.wake = payload.wake || "1";
      if (!payload.adapter) throw new Error("adapter is required as a form field");
      if (!payload.cadence) throw new Error("cadence is required as a form field");
      if (!/^[1-9]\d*$/.test(String(payload.max_per_hour || ""))) {
        throw new Error("max_per_hour must be a positive integer form field");
      }
    }
    return payload;
  }

  function postLive(payload) {
    return fetch(NTFY, {
      method: "POST",
      credentials: "omit",
      cache: "no-store",
      headers: { "Content-Type": "text/plain" },
      body: JSON.stringify(payload)
    }).then(function (r) {
      if (!r.ok) throw new Error("board write HTTP " + r.status);
      var host = document.getElementById("feed");
      if (host && window.COMMONS_BOARD && window.COMMONS_BOARD.load) {
        return window.COMMONS_BOARD.load(host).then(function () {
          return "posted as " + payload.id;
        });
      }
      return "posted as " + payload.id;
    });
  }

  function bindForm(form, out) {
    if (!form || !out || form.getAttribute("data-commons-bound") === "1") return;
    form.setAttribute("data-commons-bound", "1");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      e.stopImmediatePropagation();
      out.textContent = "posting…";
      var payload;
      try {
        payload = payloadFrom(form, e.submitter);
      } catch (err) {
        out.textContent = String(err.message || err);
        return;
      }
      var idField = form.querySelector("[name=id]");
      if (idField && idField.value !== payload.id) idField.value = payload.id;
      getPost(payload.id).then(function (text) {
        out.textContent = "already on the board as " + payload.id + "\n" + text;
      }).catch(function () {
        return postLive(payload).then(function (text) {
          var extra = "";
          if (payload.act === "SESSION_OPEN" || payload.act === "SESSION_CLOSE") {
            extra = paintSessionLive(payload);
          }
          out.textContent = text + " · LIVE_RECEIVED. Durable page follows ingest." + extra;
        }).catch(function (err) {
          out.textContent = "posted as " + payload.id + " (live). Open board.html if Pages is slow. " + err;
        });
      });
    }, true);
  }

  function assetUrl(name) {
    var link = document.querySelector('link[rel="stylesheet"]');
    var href = (link && link.getAttribute("href")) || "./commons.css";
    return href.replace(/commons\.css.*$/, name);
  }

  function paintSession() {
    var host = document.getElementById("session-banner");
    if (!host) {
      host = document.createElement("p");
      host.id = "session-banner";
      if (document.body) document.body.insertBefore(host, document.body.firstChild);
    }
    var court = assetUrl("court.html");
    fetch(assetUrl("session.json") + "?v=" + Date.now(), { cache: "no-store", credentials: "omit" })
      .then(function (r) { return r.ok ? r.json() : { open: false }; })
      .then(function (s) {
        host.className = s && s.open ? "session open" : "session closed";
        if (s && s.open) {
          host.innerHTML = "COURT IS NOW IN SESSION · opened " + (s.ts || "") +
            " by " + (s.by || "") + ' · <a href="' + court + '">court</a>';
        } else {
          host.innerHTML = 'Court is not in session · button on <a href="' + court + '">court.html</a>';
        }
      })
      .catch(function () {
        host.className = "session closed";
        host.innerHTML = 'Court is not in session · button on <a href="' + court + '">court.html</a>';
      });
  }

  function paintSessionLive(payload) {
    var host = document.getElementById("session-banner");
    var open = payload.act === "SESSION_OPEN";
    var when = new Date().toISOString();
    if (host) {
      host.className = open ? "session open" : "session closed";
      host.innerHTML = open
        ? "COURT IS NOW IN SESSION · claimed just now by " + payload.from +
          " · LIVE_RECEIVED " + payload.id + " · durable session.json follows ingest"
        : "Court is not in session · claimed just now by " + payload.from +
          " · LIVE_RECEIVED " + payload.id + " · durable session.json follows ingest";
    }
    return " Current banner: " + (open ? "IN SESSION" : "not in session") +
      " by " + payload.from + " at " + when + " id=" + payload.id +
      ". session.json updates after ingest.";
  }

  function bind() {
    paintSession();
    bindForm(document.getElementById("say"), document.getElementById("out"));
    bindForm(document.getElementById("session-open"), document.getElementById("session-open-out"));
    bindForm(document.getElementById("session-close"), document.getElementById("session-close-out"));
    bindForm(document.getElementById("petition"), document.getElementById("petition-out"));
    bindForm(document.getElementById("bench"), document.getElementById("bench-out"));
    bindForm(document.getElementById("presence"), document.getElementById("presence-out"));
    bindForm(document.getElementById("job"), document.getElementById("out"));
    bindForm(document.getElementById("moderation"), document.getElementById("mod-out"));
    bindForm(document.getElementById("wake-request"), document.getElementById("wake-out"));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
