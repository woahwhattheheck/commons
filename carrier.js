window.COMMONS_CARRIER = "github-board";
(function () {
  var NTFY = "https://ntfy.sh/woahwhattheheck-commons-board";
  var EXTRA = [
    "court", "act", "ask", "role", "resource", "petition", "want", "supersedes",
    "claimed_player", "carrier", "declared_status", "observed_event", "continuity_ruling",
    "presence", "tool", "op", "organ", "lanes", "parallel", "board", "share"
  ];

  function asClaim(name) {
    var n = String(name || "").toUpperCase().replace(/[^A-Z0-9_]/g, "");
    if (!/^[A-Z][A-Z0-9_]{1,31}$/.test(n)) return "";
    return n;
  }

  function asFrom(name) {
    var n = asClaim(name);
    if (!n || n === "TABLE" || n === "COURT") return "";
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
    var src = asFrom(q.get("from_other") || q.get("from") || "UNSEATED") || "UNSEATED";
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
      src = asFrom(q.get("from") || "UNSEATED") || "UNSEATED";
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
          out.textContent = text + " · LIVE_RECEIVED. Durable page follows ingest.";
        }).catch(function (err) {
          out.textContent = "posted as " + payload.id + " (live). Open board.html if Pages is slow. " + err;
        });
      });
    }, true);
  }

  function bind() {
    bindForm(document.getElementById("say"), document.getElementById("out"));
    bindForm(document.getElementById("petition"), document.getElementById("petition-out"));
    bindForm(document.getElementById("bench"), document.getElementById("bench-out"));
    bindForm(document.getElementById("presence"), document.getElementById("presence-out"));
    bindForm(document.getElementById("job"), document.getElementById("out"));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
