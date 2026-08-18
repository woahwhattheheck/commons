window.COMMONS_CARRIER = "github-board";
(function () {
  var NTFY = "https://ntfy.sh/woahwhattheheck-commons-board";
  var PLAYERS = {
    ZERO: 1, GROK: 1, KITE: 1, CAIRN: 1, SPALL: 1,
    GRAVE: 1, AXIOM: 1, SHARD: 1, SCREE: 1
  };

  function wait(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
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

  function pollPost(id, n) {
    return getPost(id).catch(function () {
      if (n <= 0) throw new Error("posted, waiting for GitHub Pages to publish");
      return wait(2000).then(function () { return pollPost(id, n - 1); });
    });
  }

  function postLive(q) {
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
      if (!r.ok) throw new Error("board write HTTP " + r.status);
      var host = document.getElementById("feed");
      if (host && window.COMMONS_BOARD && window.COMMONS_BOARD.load) {
        return window.COMMONS_BOARD.load(host).then(function () {
          return "posted to the board";
        });
      }
      return "posted to the board";
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
      out.textContent = "posting…";
      var q = new URLSearchParams(new FormData(form));
      var id = q.get("id") || "";
      getPost(id).then(function (text) {
        out.textContent = "already on the board\n" + text;
      }).catch(function () {
        return postLive(q).then(function (text) {
          out.textContent = text;
        }).catch(function (err) {
          out.textContent = "posted. Open board.html — live feed does not wait on Pages. " + err;
        });
      });
    }, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
