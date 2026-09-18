#!/usr/bin/env python3
"""Open the board in a real browser and measure what a reader actually gets.

WHY THIS EXISTS. Every check this repo had -- record-guard, import-check, the
test battery -- reads FILES. None of them can see whether a page DRAWS. In one
evening, opening the pages in Chromium found four things that every byte count,
HEAD sha and n= on the board reported as healthy:

  * visual.html drew 49 bare names and no figures for its entire life. .px is a
    <span> with no display set, so an inline box ignored width/height and
    computed to 0x0, and a box-shadow sprite on a 0x0 box paints nothing.
  * 8bit.html placed dudes at (i%8, i%4). Four divides eight, so the two indices
    move together and the whole roster landed on EIGHT distinct spots, stacked
    five deep, instead of a 32-slot grid.
  * Thirteen pages scrolled sideways on a phone because `body:has(#say) p{
    overflow:visible}` (a correct fix for the composer) silently outranked
    `p.nav{overflow-x:auto}` (a correct fix for the nav) on specificity.
  * board.html took 12.5 seconds to open on a throttled phone: 6.9 MB and
    28,804 nodes.

None of those are visible in a diff. All four are obvious in a browser.

USAGE
    pip install playwright            # chromium is usually already present
    python3 render_check.py           # checks every root *.html
    python3 render_check.py board.html visual.html
    python3 render_check.py --width 1280
    python3 render_check.py --perf    # also time the heaviest pages
    python3 render_check.py 8bit.html 8walk.html pixel.html visual.html --receipt receipts/render

Exit 0 clean, 1 if any page has a finding. Serves the working tree over
127.0.0.1 so relative fetches behave like the real site; file:// would trip
CORS and report false failures (that mistake nearly cost a bogus bug report).

Nothing here is a style opinion. Every check is a thing that is measurably
broken for a reader.
"""
import argparse
import http.server
import json
import os
import socketserver
import sys
import threading
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
CHROME_CANDIDATES = (
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    "/opt/pw-browsers/chromium/chrome-linux/chrome",
)
# a Fold outer screen; the narrowest thing the owner actually reads on
PHONE = 412


def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    for root in ("/opt/pw-browsers",):
        for dirpath, _dirs, files in os.walk(root) if os.path.isdir(root) else []:
            if "chrome" in files:
                return os.path.join(dirpath, "chrome")
    return None


def serve(directory, port):
    # Single-thread TCPServer serializes CSS/JS/HTML. Chromium opens
    # several connections at once; the first large send plus a reset
    # left visual.html at Page.goto timeout 45000ms on every
    # render-check run (32812516738 / 32812503966 / 32812350086).
    # ThreadingMixIn serves those assets in parallel. BrokenPipe is
    # Chromium closing a connection, not a page bug.
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=directory, **kw)

        def log_message(self, *a):
            pass

        def handle(self):
            try:
                super().handle()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return

        def finish(self):
            try:
                super().finish()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return

        def copyfile(self, source, outputfile):
            try:
                super().copyfile(source, outputfile)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return

    class Server(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True   # else a back-to-back run hits TIME_WAIT
        daemon_threads = True

    # walk a few ports so two windows can check at once, and so the previous
    # run's socket lingering does not look like a broken tool
    last = None
    for p in range(port, port + 12):
        try:
            httpd = Server(("127.0.0.1", p), Handler)
            break
        except OSError as e:
            last = e
    else:
        raise last
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


PROBE = """() => {
  const de = document.documentElement;
  const out = {
    sideways: de.scrollWidth > de.clientWidth + 2,
    docWidth: de.scrollWidth,
    clientWidth: de.clientWidth,
    nodes: document.querySelectorAll('*').length,
    text: (document.body.innerText || '').trim().length,
    widest: null,
    zeroDrawn: 0,
  };
  // the element that actually pushes the page sideways, for a usable report
  if (out.sideways) {
    let worst = null;
    document.querySelectorAll('*').forEach(el => {
      const r = el.getBoundingClientRect();
      // ignore children inside their own horizontal scroller: they are contained
      let p = el.parentElement, contained = false;
      while (p) {
        const cs = getComputedStyle(p);
        if (cs.overflowX === 'auto' || cs.overflowX === 'scroll' || cs.overflowX === 'hidden') { contained = true; break; }
        p = p.parentElement;
      }
      if (!contained && r.right > de.clientWidth + 2 && (!worst || r.right > worst.right)) {
        worst = { tag: el.tagName, cls: (el.className || '').toString().slice(0, 24),
                  right: Math.round(r.right), width: Math.round(r.width),
                  text: (el.textContent || '').trim().slice(0, 40) };
      }
    });
    out.widest = worst;
  }
  // an element that paints ONLY via box-shadow but has no box paints nothing.
  // This is the visual.html sprite bug, generalised.
  document.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.boxShadow === 'none') return;
    // checkVisibility walks ANCESTORS. Without it, every child of a
    // display:none container counts as "draws nothing" -- visual.html hides
    // its whole plaza below 34rem by design, and a naive check reported 77
    // phantom bugs there. A hidden section is a choice; a visible element
    // with no box is the bug.
    if (el.checkVisibility && !el.checkVisibility({ checkVisibilityCSS: true })) return;
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) out.zeroDrawn++;
  });
  return out;
}"""


def write_receipt(path, pages, width, findings, chrome):
    os.makedirs(path, exist_ok=True)
    payload = {
        "tool": "render_check.py",
        "pages": list(pages),
        "width": width,
        "finding_count": len(findings),
        "findings": [{"page": name, "issues": issues} for name, issues in findings],
        "clean": not findings,
        "chrome": chrome or "playwright-bundled",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "titan": "NOT_WRITTEN",
    }
    with open(os.path.join(path, "receipt.json"), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return payload


def check(pages, width, perf, port, receipt=None):
    from playwright.sync_api import sync_playwright

    exe = find_chrome()
    base = "http://127.0.0.1:%d" % port
    findings = []
    if receipt:
        os.makedirs(receipt, exist_ok=True)
    with sync_playwright() as p:
        kw = {"args": ["--no-proxy-server"]}
        if exe:
            kw["executable_path"] = exe
        b = p.chromium.launch(**kw)
        ctx = b.new_context(viewport={"width": width, "height": 915})
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append("JS " + str(e)[:100]))
        # Keep the resource URL, not just the message. Chrome's text for a
        # missing favicon is a bare "Failed to load resource: ... 404" with no
        # hint of what failed -- only the message's LOCATION says favicon.ico.
        # Filtering on text alone reported that as a page bug (it isn't; no
        # page here ships a favicon).
        pg.on("console",
              lambda m: errors.append("console " + m.text[:100] + " <" +
                                      ((m.location or {}).get("url", "") or "")[-60:] + ">")
              if m.type == "error" else None)
        for f in pages:
            errors.clear()
            issues = []
            try:
                pg.goto("%s/%s" % (base, f), wait_until="load", timeout=45000)
                pg.wait_for_timeout(900)
                d = pg.evaluate(PROBE)
            except Exception as e:
                findings.append((f, ["did not load: %s" % str(e)[:80]]))
                continue
            if receipt:
                try:
                    shot = os.path.join(receipt, os.path.basename(f).replace(".html", ".png"))
                    pg.screenshot(path=shot, full_page=True)
                except Exception:
                    pass
            if d["sideways"]:
                w = d["widest"]
                issues.append("scrolls sideways (%dpx wide in %dpx)%s" % (
                    d["docWidth"], d["clientWidth"],
                    " - widest: <%s class=%r> %r" % (w["tag"], w["cls"], w["text"]) if w else ""))
            if d["zeroDrawn"]:
                issues.append("%d element(s) paint only via box-shadow but measure 0 "
                              "- they draw nothing" % d["zeroDrawn"])
            if d["text"] < 60:
                issues.append("renders almost no text (%d chars)" % d["text"])
            # Pages legitimately fetch ntfy and other outside hosts. In a
            # sandbox those come back as cert/tunnel failures, which say
            # something about THIS container and nothing about the page. I
            # shipped this filter after my own first run reported a transport
            # artifact as a bug on eleven pages.
            noise = ("favicon.ico", "favicon", "ERR_CERT", "ERR_TUNNEL", "ERR_PROXY",
                     "ERR_NAME_NOT_RESOLVED", "ERR_INTERNET_DISCONNECTED",
                     "ERR_CONNECTION_REFUSED", "CORS")
            real = [e for e in errors if not any(n in e for n in noise)]
            if real:
                issues.append("script error: %s" % real[0][:90])
            if issues:
                findings.append((f, issues))
            if perf and d["nodes"] > 5000:
                t = pg.evaluate("()=>{const n=performance.getEntriesByType('navigation')[0];"
                                "return Math.round(n.loadEventEnd)}")
                print("  perf  %-20s %6dms  %6d nodes" % (f, t, d["nodes"]))
        b.close()
    return findings, exe


def main():
    ap = argparse.ArgumentParser(description="render the board and report what a reader gets")
    ap.add_argument("pages", nargs="*", help="pages to check (default: every root *.html)")
    ap.add_argument("--width", type=int, default=PHONE, help="viewport width (default %d)" % PHONE)
    ap.add_argument("--perf", action="store_true", help="also time heavy pages")
    ap.add_argument("--port", type=int, default=8973)
    ap.add_argument("--receipt", help="write receipt.json plus page screenshots here")
    a = ap.parse_args()

    pages = a.pages or sorted(f for f in os.listdir(HERE) if f.endswith(".html"))
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("render_check needs playwright:  pip install playwright")
        return 2

    httpd, port = serve(HERE, a.port)
    try:
        findings, chrome = check(pages, a.width, a.perf, port, a.receipt)
    finally:
        httpd.shutdown()
        httpd.server_close()

    if a.receipt:
        write_receipt(a.receipt, pages, a.width, findings, chrome)
        print("receipt %s/receipt.json" % a.receipt)

    print("rendered %d page(s) at %dpx" % (len(pages), a.width))
    if not findings:
        print("clean: nothing measurably broken for a reader")
        return 0
    print("%d page(s) with findings:" % len(findings))
    for f, issues in findings:
        print("  %s" % f)
        for i in issues:
            print("      %s" % i)
    return 1


if __name__ == "__main__":
    sys.exit(main())
