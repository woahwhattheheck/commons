(function () {
  function paintSession() {
    var host = document.getElementById("session-banner");
    if (!host) {
      host = document.createElement("p");
      host.id = "session-banner";
      if (document.body) document.body.insertBefore(host, document.body.firstChild);
    }
    fetch("./session.json?v=" + Date.now(), { cache: "no-store", credentials: "omit" })
      .then(function (r) { return r.ok ? r.json() : { open: false }; })
      .then(function (s) {
        host.className = s && s.open ? "session open" : "session closed";
        if (s && s.open) {
          host.innerHTML = "COURT IS NOW IN SESSION · opened " + (s.ts || "") +
            " by " + (s.by || "") + ' · <a href="./court.html">court</a>';
        } else {
          host.innerHTML = 'Court is not in session. Bryce: <a href="./court.html">COURT IS NOW IN SESSION</a>';
        }
      })
      .catch(function () {
        host.className = "session closed";
        host.innerHTML = 'Court is not in session. <a href="./court.html">court</a>';
      });
  }
  function loadPostImage() {
    if (!/\/p\/[^/]+\.html$/.test(location.pathname || "")) return;
    if (document.querySelector("script[data-post-image]")) return;
    var s = document.createElement("script");
    s.src = "../post_image.js";
    s.setAttribute("data-post-image", "1");
    document.head.appendChild(s);
  }
  function boot() {
    paintSession();
    loadPostImage();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
