window.COMMONS_CARRIER = "";
(function () {
  var GH = "https://api.github.com/repos/woahwhattheheck/commons/contents/r/";

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

  function getLive(q) {
    var carrier = window.COMMONS_CARRIER;
    if (!carrier) return Promise.reject(new Error("no live carrier hostname"));
    return fetch(String(carrier).replace(/\/$/, "") + "/say?" + q.toString(), {
      method: "GET",
      credentials: "omit",
      cache: "no-store"
    }).then(function (r) {
      return r.text().then(function (t) {
        if (!r.ok && !t) throw new Error("HTTP " + r.status);
        return t;
      });
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
