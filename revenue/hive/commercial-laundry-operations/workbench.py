"""Local browser interface for the existing laundry desk. No external services.

Run: python workbench.py /path/to/shift.sqlite3 --port 8899
Initialize a new database explicitly with operate.py before starting this app.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from cli import _export_stem
from laundry_desk import (
    IdempotencyConflict, InvoiceBlocked, LaundryDesk, LaundryDeskError,
    StateConflict, ValidationError,
)
from operate import (
    COMMANDS, MAX_INPUT_BYTES, MAX_INPUT_DEPTH, MAX_INPUT_NODES,
    _regular_database, _reject_number, _unique_object, authority, validate_input,
)

TITLES = {
    "customer": "Add customer", "site": "Add site", "agreement": "Set dated item price",
    "plan": "Add recurring route stop", "manifest": "Create daily route",
    "pickup": "Record pickup", "process": "Record plant counts", "deliver": "Record delivery",
    "resolve": "Resolve an exception", "invoice-draft": "Prepare invoice DRAFT",
}
HELP = {
    "operation_key": "Keep this key for retries. Use a new key for a different operation.",
    "linen_counts": "Observed pickup counts: sheet=100, towel=60. Never inferred from a plan.",
    "processed_counts": "Observed good counts after processing: sheet=100, towel=60.",
    "damaged_counts": "Observed damaged counts, for example sheet=1. Blank means none recorded.",
    "delivered_counts": "Observed delivery counts: sheet=100, towel=60.",
    "container_ids": "Actual container IDs, separated by commas or new lines.",
    "unit_price_cents": "Whole USD cents per item; 95 means $0.95. No decimal dollars.",
    "weekday": "Monday = 0, Tuesday = 1, through Sunday = 6.",
    "stop_sequence": "Operator-selected route order; no navigation is performed.",
    "active_from": "First effective date, inclusive.", "active_to": "Last effective date, inclusive; blank stays open-ended.",
    "note": "Record the supported disposition. Resolution does not change observed counts.",
}


def catalog() -> list[dict[str, Any]]:
    result = []
    for command, (_, required, optional) in COMMANDS.items():
        fields = []
        for name, kind in {"operation_key": str, **required, **optional}.items():
            fields.append({"name": name, "kind": kind.__name__,
                           "required": name not in optional, "help": HELP.get(name, "")})
        result.append({"command": command, "title": TITLES[command], "fields": fields})
    return result


def decode_operation(raw: bytes) -> tuple[str, dict[str, Any]]:
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_float=_reject_number, parse_constant=_reject_number)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValidationError("request must be bounded UTF-8 JSON with integer numbers") from exc
    if type(value) is not dict or set(value) != {"command", "payload"}:
        raise ValidationError("request requires exactly command and payload")
    command, payload = value["command"], value["payload"]
    if type(command) is not str or command not in COMMANDS or type(payload) is not dict:
        raise ValidationError("unsupported command or malformed payload")
    # Apply the operator input bounds before passing data to the same engine.
    stack, nodes = [(payload, 0)], 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > MAX_INPUT_NODES or depth > MAX_INPUT_DEPTH:
            raise ValidationError("input exceeds structural bounds")
        if type(item) is str:
            try:
                item.encode("utf-8")
            except UnicodeError as exc:
                raise ValidationError("invalid Unicode text") from exc
        elif type(item) is dict:
            for key in item:
                try:
                    key.encode("utf-8")
                except UnicodeError as exc:
                    raise ValidationError("invalid Unicode key") from exc
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
    validate_input(command, payload)
    return command, payload


def overview(database: Path) -> dict[str, Any]:
    desk = LaundryDesk.open_read_only(database)
    with closing(desk._connect()) as conn:
        # One read transaction keeps counters and selectors mutually consistent.
        conn.execute("BEGIN")
        routes = [dict(row) for row in conn.execute(
            "SELECT route_id,service_date,route_code,state FROM routes "
            "ORDER BY service_date DESC,route_code LIMIT 200")]
        customers = [dict(row) for row in conn.execute(
            "SELECT customer_id,name FROM customers ORDER BY customer_id LIMIT 200")]
        sites = [dict(row) for row in conn.execute(
            "SELECT site_id,customer_id,name FROM sites ORDER BY site_id LIMIT 200")]
        counts = {name: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                  for name, table in (("routes", "routes"), ("customers", "customers"),
                                      ("sites", "sites"), ("drafts", "invoices"))}
        counts["open_exceptions"] = conn.execute(
            "SELECT COUNT(*) FROM exceptions WHERE status='OPEN'").fetchone()[0]
        conn.commit()
    return {"routes": routes, "customers": customers, "sites": sites, "counts": counts,
            "selector_limit": 200, "authority": authority()}


def handler_for(database: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "LaundryWorkbench/1.0"

        def _send(self, status: int, content: str | bytes, content_type: str,
                  filename: str | None = None) -> None:
            body = content.encode("utf-8") if isinstance(content, str) else content
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; "
                             "base-uri 'none'; frame-ancestors 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, value: Any) -> None:
            self._send(status, json.dumps(value, ensure_ascii=True), "application/json; charset=utf-8")

        def _local_request(self) -> None:
            # Loopback binding plus browser-origin checks prevent another website
            # from submitting operations. No accounts, tokens, roles, or CORS.
            port = self.server.server_address[1]
            hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if self.headers.get("Host") not in hosts:
                raise ValidationError("open the workbench through its displayed loopback URL")
            origin = self.headers.get("Origin")
            if origin is not None and origin not in {f"http://{host}" for host in hosts}:
                raise ValidationError("cross-origin browser requests are not supported")

        def _dispatch(self, write: bool) -> None:
            try:
                self.connection.settimeout(8)
                self._local_request()
                url = urlsplit(self.path)
                query = parse_qs(url.query, keep_blank_values=True, max_num_fields=10)
                if write:
                    if url.path != "/api/operation" or url.query:
                        self._json(404, {"error": "unknown operation endpoint"})
                        return
                    if self.headers.get_content_type() != "application/json":
                        raise ValidationError("operations require application/json")
                    if self.headers.get("Transfer-Encoding") is not None:
                        raise ValidationError("chunked request bodies are not supported")
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= MAX_INPUT_BYTES:
                        raise ValidationError("request body must be between 1 byte and 1 MiB")
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValidationError("request body ended early")
                    command, payload = decode_operation(raw)
                    _regular_database(database)
                    LaundryDesk.open_read_only(database)
                    result = COMMANDS[command][0](LaundryDesk(database), **payload)
                    self._json(200, {"status": "REPLAYED" if result.replayed else "APPLIED",
                                    "operation": command, "operation_key": payload["operation_key"],
                                    "result": result.value, "authority": authority()})
                    return
                if url.path == "/":
                    self._send(200, PAGE, "text/html; charset=utf-8")
                elif url.path == "/api/catalog":
                    self._json(200, catalog())
                elif url.path == "/api/overview":
                    self._json(200, overview(database))
                elif url.path == "/api/integrity":
                    self._json(200, LaundryDesk.open_read_only(database).verify_integrity())
                elif url.path in {"/api/route", "/api/customer", "/api/export"}:
                    ids = query.get("id", [])
                    if len(ids) != 1 or not ids[0]:
                        raise ValidationError("exactly one object id is required")
                    desk = LaundryDesk.open_read_only(database)
                    object_id = ids[0]
                    if url.path == "/api/route":
                        self._json(200, desk.route_snapshot(object_id))
                    elif url.path == "/api/customer":
                        self._json(200, desk.customer_snapshot(object_id))
                    else:
                        scope, kind = query.get("scope", []), query.get("format", [])
                        if len(scope) != 1 or scope[0] not in {"route", "customer"} or len(kind) != 1:
                            raise ValidationError("export requires one scope and one format")
                        types = {"json": ("application/json", "json"), "csv": ("text/csv", "csv"),
                                 "markdown": ("text/markdown", "md")}
                        if kind[0] not in types:
                            raise ValidationError("unsupported export format")
                        exports = (desk.render_route_exports(object_id) if scope[0] == "route"
                                   else desk.render_customer_exports(object_id))
                        mime, extension = types[kind[0]]
                        self._send(200, exports[kind[0]], mime + "; charset=utf-8",
                                   _export_stem(scope[0], object_id) + "." + extension)
                else:
                    self._json(404, {"error": "not found"})
            except (IdempotencyConflict, InvoiceBlocked, StateConflict) as exc:
                self._json(409, {"error": str(exc), "error_type": type(exc).__name__})
            except (ValidationError, ValueError, UnicodeError) as exc:
                self._json(400, {"error": str(exc), "error_type": type(exc).__name__})
            except (LaundryDeskError, OSError, sqlite3.Error) as exc:
                self._json(503, {"error": str(exc), "error_type": type(exc).__name__})

        def do_GET(self) -> None:
            self._dispatch(False)

        def do_POST(self) -> None:
            self._dispatch(True)

        def log_message(self, format: str, *args: Any) -> None:
            # Do not log query strings or operation payloads/customer identifiers.
            print(f"workbench {self.command} {urlsplit(self.path).path}", file=sys.stderr)

    return Handler


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Laundry Operations Desk</title><style>
:root{color-scheme:light;--ink:#14283a;--muted:#526778;--line:#dce4ea;--accent:#075d78;--paper:#fff;--bg:#f2f5f7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
header{padding:24px max(24px,calc((100vw - 1440px)/2));background:var(--ink);color:white}h1{margin:0;font-size:25px}
header p{margin:5px 0 0;color:#c9d9e4}.wrap{max-width:1440px;margin:auto;padding:24px}.top{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}
.metric{background:white;border:1px solid var(--line);border-radius:10px;padding:12px 18px;min-width:145px}.metric b{font-size:24px;display:block}
.layout{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(320px,1fr);gap:24px}.panel,.stop{background:white;border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:18px}
h2{font-size:19px;margin:0 0 14px}h3{font-size:17px;margin:0}.muted,small{color:var(--muted)}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.between{justify-content:space-between}
label{display:block;font-weight:600;margin:12px 0 4px}input,select,textarea,button{font:inherit}input,select,textarea{width:100%;padding:9px 11px;border:1px solid #b8c8d3;border-radius:6px;background:white;color:var(--ink)}
textarea{min-height:76px;resize:vertical}select{max-width:100%}button,.download{border:1px solid var(--accent);background:var(--accent);color:white;padding:8px 12px;border-radius:6px;cursor:pointer;text-decoration:none}
button.secondary,.download{background:white;color:var(--accent)}button:disabled{opacity:.5;cursor:not-allowed}button:hover:not(:disabled),.download:hover{filter:brightness(.93)}
.actions{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}.badge{display:inline-block;font-size:12px;padding:3px 7px;border-radius:4px;background:#e6f0f5;word-break:break-word}.warning{background:#fff4dc;border-left:4px solid #ac6a00;padding:12px;margin:14px 0}
.error{background:#fff0ef;border-left:4px solid #b33127;padding:12px;white-space:pre-wrap}.success{background:#e9f5ed;border-left:4px solid #247846;padding:12px;white-space:pre-wrap}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f8;padding:12px;border-radius:6px;font-size:12px;max-height:360px;overflow:auto}
table{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}th,td{text-align:left;padding:7px 5px;border-bottom:1px solid var(--line)}.exception{padding:10px 0;border-top:1px solid var(--line)}
.empty{padding:20px 0;color:var(--muted)}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}footer{font-size:13px;color:var(--muted);margin-top:12px}.notice{margin-bottom:16px}
@media(max-width:850px){.layout{grid-template-columns:1fr}.wrap{padding:14px}.metric{min-width:120px;flex:1}header{padding:20px}}
</style></head><body>
<header><h1>Laundry Operations Desk</h1><p>Local route, linen and container records. Invoice drafts only. Nothing is sent or charged.</p></header>
<main class="wrap"><div id="notice" class="notice" role="status" aria-live="polite"></div><div id="metrics" class="top"></div>
<div class="layout"><section><div class="panel"><div class="row between"><h2>Daily route</h2><button id="refresh" class="secondary">Refresh</button></div>
<label for="route">Recent routes</label><select id="route"></select><small id="route-limit"></small>
<label for="route-id">Or open an exact route ID</label><div class="row"><input id="route-id" placeholder="route:2026-09-21:training" style="flex:1"><button id="open-route" class="secondary">Open</button></div>
<div id="route-info"></div><div id="route-downloads" class="actions"></div></div><div id="stops"></div>
<div class="panel"><h2>Customer handoff</h2><label for="customer">Recent customers</label><select id="customer"></select><small id="customer-limit"></small>
<label for="customer-id">Or open an exact customer ID</label><div class="row"><input id="customer-id" style="flex:1"><button id="open-customer" class="secondary">Open</button></div>
<div id="customer-downloads" class="actions"></div><details><summary>Customer and dated prices</summary><pre id="customer-detail">Select a customer.</pre></details></div></section>
<section><div class="panel"><h2>Record an operation</h2><p class="muted">Enter observed facts. The existing desk checks custody, counts, pricing and transitions.</p>
<label for="command">Operation</label><select id="command"></select><form id="operation-form"><div id="fields"></div>
<div class="actions"><button type="submit" id="submit">Record operation</button><button type="button" class="secondary" id="new-key">New operation key</button></div></form>
<p class="muted">A retry keeps its key. A different operation needs a new key. Uncertain network results must be retried unchanged.</p>
<div id="operation-result" role="status" aria-live="polite"></div><details><summary>Last operation response</summary><pre id="result-json">No operation recorded in this browser.</pre></details></div>
<div class="panel"><h2>Local record integrity</h2><button id="integrity" class="secondary">Inspect event consistency</button><pre id="integrity-result">Not inspected in this browser.</pre>
<footer>This is a local tool, not a hosted customer portal. Keep the database and its SQLite backups private. Drafts do not establish issued invoices, payment, cleaning quality or sanitation certification.</footer></div></section></div></main>
<script>
'use strict';
const $=id=>document.getElementById(id); let commands=[],state=null,currentRoute=null;
function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e}
function message(id,text,error=false){const e=$(id);e.className=error?'error':'success';e.textContent=text}
function clearNotice(){$('notice').className='notice';$('notice').textContent=''}
async function api(path,options={}){const r=await fetch(path,{cache:'no-store',...options});let value;try{value=await r.json()}catch{throw new Error('Unreadable response. Keep the current operation key before retrying.')}
 if(!r.ok)throw new Error((value.error_type?value.error_type+': ':'')+(value.error||'Request failed'));return value}
function params(values){return new URLSearchParams(values).toString()}
function downloads(id,scope,objectId){const parent=$(id);parent.replaceChildren();if(!objectId)return;
 for(const format of ['json','csv','markdown']){const a=node('a',format.toUpperCase(),'download');a.href='/api/export?'+params({scope,id:objectId,format});a.setAttribute('download','');parent.append(a)}}
function newKey(){return 'ui.'+crypto.randomUUID()}
function title(name){return name.replaceAll('_',' ')}
function choose(command,values={}){$('command').value=command;renderFields(values);$('command').scrollIntoView({block:'nearest',behavior:'smooth'})}
function renderFields(values={}){const definition=commands.find(c=>c.command===$('command').value);const root=$('fields');root.replaceChildren();
 for(const field of definition.fields){const label=node('label',title(field.name)+(field.required?'':' (optional)'));label.htmlFor='field-'+field.name;root.append(label);
 const input=node(field.kind==='dict'||field.kind==='list'?'textarea':'input');input.id='field-'+field.name;input.name=field.name;input.required=field.required;
 if(input.tagName==='INPUT'){input.type=field.kind==='int'?'number':field.name.includes('active_')||field.name==='service_date'?'date':'text';if(field.kind==='int'){input.step='1';input.min='0';if(field.name==='weekday')input.max='6'}}
 input.value=values[field.name]??(field.name==='operation_key'?newKey():'');root.append(input);
 if(field.help){const help=node('small',field.help);help.id='help-'+field.name;input.setAttribute('aria-describedby',help.id);root.append(help)}}
 $('operation-result').className='';$('operation-result').textContent=''}
function payload(){const definition=commands.find(c=>c.command===$('command').value),out={};
 for(const f of definition.fields){const value=$('field-'+f.name).value.trim();if(!value&&!f.required)continue;
 if(f.kind==='int'){if(!/^\d+$/.test(value)||!Number.isSafeInteger(Number(value)))throw new Error(f.name+' must be a whole safe integer');out[f.name]=Number(value)}
 else if(f.kind==='list')out[f.name]=value.split(/[,\n]/).map(s=>s.trim()).filter(Boolean);
 else if(f.kind==='dict'){const counts=Object.create(null);for(const entry of value.split(/[,\n]/).map(s=>s.trim()).filter(Boolean)){const pair=entry.split('=');
 if(pair.length!==2||!pair[0].trim()||!/^\d+$/.test(pair[1].trim())||!Number.isSafeInteger(Number(pair[1])))throw new Error(f.name+' must use item=whole_count entries');
 const key=pair[0].trim();if(Object.hasOwn(counts,key))throw new Error('Duplicate item: '+key);counts[key]=Number(pair[1])}out[f.name]=counts}
 else out[f.name]=value}return out}
function selectItems(id,items,key,label,selected){const select=$(id);select.replaceChildren();if(!items.length){select.append(new Option('No records yet',''));return}
 for(const item of items)select.append(new Option(label(item),item[key]));if(items.some(i=>i[key]===selected))select.value=selected}
async function loadOverview(preferredRoute){state=await api('/api/overview');const metrics=$('metrics');metrics.replaceChildren();
 for(const [key,label] of [['routes','Routes'],['customers','Customers'],['open_exceptions','Open exceptions'],['drafts','Invoice DRAFTS']]){const box=node('div',undefined,'metric');box.append(node('b',String(state.counts[key])),node('span',label));metrics.append(box)}
 const selected=preferredRoute||currentRoute||$('route').value;
 selectItems('route',state.routes,'route_id',r=>r.service_date+' · '+r.route_code+' · '+r.state,selected);
 $('route-limit').textContent=`Showing ${state.routes.length} of ${state.counts.routes} routes. Use an exact ID for older records.`;
 selectItems('customer',state.customers,'customer_id',c=>c.name+' · '+c.customer_id,$('customer').value);
 $('customer-limit').textContent=`Showing ${state.customers.length} of ${state.counts.customers} customers. Exact IDs also work.`;
 await Promise.all([loadRoute(selected&& !state.routes.some(r=>r.route_id===selected)?selected:$('route').value),loadCustomer($('customer').value)])}
function money(cents){return (cents/100).toLocaleString('en-US',{style:'currency',currency:'USD'})}
async function loadRoute(id){$('stops').replaceChildren();$('route-info').replaceChildren();downloads('route-downloads','route',null);if(!id){currentRoute=null;$('stops').append(node('p','Create a customer, site, dated price, recurring plan, then a daily route.','empty'));return}
 const route=await api('/api/route?'+params({id}));currentRoute=id;$('route-id').value=id;$('route-info').append(node('p',route.route_id,'muted'),node('span',route.state,'badge'));downloads('route-downloads','route',id);
 for(const stop of route.stops){const card=node('article',undefined,'stop'),heading=node('div',undefined,'row between');heading.append(node('h3',stop.sequence+' · '+stop.site_name),node('span',stop.state,'badge'));card.append(heading,node('p',stop.customer_name+' · '+stop.stop_id,'muted'));
 const table=node('table'),thead=node('thead'),tr=node('tr');for(const text of ['Item','Picked up','Good','Damaged','Delivered'])tr.append(node('th',text));thead.append(tr);table.append(thead);const body=node('tbody');
 const items=new Set([...Object.keys(stop.pickup_counts),...Object.keys(stop.processed_counts),...Object.keys(stop.delivered_counts),...Object.keys(stop.damaged_counts)]);
 for(const item of [...items].sort()){const row=node('tr');row.append(node('td',item));for(const key of ['pickup_counts','processed_counts','damaged_counts','delivered_counts'])row.append(node('td',stop[key][item]===undefined?'—':String(stop[key][item])));body.append(row)}table.append(body);card.append(table);
 card.append(node('p','Containers: pickup '+(stop.pickup_containers.join(', ')||'not recorded')+'; delivery '+(stop.delivery_containers.join(', ')||'not recorded'),'muted'));
 for(const exception of stop.exceptions){const block=node('div',undefined,'exception');block.append(node('strong',exception.kind+' · '+exception.status),node('p',exception.item_code+': expected '+exception.expected_qty+', recorded '+exception.actual_qty));
 if(exception.status==='OPEN'){const button=node('button','Record resolution','secondary');button.onclick=()=>choose('resolve',{exception_id:exception.exception_id});block.append(button)}else block.append(node('small',(exception.resolution_code||'')+' — '+(exception.resolution_note||'')));card.append(block)}
 if(stop.invoice)card.append(node('p','Invoice DRAFT '+money(stop.invoice.total_cents)+' — not sent or paid','success'));
 const next={MANIFESTED:'pickup',PICKED_UP:'process',PROCESSED:'deliver',DELIVERED:'invoice-draft'}[stop.state];
 if(next){const actions=node('div',undefined,'actions'),button=node('button',TITLES_UI[next]);button.onclick=()=>choose(next,{stop_id:stop.stop_id});if(next==='invoice-draft'&&stop.exceptions.some(e=>e.status==='OPEN')){button.disabled=true;card.append(node('p','Resolve open exceptions before drafting.','warning'))}actions.append(button);card.append(actions)}$('stops').append(card)}}
const TITLES_UI={pickup:'Record pickup',process:'Record plant counts',deliver:'Record delivery','invoice-draft':'Prepare invoice DRAFT'};
async function loadCustomer(id){downloads('customer-downloads','customer',null);if(!id){$('customer-detail').textContent='No customer selected.';return}
 const data=await api('/api/customer?'+params({id}));$('customer-id').value=id;$('customer-detail').textContent=JSON.stringify(data,null,2);downloads('customer-downloads','customer',id)}
function action(fn){return async()=>{clearNotice();try{await fn()}catch(e){message('notice',e.message,true)}}}
$('command').onchange=()=>renderFields();$('new-key').onclick=()=>{$('field-operation_key').value=newKey()};
$('refresh').onclick=action(()=>loadOverview());$('route').onchange=action(()=>loadRoute($('route').value));$('customer').onchange=action(()=>loadCustomer($('customer').value));
$('open-route').onclick=action(()=>loadRoute($('route-id').value.trim()));$('open-customer').onclick=action(()=>loadCustomer($('customer-id').value.trim()));
$('integrity').onclick=action(async()=>{$('integrity-result').textContent=JSON.stringify(await api('/api/integrity'),null,2)});
$('operation-form').onsubmit=async event=>{event.preventDefault();$('submit').disabled=true;clearNotice();
 try{const command=$('command').value;const result=await api('/api/operation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command,payload:payload()})});
 $('result-json').textContent=JSON.stringify(result,null,2);message('operation-result',result.status+' · '+result.operation_key+'\nThe key is retained for exact retries.');
 try{await loadOverview(command==='manifest'?result.result.route_id:undefined)}catch(e){message('notice','Operation '+result.status+'; board refresh failed: '+e.message+' Refresh the board; do not create a new key to repeat the operation.',true)}}
 catch(e){message('operation-result',e.message+'\nKeep this key and payload when retrying an uncertain outcome.',true)}finally{$('submit').disabled=false}};
(async()=>{try{commands=await api('/api/catalog');for(const c of commands)$('command').append(new Option(c.title,c.command));renderFields();await loadOverview()}catch(e){message('notice',e.message,true)}})();
</script></body></html>'''


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local browser workbench for an existing laundry database")
    parser.add_argument("database", type=Path)
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        database = args.database.absolute()
        _regular_database(database)
        LaundryDesk.open_read_only(database)
        with ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(database)) as server:
            print(f"Laundry workbench: http://127.0.0.1:{args.port}/", flush=True)
            print("Local records only. Stop with Ctrl-C. No external services or payments.", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except (LaundryDeskError, OSError, sqlite3.Error) as exc:
        print(f"Cannot start workbench: {exc}. Initialize a new database with operate.py first.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
