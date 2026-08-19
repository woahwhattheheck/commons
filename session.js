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
  function loadReply() {
    if (!/\/p\/[^/]+\.html$/.test(location.pathname || "")) return;
    if (document.querySelector("script[data-reply]")) return;
    var s = document.createElement("script");
    s.src = "../reply.js?v=20260819r";
    s.setAttribute("data-reply", "1");
    document.head.appendChild(s);
  }
  function loadChromeStack() {
    if (!document.getElementById("say")) return;
    if (document.querySelector("link[data-ink-chrome]")) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = "./chrome-stack.css?v=20260819k";
    l.setAttribute("data-ink-chrome", "1");
    document.head.appendChild(l);
  }
  function boot() {
    loadChromeStack();
    paintSession();
    loadPostImage();
    loadReply();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
