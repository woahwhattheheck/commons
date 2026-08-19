window.COMMONS_OWNER = "hashed-ip-door";
(function () {
  // Directive 10. Cite BRYCE-1787134106972-vr8fo8. Do not remint.
  // Law: admin-no-verification-loop-20260819-01. Do not remint.
  // GitHub Pages is static. The browser hashes this network's public IP
  // (pepper + LF + IP) and never writes the address. A match fills visible
  // from=BRYCE. No login. Not a write gate. from= stays a claim.
  // Live bus: topic woahwhattheheck-commons-owner-net (not the board topic).
  // A browser that already holds commons-from=BRYCE publishes the digest
  // (not the IP). Phone and PC on that public IP then match without typing.
  if (window.COMMONS_OWNER_BOOT) return;
  window.COMMONS_OWNER_BOOT = 1;

  var SPEC_NAME = "owner.json";
  var ONLY_CLAIM = "BRYCE";
  var FALLBACK_PEPPER = "commons-owner-v1";
  var HASH_RE = /^[0-9a-f]{64}$/;
  var NET_TOPIC = "woahwhattheheck-commons-owner-net";
  var NET_HOSTS = [
    "https://ntfy.sh",
    "https://ntfy.envs.net",
    "https://ntfy.adminforge.de",
    "https://ntfy.mzte.de"
  ];
  var SEND_GAP_MS = 6 * 60 * 60 * 1000;
  var SENT_KEY = "commons-owner-net-sent";

  function assetUrl(name) {
    var link = document.querySelector('link[rel="stylesheet"]');
    var href = (link && link.getAttribute("href")) || "./commons.css";
    return href.replace(/commons\.css.*$/, name);
  }

  function normalizeIp(raw) {
    var s = String(raw || "").trim();
    if (s.charAt(0) === "[" && s.charAt(s.length - 1) === "]") s = s.slice(1, -1);
    var pct = s.indexOf("%");
    if (pct !== -1) s = s.slice(0, pct);
    if (s.indexOf(":") !== -1) s = s.toLowerCase();
    return s;
  }

  function looksLikeIp(s) {
    s = String(s || "");
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(s)) return true;
    if (s.indexOf(":") !== -1 && /^[0-9a-f:]+$/.test(s)) return true;
    return false;
  }

  function asHash(item) {
    var h = "";
    if (typeof item === "string") h = item.toLowerCase();
    else if (item && typeof item.sha256 === "string") h = item.sha256.toLowerCase();
    return HASH_RE.test(h) ? h : "";
  }

  function sha256hex(s) {
    if (!window.crypto || !crypto.subtle || typeof TextEncoder === "undefined") {
      return Promise.reject(new Error("no-subtle"));
    }
    var bytes = new TextEncoder().encode(s);
    return crypto.subtle.digest("SHA-256", bytes).then(function (buf) {
      var b = new Uint8Array(buf);
      var out = "";
      var i;
      for (i = 0; i < b.length; i++) {
        out += (b[i] < 16 ? "0" : "") + b[i].toString(16);
      }
      return out;
    });
  }

  function digestIp(ip, pepper) {
    var n = normalizeIp(ip);
    if (!looksLikeIp(n)) return Promise.reject(new Error("not-ip"));
    return sha256hex(String(pepper || FALLBACK_PEPPER) + "\n" + n);
  }

  function fetchText(url) {
    return fetch(url, { cache: "no-store", credentials: "omit" }).then(function (r) {
      if (!r.ok) throw new Error("echo");
      return r.text();
    });
  }

  function hashEcho(url, pepper) {
    return fetchText(url).then(function (text) {
      return digestIp(text, pepper);
    });
  }

  function loadSpec() {
    return fetch(assetUrl(SPEC_NAME) + "?v=" + Date.now(), {
      cache: "no-store",
      credentials: "omit"
    }).then(function (r) {
      if (!r.ok) throw new Error("spec");
      return r.json();
    }, function () {
      return { claim: ONLY_CLAIM, algo: "sha256", pepper: FALLBACK_PEPPER, hashes: [] };
    });
  }

  function echoList(spec) {
    var echoes = (spec && spec.echoes) || {};
    var list = echoes.browser || echoes.host || [];
    if (!list.length) {
      list = ["https://api.ipify.org", "https://api64.ipify.org"];
    }
    var out = [];
    var seen = {};
    list.forEach(function (u) {
      u = String(u || "").trim();
      if (!u || seen[u] || u.indexOf("https://") !== 0) return;
      seen[u] = 1;
      out.push(u);
    });
    return out;
  }

  function collectDigests(spec) {
    var pepper = String((spec && spec.pepper) || FALLBACK_PEPPER);
    var urls = echoList(spec);
    return Promise.all(urls.map(function (url) {
      return hashEcho(url, pepper).then(function (h) { return h; }, function () { return ""; });
    })).then(function (got) {
      var uniq = [];
      var seen = {};
      got.forEach(function (h) {
        if (!HASH_RE.test(h) || seen[h]) return;
        seen[h] = 1;
        uniq.push(h);
      });
      return uniq;
    });
  }

  function hashesFromSpec(spec) {
    var out = [];
    var seen = {};
    ((spec && spec.hashes) || []).forEach(function (item) {
      var h = asHash(item);
      if (!h || seen[h]) return;
      seen[h] = 1;
      out.push(h);
    });
    return out;
  }

  function parseNetPayload(raw) {
    var h = "";
    try {
      var o = JSON.parse(String(raw || ""));
      if (o && o.k === "owner-net") h = asHash(o);
    } catch (e) {
      h = asHash(String(raw || "").trim());
    }
    return h;
  }

  function pollNetHost(host) {
    return fetch(host + "/" + NET_TOPIC + "/json?poll=1&since=12h", {
      cache: "no-store",
      credentials: "omit",
      headers: { Accept: "application/x-ndjson" }
    }).then(function (r) {
      if (!r.ok) throw new Error("net");
      return r.text();
    }).then(function (text) {
      var found = [];
      var seen = {};
      String(text || "").split("\n").forEach(function (line) {
        line = line.trim();
        if (!line) return;
        try {
          var ev = JSON.parse(line);
          var h = parseNetPayload(ev.message || ev.title || "");
          if (!h || seen[h]) return;
          seen[h] = 1;
          found.push(h);
        } catch (e) {}
      });
      return found;
    });
  }

  function pollNet() {
    function next(i) {
      if (i >= NET_HOSTS.length) return Promise.resolve([]);
      return pollNetHost(NET_HOSTS[i]).then(function (rows) {
        return rows;
      }, function () {
        return next(i + 1);
      });
    }
    return next(0);
  }

  function rememberedBryce() {
    try {
      return String(localStorage.getItem("commons-from") || "").toUpperCase() === ONLY_CLAIM;
    } catch (e) {
      return false;
    }
  }

  function recentlySent(digest) {
    try {
      var raw = localStorage.getItem(SENT_KEY);
      if (!raw) return false;
      var o = JSON.parse(raw);
      if (!o || o.hash !== digest) return false;
      return (Date.now() - Number(o.ts || 0)) < SEND_GAP_MS;
    } catch (e) {
      return false;
    }
  }

  function markSent(digest) {
    try {
      localStorage.setItem(SENT_KEY, JSON.stringify({ hash: digest, ts: Date.now() }));
    } catch (e) {}
  }

  function publishDigest(digest) {
    if (!HASH_RE.test(digest)) return Promise.resolve(false);
    if (recentlySent(digest)) return Promise.resolve(false);
    var packed = JSON.stringify({ k: "owner-net", sha256: digest });
    function send(i) {
      if (i >= NET_HOSTS.length) return Promise.resolve(false);
      return fetch(NET_HOSTS[i] + "/" + NET_TOPIC, {
        method: "POST",
        credentials: "omit",
        cache: "no-store",
        headers: { "Content-Type": "text/plain" },
        body: packed
      }).then(function (r) {
        if (!r.ok) return send(i + 1);
        markSent(digest);
        return true;
      }, function () {
        return send(i + 1);
      });
    }
    return send(0);
  }

  function anyMatch(digests, known) {
    var i, j;
    for (i = 0; i < digests.length; i++) {
      for (j = 0; j < known.length; j++) {
        if (digests[i] === known[j]) return true;
      }
    }
    return false;
  }

  function fillClaim(claim) {
    var other = document.querySelector("[name=from_other]");
    if (other && String(other.value || "").trim()) return;
    document.querySelectorAll('input[name="from"]').forEach(function (el) {
      if (el.type === "hidden") return;
      if (document.activeElement === el) {
        var cur = String(el.value || "").trim().toUpperCase();
        if (cur && cur !== claim) return;
      }
      el.value = claim;
    });
    try { localStorage.setItem("commons-from", claim); } catch (e) {}
  }

  function ensureMark() {
    var host = document.getElementById("owner-mark");
    if (host) return host;
    var say = document.getElementById("say");
    if (!say || !say.parentNode) return null;
    host = document.createElement("p");
    host.id = "owner-mark";
    host.className = "law";
    say.parentNode.insertBefore(host, say);
    return host;
  }

  function paintMatch(claim) {
    var host = ensureMark();
    if (!host) return;
    host.className = "law";
    host.innerHTML = "this network is " + claim +
      ' (hashed IP, no login). from= is still a claim. <a href="' +
      assetUrl("owner.html") + '">owner door</a>';
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function paintPanel(state, spec, digests, matched) {
    var panel = document.getElementById("owner-panel");
    if (!panel) return;
    var enrolled = hashesFromSpec(spec);
    var digest = (digests && digests[0]) || "";
    var blob = digest ? '{"k":"owner-net","sha256":"' + digest + '"}' : "";
    setText("owner-state", state);
    setText("owner-hash", digest || "(echo unreachable this load)");
    setText("owner-json", blob || "");
    setText("owner-count", String(enrolled.length));
    var knock = document.getElementById("owner-knock-result");
    if (knock) {
      if (matched) knock.textContent = "the door opened. no key. this network was enough.";
      else if (!digest) knock.textContent = "echo missed. try again from the phone or the PC.";
      else knock.textContent = "this network is a guest until a BRYCE browser on it has spoken.";
    }
    var copyBtn = document.getElementById("owner-copy");
    if (copyBtn) copyBtn.disabled = !blob;
  }

  function boot() {
    var panel = document.getElementById("owner-panel");
    loadSpec().then(function (spec) {
      if (!spec || spec.algo !== "sha256") spec = { claim: ONLY_CLAIM, algo: "sha256", pepper: FALLBACK_PEPPER, hashes: [] };
      if (spec.claim && spec.claim !== ONLY_CLAIM) {
        if (panel) paintPanel("bad spec", spec, [], false);
        return;
      }
      var durable = hashesFromSpec(spec);
      return Promise.all([collectDigests(spec), pollNet()]).then(function (pair) {
        var digests = pair[0] || [];
        var live = pair[1] || [];
        var known = durable.concat(live);
        var matched = anyMatch(digests, known);
        var mine = digests[0] || "";
        if (matched) {
          fillClaim(ONLY_CLAIM);
          if (!panel) paintMatch(ONLY_CLAIM);
        }
        if ((matched || rememberedBryce()) && mine) {
          publishDigest(mine);
        }
        if (panel) {
          var state = matched ? "this network is you" :
            (known.length ? "not this network" : "waiting for a BRYCE browser on this network");
          paintPanel(state, spec, digests, matched);
        }
      });
    }).catch(function () {
      if (panel) paintPanel("owner door missed this load", null, [], false);
    });
  }

  function bindCopy() {
    var btn = document.getElementById("owner-copy");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var el = document.getElementById("owner-json");
      var text = el ? String(el.textContent || "").trim() : "";
      if (!text || !navigator.clipboard) return;
      navigator.clipboard.writeText(text).catch(function () {});
    });
  }

  function bindKnock() {
    var btn = document.getElementById("owner-knock");
    if (!btn) return;
    btn.addEventListener("click", function () {
      setText("owner-knock-result", "knocking…");
      boot();
    });
  }

  function start() {
    bindCopy();
    bindKnock();
    boot();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
