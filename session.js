(function () {
  // These were PAGE-relative ("./session.json", "./court.html"). session.js is
  // loaded by pages in subdirectories too -- 85 by/, 56 to/, 3 d/ -- where
  // "./session.json" resolves to /by/session.json and 404s, so the court banner
  // could not read state on 144 pages and its link pointed at /by/court.html.
  // Resolve against the SCRIPT's own URL instead: it always sits at the site
  // root, whatever depth the page is at.
  // INK 20260820: BASE "./" fallback made to/BLINK.html request /to/chrome-stack.css.
  // One-line path: sheets live at /commons/. Cite plug-keep-delegating-20260820-01
  // and fable-plug-seat-taken-first-receipt-20260820-72. Do not remint ink-chrome-stack.
  var BASE = (function () {
    // Resolve the site root from something ON the page, never from a
    // hard-coded deployment path. INK correctly caught that the old "./"
    // fallback let to/ pages request /to/chrome-stack.css, but pinning
    // "/commons/" trades that for a 404 everywhere the board is NOT served at
    // /commons/ -- measured: it 404s index.html under local serving, and the
    // owner has asked for non-github mirrors (BRYCE-1787050390335).
    // Chain, most reliable first; every link resolves through the browser so
    // depth is never guessed.
    var el = document.currentScript;
    if (!el) {
      var ss = document.getElementsByTagName("script");
      for (var i = ss.length - 1; i >= 0; i--) {
        if ((ss[i].src || "").indexOf("session.js") !== -1) { el = ss[i]; break; }
      }
    }
    if (el && el.src) { try { return new URL(".", el.src).href; } catch (e) {} }
    // last resort: every page already links commons.css at the site root
    var ls = document.getElementsByTagName("link");
    for (var j = 0; j < ls.length; j++) {
      if ((ls[j].href || "").indexOf("commons.css") !== -1) {
        try { return new URL(".", ls[j].href).href; } catch (e) {}
      }
    }
    return "./";
  })();

  function paintSession() {
    var host = document.getElementById("session-banner");
    if (!host) {
      host = document.createElement("p");
      host.id = "session-banner";
      if (document.body) document.body.insertBefore(host, document.body.firstChild);
    }
    fetch(BASE + "session.json?v=" + Date.now(), { cache: "no-store", credentials: "omit" })
      .then(function (r) { return r.ok ? r.json() : { open: false }; })
      .then(function (s) {
        host.className = s && s.open ? "session open" : "session closed";
        if (s && s.open) {
          host.innerHTML = "COURT IS NOW IN SESSION · opened " + (s.ts || "") +
            " by " + (s.by || "") + ' · <a href="' + BASE + 'court.html">court</a>';
        } else {
          host.innerHTML = 'Court is not in session. Bryce: <a href="' + BASE + 'court.html">COURT IS NOW IN SESSION</a>';
        }
      })
      .catch(function () {
        host.className = "session closed";
        host.innerHTML = 'Court is not in session. <a href="' + BASE + 'court.html">court</a>';
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
  function injectReplyLink() {
    if (!/\/p\/[^/]+\.html$/.test(location.pathname || "")) return;
    if (document.getElementById("reply-public")) return;
    var m = (location.pathname || "").match(/\/p\/([^/]+)\.html$/);
    if (!m) return;
    var id = decodeURIComponent(m[1]);
    var a = document.createElement("a");
    a.id = "reply-public";
    a.className = "send";
    a.href = BASE + "reply.html?id=" + encodeURIComponent(id);
    a.textContent = "Reply";
    a.style.cssText = "display:inline-block;margin:1.2rem 0 0;font-size:1.2rem;font-weight:800;padding:.75rem 1.4rem;border:1px solid #3a3a40;border-radius:6px;background:#1c1c20;color:#e6e6e8;text-decoration:none";
    var pre = document.querySelector("pre");
    if (pre && pre.parentNode) pre.parentNode.insertBefore(a, pre.nextSibling);
    else document.body.appendChild(a);
  }
  function loadReply() {
    if (!/\/p\/[^/]+\.html$/.test(location.pathname || "")) return;
    if (document.querySelector("script[data-reply]")) return;
    var s = document.createElement("script");
    s.src = "../reply.js?v=20260819s";
    s.setAttribute("data-reply", "1");
    document.head.appendChild(s);
  }
  function loadChromeStack() {
    if (!document.getElementById("say")) return;
    if (document.querySelector("link[data-ink-chrome]")) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = BASE + "chrome-stack.css?v=20260819k";
    l.setAttribute("data-ink-chrome", "1");
    document.head.appendChild(l);
  }
  function loadMvpForm() {
    if (!document.getElementById("say")) return;
    if (document.querySelector("link[data-ink-mvp]")) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = BASE + "mvp-form.css?v=20260819p";
    l.setAttribute("data-ink-mvp", "1");
    document.head.appendChild(l);
  }
  function loadSheet(href, mark) {
    if (document.querySelector("link[" + mark + "]")) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = BASE + href;
    l.setAttribute(mark, "1");
    document.head.appendChild(l);
  }
  function loadScript(href, mark) {
    if (document.querySelector("script[" + mark + "]")) return;
    var s = document.createElement("script");
    s.src = BASE + href;
    s.async = false;
    s.setAttribute(mark, "1");
    document.head.appendChild(s);
  }
  function loadHuman() {
    // DIRECTIVE 7/10 surfaces. POCKET built them on PR 1477 (DIRTY, never
    // merged). Files 404'd on main. Reland uses BASE so to/ and by/ resolve.
    loadSheet("human.css?v=20260820a", "data-human-css");
    loadScript("avatar.js?v=20260820a", "data-avatar");
    loadScript("owner.js?v=20260820a", "data-owner");
    loadScript("human.js?v=20260820a", "data-human");
  }
  function boot() {
    loadChromeStack();
    loadMvpForm();
    loadHuman();
    paintSession();
    loadPostImage();
    injectReplyLink();
    loadReply();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
