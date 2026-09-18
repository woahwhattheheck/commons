(function () {
  // DIRECTIVE 10. Knows this phone/PC. Pages cannot see an IP.
  // Not IP-as-proof. Cite BRYCE-1787134106972-vr8fo8, ROOT_CODEX 023.
  var KEY = "commons-owner-pin";

  function readPin() {
    try { return JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { return null; }
  }

  function writePin(kind) {
    var k = String(kind || "").toLowerCase();
    if (k !== "phone" && k !== "pc") return { ok: false, error: "kind is phone or pc" };
    var pin = {
      kind: k,
      ts: new Date().toISOString(),
      ua: String(navigator.userAgent || "").slice(0, 80)
    };
    try { localStorage.setItem(KEY, JSON.stringify(pin)); } catch (e) {
      return { ok: false, error: "could not save on this browser" };
    }
    return { ok: true, pin: pin };
  }

  function clearPin() {
    try { localStorage.removeItem(KEY); } catch (e) {}
  }

  function paint() {
    var pin = readPin();
    var host = document.getElementById("owner-pin-banner");
    if (!pin || !pin.kind) {
      if (host) host.remove();
      return pin;
    }
    if (!host) {
      host = document.createElement("p");
      host.id = "owner-pin-banner";
      if (document.body) {
        var banner = document.getElementById("session-banner");
        if (banner && banner.nextSibling) document.body.insertBefore(host, banner.nextSibling);
        else document.body.insertBefore(host, document.body.firstChild);
      }
    }
    host.textContent = "This browser is pinned as the owner's " + pin.kind +
      " · no login · not an IP · " + (pin.ts || "");
    return pin;
  }

  window.COMMONS_OWNER = { readPin: readPin, writePin: writePin, clearPin: clearPin, paint: paint };

  function boot() { paint(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
