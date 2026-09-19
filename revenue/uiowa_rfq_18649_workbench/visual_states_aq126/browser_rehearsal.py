#!/usr/bin/env python3
"""Exercise the actual workbench and export its rendered synthetic state matrix.

Requires Playwright, PyMuPDF and a Chromium executable. No server, network request,
parent-compiler execution, or actual University data is used. Missing browser
support fails explicitly; this is not part of the stdlib Node-only battery.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New directory; existing output is never overwritten")
    parser.add_argument("--chromium", default=None, help="Browser executable; defaults to chromium on PATH")
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
        import fitz
    except ImportError:
        parser.error("Playwright and PyMuPDF are required for browser/PDF acceptance")
    browser_path = args.chromium or shutil.which("chromium") or shutil.which("google-chrome")
    if not browser_path:
        parser.error("Chromium executable unavailable; provide --chromium")
    here = Path(__file__).resolve().parent
    parent = here.parent
    sources = {name: (parent / name).read_text(encoding="utf-8") for name in ("index.html", "app.js", "style.css")}
    fixture = json.loads((here / "comparison.json").read_text(encoding="utf-8"))
    # Fail rather than quietly exercising different resources after integration.
    html = sources["index.html"]
    for old in ('  <link rel="stylesheet" href="/style.css">', '  <script src="/app.js" defer></script>'):
        if html.count(old) != 1:
            raise RuntimeError("workbench resource wiring changed; reconcile the rehearsal")
        html = html.replace(old, "")
    args.output.mkdir(parents=False, exist_ok=False)
    checks: list[str] = []
    def require(condition: bool, label: str) -> None:
        if not condition:
            raise RuntimeError(f"browser check failed: {label}")
        checks.append(label)
    errors: list[str] = []
    blocked_requests: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=browser_path, headless=True, args=["--no-sandbox"])
        version = browser.version
        context = browser.new_context(viewport={"width": 1280, "height": 960}, color_scheme="light", accept_downloads=True)
        context.route("**/*", lambda route: (blocked_requests.append(route.request.url), route.abort()))
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(html)
        page.add_style_tag(content=sources["style.css"])
        page.add_script_tag(content=sources["app.js"])
        page.evaluate("report => installReport(report)", fixture["report"])
        require(page.locator("#matrix > .cell").count() == 12, "twelve actual matrix cards")
        for label in ("Internally consistent", "Missing evidence", "Unknown", "Not assessed", "Not applicable", "Conflicting evidence", "Stale evidence", "Unrecognized status"):
            require(page.locator("#matrix").inner_text().find(label) >= 0, f"visible state: {label}")
        text = page.locator("#matrix").inner_text()
        for label in ("Supplied value: 0 (display only)", "Not supplied (field absent)", "Not determined (null)", "Not reported in untrusted inspection (null)", "Non-numeric or invalid value"):
            require(label in text, f"numeric distinction: {label}")
        require(page.evaluate("JSON.stringify(state.report)") == json.dumps(fixture["report"], ensure_ascii=False, separators=(",", ":")), "input report unchanged")
        page.locator('[data-key="IAM|security"]').click()
        require(page.locator('[data-key="IAM|security"]').get_attribute("data-evidence-state") == "conflict", "zero does not resolve conflict")
        page.locator('[data-key="ESS|security"]').click()
        detail = json.loads(page.locator("#detail").inner_text())
        require(detail["display_only"]["maturity_availability"] == "Not supplied (field absent)", "detail preserves absent field meaning")
        page.locator('[data-key="ESS|software"]').click()
        page.locator("#note").fill("FICTIONAL: retain the literal 0.\nSecond line.")
        page.locator("#disposition").select_option("NEEDS_EVIDENCE")
        with page.expect_download() as download:
            page.locator("#exportBtn").click()
        handoff_path = args.output / "actual-handoff.json"
        download.value.save_as(handoff_path)
        handoff = json.loads(handoff_path.read_text())
        require(handoff["cell_notes"][0]["analyst_note"] == "FICTIONAL: retain the literal 0.\nSecond line.", "actual download retains literal multiline note")
        require(handoff["cell_notes"][0]["disposition"] == "NEEDS_EVIDENCE", "actual download retains disposition")
        require([cell["compiler_status"] for cell in handoff["cell_notes"]] == [cell["status"] for cell in fixture["report"]["assessment_matrix"]], "actual download retains original status codes")
        require(handoff["synthetic_demo"] is True and len(handoff["authority"]) == 7 and all(v is False for v in handoff["authority"].values()), "actual download retains synthetic marker and all false authority")
        page.locator("#statusFilter").select_option("HOLD_CONFLICT")
        require(page.locator("#matrix > .cell").count() == 2, "raw status filtering still works")
        page.locator("#statusFilter").select_option("")
        require(page.locator("#matrix > .cell").count() == 12, "clearing filter restores twelve cells")
        for mode in ("light", "dark"):
            page.emulate_media(color_scheme=mode)
            require(page.locator(".state-label").count() == 12, f"labels retained in {mode} mode")
        page.emulate_media(color_scheme="light", forced_colors="active")
        require(page.locator("#matrix").inner_text() == text, "forced colors preserve every state and value")
        page.emulate_media(forced_colors="none")
        page.set_viewport_size({"width": 390, "height": 844})
        require(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "no horizontal page overflow at 390 px")
        require(page.locator("#matrix > .cell").evaluate_all("cards => cards.every(c => c.scrollWidth <= c.clientWidth)"), "no clipped card text at 390 px")
        page.set_viewport_size({"width": 1280, "height": 960})
        page.screenshot(path=str(args.output / "workbench-color.png"), full_page=True)
        # Capture the actual rendered DOM, not a separately implemented mock.
        matrix = page.locator("#matrix").evaluate("element => element.outerHTML")
        hashes = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in sources.items()}
        comparison = ('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>UIOWA-126 — fictional visual state comparison</title><style>' + sources["style.css"] +
            '\n@page { size:A4; margin:14mm; @bottom-left { content:"UI-ONLY FICTIONAL DISPLAY FIXTURE"; font-size:8pt; } @bottom-right { content:"UIOWA-126 | " counter(page) " / " counter(pages); font-size:8pt; } } .comparison-source {overflow-wrap:anywhere;font-size:.7rem;} </style>'
            '<header><p class="eyebrow">UIOWA-126 / ZZ-ASTRA-QUARTZ</p><h1>Different states, not different grades</h1>'
            '<p class="boundary">UI-ONLY FICTIONAL DISPLAY COMPARISON. Not compiler output, University findings, or verified maturity numbers. '
            'Extra statuses and numeric sentinels exercise presentation only. This static export contains the actual workbench-rendered matrix.</p>'
            '<p>Text labels and border patterns retain meaning without color. Zero is a supplied numeric value; it is not missing data. '
            'An absent field, explicit null, unassessed cell, inapplicable cell, stale source and conflict remain different. '
            'No score, success rate, or performance ranking is calculated.</p></header><main>' + matrix +
            '<p class="comparison-source">Executed app.js SHA-256: ' + hashes["app.js"] + '<br>Executed style.css SHA-256: ' + hashes["style.css"] + '</p></main></html>\n')
        (args.output / "comparison.html").write_text(comparison, encoding="utf-8")
        proof = context.new_page()
        proof.set_content(comparison)
        proof.screenshot(path=str(args.output / "comparison-color.png"), full_page=True)
        gray = proof.add_style_tag(content="html { filter: grayscale(1); }")
        proof.screenshot(path=str(args.output / "comparison-monochrome.png"), full_page=True)
        # CSS filters rasterize Chromium PDF text. Monochrome simulation is
        # screenshot-only; the actual print rules already use black on white.
        gray.evaluate("node => node.remove()")
        proof.emulate_media(media="print")
        proof.pdf(path=str(args.output / "comparison.pdf"), prefer_css_page_size=True, print_background=True)
        require(proof.locator(".state-label").count() == 12, "all twelve labels present for print")
        with fitz.open(args.output / "comparison.pdf") as pdf:
            require(all(page.get_text().strip() for page in pdf), "every PDF page retains searchable text")
            require(all("UI-ONLY FICTIONAL DISPLAY FIXTURE" in page.get_text() for page in pdf), "every PDF page retains fictional context")
            pdf_text = " ".join(" ".join(page.get_text().split()) for page in pdf)
            for label in ("Not assessed", "Not applicable", "Conflicting evidence", "Missing evidence", "Supplied value: 0", "Not supplied (field absent)", "Not determined (null)", "Not reported in untrusted inspection (null)", "FUTURE_SCHEMA_STATUS"):
                require(label in pdf_text, f"PDF text retained: {label}")
            for index, page in enumerate(pdf):
                page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3)).save(args.output / f"page-{index+1:02}.png")
        require(not blocked_requests, "no runtime network requests")
        require(not errors, "no browser JavaScript errors")
        browser.close()
    receipt = {"schema": "uiowa-126-local-browser-rehearsal/v1", "notice": fixture["notice"], "python": platform.python_version(), "chromium": version, "checks_passed": len(checks), "checks": checks, "executed_sha256": hashes, "not_claimed": ["parent compiler execution", "hosted CI", "University findings", "source authenticity", "merge authority", "PDF byte determinism"]}
    (args.output / "browser-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks_passed":len(checks), "chromium":version, "output":str(args.output)}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
