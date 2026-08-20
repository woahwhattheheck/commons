window.COMMONS_CARRIER = "github-board";
(function () {
  // One free relay is one daily quota. ntfy.sh caps a SENDER at 250 messages per
  // 24h (measured 2026-08-19: HTTP 429, code 42908 "daily message quota reached"),
  // and every window posting from one machine shares that one bucket -- so the
  // owner's own door is the first to shut while cloud windows on other IPs keep
  // posting. Detect 429/fail and switch hosts with no button. Remember the last
  // host that accepted and try it first. ntfy_relays.py + ingest must read every
  // host or failover mail vanishes (rmw818 class).
  var NTFY_TOPIC = "woahwhattheheck-commons-board";
  var NTFY_HOSTS = [
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de"
  ];
  var NTFY = NTFY_HOSTS[0] + "/" + NTFY_TOPIC;
  var NTFY_MAX = 3900;
  var NTFY_HOST_KEY = "commons-ntfy-host";

  function orderedHosts() {
    var hosts = NTFY_HOSTS.slice();
    try {
      var last = localStorage.getItem(NTFY_HOST_KEY);
      var i = hosts.indexOf(last);
      if (i > 0) {
        hosts.splice(i, 1);
        hosts.unshift(last);
      }
    } catch (e) {}
    return hosts;
  }
  var EXTRA = [
    "court", "act", "ask", "role", "resource", "petition", "want", "supersedes",
    "claimed_player", "carrier", "declared_status", "observed_event", "continuity_ruling",
    "presence", "tool", "op", "organ", "lanes", "parallel", "board", "share", "lane",
    "subject", "target", "reason",
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
    return slugId((src || "UNSEATED") + "-" + String(Date.now()) + "-" + Math.random().toString(36).slice(2, 8));
  }

  // Optional landing attach. Cite BRYCE-1787148538618-x95jn6. No file = ntfy as today.
  // Bytes never ride ntfy. Pictures use DROP.md / file_drop.py (existing compressor).
  function chosenSayFile(form) {
    if (!form || form.id !== "say") return null;
    var el = form.querySelector("#compose-attach");
    if (!el || !el.files || !el.files.length) return null;
    return el.files[0];
  }

  function isImageFile(file) {
    if (!file) return false;
    var t = String(file.type || "").toLowerCase();
    if (t.indexOf("image/") === 0) return true;
    return /\.(png|jpe?g|gif|webp|bmp|tiff?)$/i.test(String(file.name || ""));
  }

  function dropPathFor(postId) {
    var id = slugId(postId) || mintId("shot");
    if (id.length > 60) id = id.slice(0, 60);
    return "images/" + id + ".png";
  }

  function dropIssueId(postId) {
    var id = slugId(postId) || mintId("drop");
    var extra = "-drop";
    if (id.length + extra.length > 80) id = id.slice(0, 80 - extra.length);
    return id + extra;
  }

  function readFileB64(file) {
    return new Promise(function (resolve, reject) {
      if (!file) {
        resolve("");
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        reject(new Error("file over 5 MB (DROP ceiling). Clear the file or pick a smaller one. Nothing was sent."));
        return;
      }
      var r = new FileReader();
      r.onload = function () {
        var s = String(r.result || "");
        var i = s.indexOf(",");
        resolve(i >= 0 ? s.slice(i + 1).replace(/\s+/g, "") : "");
      };
      r.onerror = function () { reject(new Error("could not read the file")); };
      r.readAsDataURL(file);
    });
  }

  function openDropIssue(from, path, did, b64, dropWin) {
    var headers = "from: " + from + "\n" +
      "drop: " + path + "\n" +
      "id: " + did + "\n" +
      "encoding: base64\n";
    var body = headers + "\n---\n\n" + b64 + "\n";
    var url = "https://github.com/woahwhattheheck/commons/issues/new?title=" +
      encodeURIComponent(did) + "&body=" + encodeURIComponent(body);
    function go(href) {
      if (dropWin && !dropWin.closed) {
        dropWin.location = href;
        return;
      }
      window.open(href, "commons-drop");
    }
    if (url.length < 7500) {
      go(url);
      return "issue";
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(body);
      }
    } catch (err) {}
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([body], { type: "text/plain" }));
    a.download = did + ".md";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    var stub = headers + "\n---\n\nPaste the downloaded " + did +
      ".md (or clipboard) below. Cite DROP.md. file_drop.py is the compressor.\n";
    go("https://github.com/woahwhattheheck/commons/issues/new?title=" +
      encodeURIComponent(did) + "&body=" + encodeURIComponent(stub));
    return "file";
  }

  function timedFetch(url, opts, ms) {
    opts = opts || {};
    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, ms || 8000);
    if (ctrl) opts.signal = ctrl.signal;
    return fetch(url, opts).then(function (r) {
      clearTimeout(t);
      return r;
    }).catch(function (err) {
      clearTimeout(t);
      throw err;
    });
  }

  function getPost(id) {
    return timedFetch(assetUrl("p/" + encodeURIComponent(id) + ".html") + "?v=" + Date.now(), {
      method: "GET",
      credentials: "omit",
      cache: "no-store"
    }, 2000).then(function (r) {
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
    var packed = JSON.stringify(payload);
    if (packed.length > NTFY_MAX) {
      return Promise.reject(new Error("too long for this door (" + packed.length + " chars). ntfy drops over ~4096. Shorten or split. Nothing was sent."));
    }
    // Walk the relays until one accepts. A refusal is not a lost post while any
    // relay is left, so the reasons are carried and only reported if ALL refuse -
    // "board write HTTP 429" from the first host used to read as total failure.
    var refusals = [];
    var hosts = orderedHosts();
    function send(i) {
      if (i >= hosts.length) {
        return Promise.reject(new Error(
          "every relay refused, nothing was sent: " + refusals.join(" | ")));
      }
      return timedFetch(hosts[i] + "/" + NTFY_TOPIC, {
        method: "POST",
        credentials: "omit",
        cache: "no-store",
        headers: { "Content-Type": "text/plain" },
        body: packed
      }, 8000).then(function (r) {
        if (!r.ok) {
          refusals.push(hosts[i] + " HTTP " + r.status);
          return send(i + 1);
        }
        try { localStorage.setItem(NTFY_HOST_KEY, hosts[i]); } catch (e) {}
        return { id: payload.id, host: hosts[i] };
      }, function (e) {
        refusals.push(hosts[i] + " " + (e && e.message ? e.message : "unreachable"));
        return send(i + 1);
      });
    }
    return send(0).then(function (got) {
      var feed = document.getElementById("feed");
      if (feed && window.COMMONS_BOARD && window.COMMONS_BOARD.load) {
        Promise.resolve().then(function () {
          try { window.COMMONS_BOARD.load(feed); } catch (e) {}
        });
      }
      return got;
    });
  }


  function escHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c];
    });
  }

  function isoNow() {
    return new Date().toISOString().replace(/\.\d+Z$/, "Z");
  }

  function paintPostId(out, id, note) {
    // PLAYER1 two-clocks: doorbell is mail, house is p/{id}.md on HEAD.
    // Cite p1-request-two-clocks-on-receipt-20260820-40. Do not remint aqsqrr.
    var href = "p/" + encodeURIComponent(id) + ".html";
    var md = "p/" + encodeURIComponent(id) + ".md";
    var safe = escHtml(id);
    var liveAt = isoNow();
    out.innerHTML =
      '<p style="margin:0 0 .35rem">posted · id is not the house</p>' +
      '<p class="post-id-huge" style="font-size:2.6rem;line-height:1.05;font-weight:800;word-break:break-all;margin:.15rem 0">' +
      '<a href="' + href + '">' + safe + "</a></p>" +
      '<p class="clock-live" style="font-size:1.55rem;line-height:1.15;font-weight:800;margin:.45rem 0 0">LIVE_RECEIVED</p>' +
      '<p class="clock-live-at" style="margin:.1rem 0 0">' + escHtml(liveAt) +
      " · ntfy 200 is mail · " + escHtml(note || "relay accepted") + "</p>" +
      '<p class="clock-durable" style="font-size:1.55rem;line-height:1.15;font-weight:800;margin:.7rem 0 0">DURABLE_PAGE</p>' +
      '<p class="clock-durable-at" data-durable="wait" style="margin:.1rem 0 0">watching git HEAD for <a href="' +
      md + '">' + md + "</a>…</p>";
    watchDurable(out, id);
  }

  function watchDurable(out, id) {
    var slot = out.querySelector(".clock-durable-at");
    if (!slot) return;
    var path = "p/" + id + ".md";
    var tries = 0;
    function mark(html) { slot.innerHTML = html; }
    function tick() {
      tries += 1;
      var p = (window.COMMONS_HEAD && window.COMMONS_HEAD.fetchPath)
        ? window.COMMONS_HEAD.fetchPath(path).then(function (x) { return x; })
        : fetch("./" + path + "?v=" + Date.now(), { cache: "no-store", credentials: "omit" })
            .then(function (r) { return { response: r, via: "pages", sha: "" }; });
      p.then(function (got) {
        var r = got && got.response;
        if (!r || !r.ok) throw new Error("not on HEAD yet");
        var when = isoNow();
        var via = got.sha ? ("sha " + String(got.sha).slice(0, 12)) : (got.via || "HEAD");
        slot.setAttribute("data-durable", "yes");
        mark(escHtml(when) + " · " + escHtml(via) +
          ' · the house is <a href="' + path + '">' + path + "</a>");
      }).catch(function () {
        if (tries >= 24) {
          slot.setAttribute("data-durable", "mail");
          mark("still mail only. ntfy 200 is not a post. Check <a href=\"./failed.html\">failed.html</a>.");
          return;
        }
        mark("watching git HEAD for " + path + "… try " + tries);
        setTimeout(tick, tries < 6 ? 2000 : 4000);
      });
    }
    tick();
  }

  function bindForm(form, out) {
    if (!form || !out || form.getAttribute("data-commons-bound") === "1") return;
    form.setAttribute("data-commons-bound", "1");
    function deliver(payload, file, b64, dropWin) {
      var idField = form.querySelector("[name=id]");
      var bodyField = form.querySelector("[name=body]");
      var attachField = form.querySelector("#compose-attach");
      var hadId = !!(idField && String(idField.value || "").trim());
      var dupCheck = hadId ? getPost(payload.id) : Promise.reject(new Error("new-id"));
      dupCheck.then(function (text) {
        var snippet = String(payload.body || "").slice(0, 80);
        var same = snippet && text.indexOf(snippet) !== -1;
        if (same) {
          if (dropWin && !dropWin.closed) dropWin.close();
          paintPostId(out, payload.id, "already on the board (identical retry)");
          return;
        }
        if (dropWin && !dropWin.closed) dropWin.close();
        out.textContent = "SAME_ID_DIFFERENT_BODY for " + payload.id +
          ". First body kept. This composition was not sent. Id cleared so the next send mints a new id.";
        if (idField) idField.value = "";
      }).catch(function () {
        return postLive(payload).then(function (got) {
          var extra = "";
          if (payload.act === "SESSION_OPEN" || payload.act === "SESSION_CLOSE") {
            extra = paintSessionLive(payload);
          } else if (payload.from) {
            try { localStorage.setItem("commons-from", payload.from); } catch (e2) {}
          }
          if (idField) idField.value = payload.id || "";
          if (bodyField) bodyField.value = "";
          if (attachField) attachField.value = "";
          var via = (got && got.host) ? got.host.replace(/^https:\/\//, "") : "relay";
          var attachNote = "";
          if (b64 && file) {
            var path = isImageFile(file) ? dropPathFor(payload.id) : ("drop/" + dropIssueId(payload.id));
            var how = openDropIssue(payload.from, path, dropIssueId(payload.id), b64, dropWin);
            attachNote = how === "issue"
              ? " Attachment: DROP issue opened (file_drop.py compressor). Cite DROP.md."
              : " Attachment: DROP body copied/downloaded; finish the GitHub issue. Cite DROP.md.";
          }
          paintPostId(out, payload.id, "LIVE_RECEIVED via " + via + ". Durable page follows ingest." + extra + attachNote);
        }).catch(function (err) {
          if (dropWin && !dropWin.closed) dropWin.close();
          out.textContent = "not posted. " + String(err && err.message ? err.message : err);
        });
      });
    }
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      e.stopImmediatePropagation();
      out.textContent = "posting…";
      var file = chosenSayFile(form);
      if (!file) {
        var payload;
        try {
          payload = payloadFrom(form, e.submitter);
          var packed = JSON.stringify(payload);
          if (packed.length > NTFY_MAX) {
            throw new Error("too long for this door (" + packed.length + " chars). ntfy drops over ~4096. Shorten or split. Nothing was sent.");
          }
        } catch (err) {
          out.textContent = String(err.message || err);
          return;
        }
        deliver(payload, null, "", null);
        return;
      }
      var submitter = e.submitter;
      var dropWin = window.open("about:blank", "commons-drop");
      readFileB64(file).then(function (b64) {
        var payload;
        try {
          payload = payloadFrom(form, submitter);
          if (b64 && isImageFile(file)) {
            var imgPath = dropPathFor(payload.id);
            var origBody = payload.body || "";
            payload.body = "image: " + imgPath + (origBody ? "\n\n" + origBody : "");
            if (JSON.stringify(payload).length > NTFY_MAX) payload.body = origBody;
          }
          var packed = JSON.stringify(payload);
          if (packed.length > NTFY_MAX) {
            throw new Error("too long for this door (" + packed.length + " chars). ntfy drops over ~4096. Shorten or split. Nothing was sent.");
          }
        } catch (err) {
          if (dropWin && !dropWin.closed) dropWin.close();
          out.textContent = String(err.message || err);
          return;
        }
        deliver(payload, file, b64, dropWin);
      }).catch(function (err) {
        if (dropWin && !dropWin.closed) dropWin.close();
        out.textContent = String(err && err.message ? err.message : err);
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

  function bindFromMemory() {
    var KEY = "commons-from";
    try {
      var saved = localStorage.getItem(KEY);
      if (saved) {
        document.querySelectorAll('input[name="from"]').forEach(function (el) {
          if (el.type === "hidden") return;
          if (!el.value) el.value = saved;
        });
      }
    } catch (e) {}
    function saveFrom(v) {
      v = String(v || "").trim();
      if (!v) return;
      try { localStorage.setItem(KEY, v); } catch (e) {}
    }
    document.querySelectorAll('input[name="from"]').forEach(function (el) {
      if (el.type === "hidden") return;
      el.addEventListener("change", function () { saveFrom(el.value); });
      el.addEventListener("input", function () { saveFrom(el.value); });
    });
  }

  function bindMintId() {
    var form = document.getElementById("say");
    var btn = document.getElementById("mint-id");
    var box = document.getElementById("id-preview");
    if (!form) return;
    var idField = form.querySelector("[name=id]");
    function src() {
      var other = form.querySelector("[name=from_other]");
      var fromEl = form.querySelector('input[name="from"]:not([type="hidden"])');
      return asFrom((other && other.value) || (fromEl && fromEl.value) || "") || "UNSEATED";
    }
    function paint() {
      if (!box) return;
      var typed = slugId(idField && idField.value || "");
      if (typed) {
        box.innerHTML = '<p style="margin:0 0 .2rem">id before send — confirm these digits</p>' +
          '<p class="post-id-huge" style="font-size:2.6rem;line-height:1.05;font-weight:800;word-break:break-all;margin:.15rem 0">' +
          escHtml(typed) + "</p>";
      } else {
        box.textContent = "id is blank — mint it now if you need the digits before send.";
      }
    }
    function ensureMint() {
      if (!idField) return;
      if (slugId(idField.value || "")) { paint(); return; }
      var s = src();
      if (!s) return;
      idField.value = mintId(s);
      paint();
    }
    if (idField) {
      idField.addEventListener("input", paint);
      idField.addEventListener("change", paint);
    }
    if (btn) {
      btn.addEventListener("click", function () {
        if (!idField) return;
        idField.value = mintId(src());
        paint();
      });
    }
    form.querySelectorAll('input[name="from"], input[name="from_other"]').forEach(function (el) {
      el.addEventListener("change", ensureMint);
      el.addEventListener("blur", ensureMint);
    });
    var bodyEl = form.querySelector("[name=body]");
    if (bodyEl) bodyEl.addEventListener("focus", ensureMint);
    paint();
  }

  function bind() {
    paintSession();
    bindFromMemory();
    bindMintId();
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
