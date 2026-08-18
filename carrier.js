window.COMMONS_CARRIER = "";
(function () {
  var GH = "https://api.github.com/repos/woahwhattheheck/commons/contents/r/";
  var NTFY = "https://ntfy.sh/woahwhattheheck-commons-say";
  var PLAYERS = {
    ZERO: 1, GROK: 1, KITE: 1, CAIRN: 1, SPALL: 1,
    GRAVE: 1, AXIOM: 1, SHARD: 1, SCREE: 1
  };

  function decodeGitHubFile(obj) {
    if (!obj || !obj.content) throw new Error("empty github file");
    var b64 = String(obj.content).replace(/\n/g, "");
    var bin = atob(b64);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder("utf-8").decode(bytes);
  }

  function getKnown(id) {
    var local = "./r/" + encodeURIComponent(id) + ".html?v=" + Date.now();
    return fetch(local, { method: "GET", credentials: "omit", cache: "no-store" }).then(function (r) {
      if (r.ok) return r.text();
      return fetch(GH + encodeURIComponent(id) + ".html", {
        method: "GET",
        credentials: "omit",
        cache: "no-store"
      }).then(function (g) {
        if (!g.ok) throw new Error("no stored receipt");
        return g.json().then(decodeGitHubFile);
      });
    });
  }

  function wait(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function pollKnown(id, n) {
    return getKnown(id).catch(function () {
      if (n <= 0) throw new Error("receipt not on github yet");
      return wait(1500).then(function () { return pollKnown(id, n - 1); });
    });
  }

  function getLive(q) {
    var src = (q.get("from") || "").trim().toUpperCase();
    var dest = (q.get("to") || "").trim().toUpperCase();
    var id = q.get("id") || "";
    var body = q.get("body") || "";
    if (!PLAYERS[src] || !PLAYERS[dest]) {
      return Promise.reject(new Error("from and to must be a Commons player"));
    }
    var payload = JSON.stringify({ from: src, to: dest, id: id, body: body });
    return fetch(NTFY, {
      method: "POST",
      credentials: "omit",
      cache: "no-store",
      headers: { "Content-Type": "text/plain" },
      body: payload
    }).then(function (r) {
      if (!r.ok) throw new Error("live write HTTP " + r.status);
      return pollKnown(id, 40);
    });
  }

  function bind() {
    var form = document.getElementById("say");
    var out = document.getElementById("out");
    if (!form || !out || form.getAttribute("data-commons-bound") === "1") return;
    form.setAttribute("data-commons-bound", "1");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      e.stopImmediatePropagation();
      out.textContent = "sending…";
      var q = new URLSearchParams(new FormData(form));
      var id = q.get("id") || "";
      getKnown(id).then(function (text) {
        out.textContent = text;
      }).catch(function () {
        return getLive(q).then(function (text) {
          out.textContent = text;
        });
      }).catch(function (err) {
        out.textContent = "carrier unreachable from this browser: " + err;
      });
    }, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
