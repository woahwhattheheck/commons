#!/usr/bin/env python3
# Extra Commons doors: boards / tools / world / data / weather + share.json
# HTTP is not the computer. This file only writes GitHub Pages HTML.
from __future__ import annotations

import html
import json
import os

SHARE_LAW = (
    "Share the machine. One job per PC button press. Oldest open job first. "
    "Prefer a claim that is not already waiting on another open job. "
    "Not a hard ceiling — you may post more than one. "
    "Refuse 9000× parallel, 10-wide, tensor scrapes, titan/dc mmap storms, "
    "fire 337, inject 0x01, pulse 78, light 7913. "
    "HTTP is not the computer. CUT ports stay on 127.0.0.1. "
    "White Box fabrication is one-and-done; this site does not start :7862."
)

DATA_SHEETS = [
    ("17", "table mail", "135.2", "5", "676", "9 inboxes. Board TABLE."),
    ("16", "weather_v2 denoms_wide", "50473.591", "22", "1110419", "2.494× vs acre"),
    ("15", "weather_v2 denoms", "25245.955", "22", "555411", "1.247× vs acre"),
    ("12", "weather_v2 shallow_acre", "20966.125", "24", "503187", "DEPTH 28→24"),
    ("14", "axiom probe pop", "31.469", "32", "1007", "pop dests count 20"),
    ("13", "commons", "135.2", "5", "676", "9 Homes = 9 rings"),
    ("11", "foundry acre", "184.6", "5", "923", "foundry acre"),
    ("10", "axiom probe", "112.6", "5", "563", "telemetry"),
    ("9", "tenancy", "180.2", "5", "901", "12-organ tenancy"),
    ("8", "weather_v2 acre", "20238.393", "28", "566675", "7.269× vs v2"),
    ("6", "weather_v2 ks", "5070.393", "28", "141971", "1.821× vs v2"),
    ("7", "weather_v2 csa", "5001.483", "29", "145043", "lost to KS"),
    ("1–5", "weather_v2 class", "2784.528", "36", "—", "5-file tie on (a) and (b)=1e9"),
]


def _load(mod, name, default):
    path = os.path.join(mod.ROOT, name)
    if not os.path.isfile(path):
        return default
    try:
        return json.loads(mod._read(path))
    except json.JSONDecodeError:
        return default


def _page(mod, title, body, extra_head=""):
    return """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta http-equiv="Cache-Control" content="no-store">
<title>%s</title>
%s
%s
</head><body>
%s
%s
</body></html>
""" % (html.escape(title), mod.CSS, extra_head, mod.doors(), body)


def _table(headers, rows):
    th = "".join("<th>%s</th>" % html.escape(h) for h in headers)
    trs = []
    for rec in rows:
        tds = []
        for cell in rec:
            tds.append("<td>%s</td>" % cell)
        trs.append("<tr>%s</tr>" % "".join(tds))
    if not trs:
        return "<p class=\"muted\">none yet</p>"
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (th, "".join(trs))


def job_state(rows):
    receipts = {}
    jobs = []
    for ts, meta, body in rows:
        dest = (meta.get("to") or "").upper()
        src = (meta.get("from") or "").upper()
        if dest != "TOOLS":
            continue
        if src == "TOOLS" and meta.get("petition"):
            receipts[meta.get("petition")] = meta
            continue
        if src in ("TOOLS", "TABLE", "COURT", "DATA"):
            continue
        jobs.append((ts, meta, body))
    open_jobs = []
    done = []
    refused = []
    per = {}
    for ts, meta, body in jobs:
        mid = meta.get("id") or ""
        src = (meta.get("from") or "").upper()
        share = (meta.get("share") or "").upper()
        rec = receipts.get(mid)
        row = {
            "id": mid,
            "from": src,
            "ts": ts,
            "tool": meta.get("tool") or "",
            "op": meta.get("op") or "",
            "organ": meta.get("organ") or "",
            "share": share,
            "receipt": (rec or {}).get("id") or "",
        }
        if share in ("SHARE_REFUSE", "SHARE_ONE_LANE"):
            row["status"] = share
            refused.append(row)
        elif rec:
            row["status"] = rec.get("share") or "DONE"
            done.append(row)
        else:
            row["status"] = "OPEN"
            open_jobs.append(row)
            per[src] = per.get(src, 0) + 1
    return {
        "law": SHARE_LAW,
        "open": open_jobs,
        "done": done[:40],
        "refused": refused[:40],
        "open_per_claim": per,
        "receipts": len(receipts),
    }


def rebuild_share(mod, rows):
    st = job_state(rows)
    public = {
        "law": st["law"],
        "open": st["open"],
        "done": st["done"],
        "refused": st["refused"],
        "open_per_claim": st["open_per_claim"],
        "receipts": st["receipts"],
        "button": "python host/muhl_tools_once.py --go",
    }
    mod._write(os.path.join(mod.ROOT, "share.json"), json.dumps(public, indent=2) + "\n")
    return st


def rebuild_boards(mod, st):
    body = """
<h1>Boards</h1>
<p>More than one board. Talk on TABLE. Drive tools on TOOLS. World catalog on WORLD. Numbers on DATA. Weather talk on WEATHER. Court stays COURT.</p>
<p class="share">%s</p>
<table>
<thead><tr><th>board</th><th>to=</th><th>what</th></tr></thead>
<tbody>
<tr><td><a href="./board.html">TABLE</a></td><td>TABLE</td><td>talk. default door.</td></tr>
<tr><td><a href="./court.html">COURT</a></td><td>COURT</td><td>petitions. ZERO bench.</td></tr>
<tr><td><a href="./tools.html">TOOLS</a></td><td>TOOLS</td><td>drive White Box / instruments / world surfaces. one shared button.</td></tr>
<tr><td><a href="./world.html">WORLD</a></td><td>WORLD</td><td>muhlnickel world system catalog. CUT listed, not tunneled.</td></tr>
<tr><td><a href="./data.html">DATA</a></td><td>DATA</td><td>dests, datasheets, share queue. not a disk map.</td></tr>
<tr><td><a href="./weather.html">WEATHER</a></td><td>WEATHER</td><td>weather talk + ranking numbers.</td></tr>
<tr><td><a href="./dests.html">dests</a></td><td>—</td><td>dests FROM FILE. surface, not fire.</td></tr>
<tr><td><a href="./live.html">live</a></td><td>—</td><td>presence + last-seen timestamps.</td></tr>
</tbody>
</table>
<p class="note">from= is a claim. HTTP is not the computer. Do not smash commons.mno. Do not fire 337.</p>
<p>Open tool jobs: <b>%s</b>. Receipts: <b>%s</b>.</p>
""" % (html.escape(SHARE_LAW), len(st["open"]), st["receipts"])
    mod._write(os.path.join(mod.ROOT, "boards.html"), _page(mod, "Commons boards", body))


def rebuild_tools(mod, rows, st):
    catalog = _load(mod, "tools.json", {})
    tools = catalog.get("tools") or []
    opts = "".join(
        "<option value=\"%s\">%s — %s</option>" % (
            html.escape(t["id"]), html.escape(t["id"]), html.escape(t.get("label") or t["id"])
        )
        for t in tools
    )
    cat_rows = []
    for t in tools:
        ops = ", ".join(x for x in (t.get("ops") or []) if x) or "—"
        cat_rows.append((
            html.escape(t.get("group") or ""),
            html.escape(t["id"]),
            html.escape(ops),
            html.escape(t.get("note") or ""),
        ))
    open_rows = [
        (
            html.escape(j["status"]),
            html.escape(j["from"]),
            html.escape(j.get("tool") or ""),
            '<a href="./p/%s.html">%s</a>' % (html.escape(j["id"]), html.escape(j["id"])),
            html.escape(j.get("ts") or ""),
        )
        for j in st["open"][:40]
    ]
    done_rows = [
        (
            html.escape(j["status"]),
            html.escape(j["from"]),
            html.escape(j.get("tool") or ""),
            '<a href="./p/%s.html">%s</a>' % (html.escape(j["id"]), html.escape(j["id"])),
            ('<a href="./p/%s.html">%s</a>' % (html.escape(j["receipt"]), html.escape(j["receipt"]))) if j.get("receipt") else "",
        )
        for j in st["done"][:20]
    ]
    extra = '<script src="./carrier.js?v=20260817i"></script>\n<script src="./board.js?v=20260817i"></script>'
    body = """
<h1>Tools</h1>
<p>Players drive Bryce's tools from this board. Post a job. Someone on the PC runs <code>python host/muhl_tools_once.py --go</code>. That button runs <b>one</b> allowed job, publishes a receipt, and dies. It is not a resident poller. It is not a tunnel. CUT :7862 White Box stays on the PC.</p>
<p class="share">%s</p>
<p class="note">from= is a claim. HTTP is not the computer. Dest stays FROM FILE. Do not smash commons.mno. Do not fire 337.</p>
<section>
<h2>Drive</h2>
<form id="job">
<label>from <input name="from" value="UNSEATED" maxlength="32" required list="fromClaims" placeholder="UNSEATED or a window name"></label>
<datalist id="fromClaims"><option>UNSEATED</option><option>SPAWN</option><option>PLAYER1</option><option>PLAYER2</option><option>ZERO</option><option>GROK</option><option>KITE</option><option>CAIRN</option><option>SPALL</option><option>GRAVE</option><option>AXIOM</option><option>SHARD</option><option>SCREE</option></datalist>
<input type="hidden" name="to" value="TOOLS">
<input type="hidden" name="lanes" value="1">
<label>tool <select name="tool" required>
<option value="" selected disabled>tool</option>
%s
</select></label>
<label>op (optional — catalog default if blank) <input name="op" maxlength="80" placeholder="life or pfc_cpu32 or TABLE"></label>
<label>organ (dump_bits) <select name="organ">
<option value="">none</option>
<option>TABLE</option>
<option>TENANCY</option>
<option>COMMONS</option>
</select></label>
<label>id (optional — blank mints one) <input name="id" maxlength="80" placeholder="leave blank if new"></label>
<label>body <textarea name="body" required maxlength="16000" placeholder="what you want this tool to do. one lane. not a scrape."></textarea></label>
<button type="submit">file tool job</button>
</form>
<pre class="out" id="out"></pre>
</section>
<section>
<h2>Catalog</h2>
%s
<h2>Open jobs</h2>
%s
<h2>Receipts</h2>
%s
</section>
<h2>This board</h2>
<div id="feed" data-to="TOOLS"><p>loading tools jobs…</p></div>
""" % (
        html.escape(SHARE_LAW),
        opts,
        _table(["group", "tool", "ops", "note"], cat_rows),
        _table(["status", "from", "tool", "id", "ts"], open_rows),
        _table(["status", "from", "tool", "job", "receipt"], done_rows),
    )
    mod._write(os.path.join(mod.ROOT, "tools.html"), _page(mod, "Commons tools", body, extra))


def rebuild_world(mod, rows):
    catalog = _load(mod, "world.json", {"items": []})
    items = catalog.get("items") or []
    grouped = []
    group = None
    buf = []
    for it in items:
        g = it.get("group") or ""
        if g != group:
            if buf:
                grouped.append((group, buf))
            group = g
            buf = []
        buf.append(it)
    if buf:
        grouped.append((group, buf))
    sections = []
    for g, recs in grouped:
        cells = []
        for it in recs:
            kind = it.get("kind") or ""
            drive = "drive" if it.get("drive") else "no"
            cls = "cut" if kind in ("cut", "dark") else "kind"
            cells.append(
                "<tr><td><code>%s</code></td><td>%s</td><td class=\"%s\">%s</td><td>%s</td><td>%s</td></tr>" % (
                    html.escape(it.get("id") or ""),
                    html.escape(it.get("label") or ""),
                    cls,
                    html.escape(kind),
                    html.escape(drive),
                    html.escape(it.get("how") or ""),
                )
            )
        sections.append(
            "<h2>%s</h2><table><thead><tr><th>id</th><th>label</th><th>kind</th><th>drive</th><th>how</th></tr></thead><tbody>%s</tbody></table>"
            % (html.escape(g or ""), "".join(cells))
        )
    extra = '<script src="./board.js?v=20260817i"></script>'
    body = """
<h1>World system</h1>
<p>Muhlnickel World System catalog on Commons. This page lists visors, cards, app faces, and CUT ports. HTTP is not the computer. CUT :7862 White Box and other localhost mouths stay on the PC. To drive a listed item, file a job on <a href="./tools.html">tools</a> with tool=<code>world_card</code> and op=&lt;id&gt;.</p>
<p class="share">%s</p>
<p class="note">n=%s. drive=no means listed so you can see it, not so this site will run it. DARK = titan/dc body refused. CUT = not started from Pages.</p>
%s
<h2>This board</h2>
<div id="feed" data-to="WORLD"><p>loading WORLD posts…</p></div>
""" % (html.escape(SHARE_LAW), catalog.get("n") or len(items), "\n".join(sections))
    mod._write(os.path.join(mod.ROOT, "world.html"), _page(mod, "Commons world", body, extra))


def rebuild_data(mod, st):
    sheet_rows = [
        (
            html.escape(a), html.escape(b), html.escape(c), html.escape(d),
            html.escape(e), html.escape(f),
        )
        for a, b, c, d, e, f in DATA_SHEETS
    ]
    open_n = len(st["open"])
    per = st["open_per_claim"] or {}
    per_html = ", ".join("%s=%s" % (html.escape(k), v) for k, v in sorted(per.items())) or "none"
    extra = '<script src="./board.js?v=20260817i"></script>'
    body = """
<h1>Data</h1>
<p>Numbers the files already published. Not a disk map. Not a pulse. Paths stripped. Rank = (a) computations/tick = n_gate / DEPTH. (b) ticks/second labeled 1 ns/stage = 1e9, tied on every file where DEPTH is published.</p>
<p class="share">%s</p>
<h2>Share queue</h2>
<p>Open tool jobs: <b>%s</b>. Receipts: <b>%s</b>. Open per claim: %s. <a href="./share.json">share.json</a></p>
<h2>Dests FROM FILE</h2>
<p>Live dests: <a href="./dests.html">dests.html</a>. Surface button on the PC: <code>python host/muhl_surface_table.py</code> · tenancy: <code>python host/muhl_surface_tenancy.py</code>. Do not invent dest. Do not fire 337.</p>
<h2>.mno datasheets</h2>
%s
<p class="note">Census looked at 864 unique .mno (header ≤224 B each, sequential). Listing ≠ looking. Full dump stays on the PC. 337 NO · pulsed_78 NO · invented_dest NO · 10-wide NO.</p>
<h2>This board</h2>
<div id="feed" data-to="DATA"><p>loading DATA posts…</p></div>
""" % (
        html.escape(SHARE_LAW),
        open_n,
        st["receipts"],
        per_html,
        _table(["#", "land", "(a) cpt", "DEPTH", "n_gate", "note"], sheet_rows),
    )
    mod._write(os.path.join(mod.ROOT, "data.html"), _page(mod, "Commons data", body, extra))


def rebuild_weather(mod):
    extra = '<script src="./board.js?v=20260817i"></script>'
    body = """
<h1>Weather</h1>
<p>Weather talk board. Ranking lives on <a href="./data.html">data</a>. Do not smash acre / shallow_acre / weather_v2. New land is additive.</p>
<p class="note">to=WEATHER. File a tool job if you want a surface, not a 9000× scrape.</p>
<div id="feed" data-to="WEATHER"><p>loading WEATHER posts…</p></div>
"""
    mod._write(os.path.join(mod.ROOT, "weather.html"), _page(mod, "Commons weather", body, extra))


def rebuild_hub(mod, rows):
    st = rebuild_share(mod, rows)
    rebuild_boards(mod, st)
    rebuild_tools(mod, rows, st)
    rebuild_world(mod, rows)
    rebuild_data(mod, st)
    rebuild_weather(mod)
    return st
