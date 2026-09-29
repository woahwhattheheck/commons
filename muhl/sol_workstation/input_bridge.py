"""Local in-place variable-input bridge for an explicitly selected artifact.

The host supplies bytes to file-published inputs, journals them, and surfaces
readback. This does not evaluate records or run inference/training/feedback.
"""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlparse

import bench


PAGE = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Muhlnickel native input bench</title><style>
body{font:16px system-ui;background:#101c23;color:#dfebeb;max-width:1000px;margin:35px auto;padding:20px}h1{font-size:30px}p{line-height:1.6}small{color:#a3bbc4}input,select,button,textarea{font:inherit;background:#19313c;color:#eef8f4;border:1px solid #507382;padding:10px;border-radius:6px}select,textarea{width:100%;margin:8px 0}button{cursor:pointer;background:#28694f;margin:8px 8px 8px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#142a33;padding:16px}.scope{color:#a1e3c2}label{display:block;margin-top:18px}textarea{min-height:70px}</style>
<h1>Muhlnickel input bench</h1><p class="scope">Weightless one-file speaking Titan · separate from Kaggriculture Titan and the Kaggle/ARC agent.</p><p id="target">Connecting to the selected file…</p><small>In-place input writes. No whole-container browser buffer or temporary copy. No host gate evaluation or model execution.</small>
<label>Published input window<select id="window"></select></label><pre id="current"></pre>
<label>Input bytes as hexadecimal<textarea id="hex" spellcheck="false">01</textarea></label><label>Input operation<select id="mode"><option value="or">Apply charge bits (old OR supplied mask)</option><option value="replace">Replace variable data bytes exactly</option></select></label>
<button id="read">Read current bytes</button><button id="write" disabled>Write selected input</button><pre id="receipt">No write requested.</pre><p><small>The receipt reports supplied input and immediate readback. It does not claim a model result or native computation. Operation IDs are retained for replay.</small></p>
<script>
const el=id=>document.getElementById(id);let selectedStatus;async function api(url,opts){const r=await fetch(url,opts);const d=await r.json();if(!r.ok)throw Error(d.error||r.statusText);return d}
async function read(){const name=el('window').value;el('write').disabled=!name;if(!name)return;el('current').textContent=JSON.stringify(await api('/api/window?name='+encodeURIComponent(name)),null,2)}
async function load(){selectedStatus=await api('/api/status');el('target').textContent=selectedStatus.path+' · '+selectedStatus.bytes.toLocaleString()+' bytes · '+selectedStatus.profile;for(const w of selectedStatus.windows){const o=document.createElement('option');o.value=w.name;o.textContent=w.name+' — byte '+w.offset+' — '+w.length+' bytes';el('window').append(o)}const selected=new URLSearchParams(location.search).get('window');if(selected){if(!selectedStatus.windows.some(w=>w.name===selected)){el('window').selectedIndex=-1;throw Error('The requested input is not published on this selected file. Choose its intended input explicitly.')}el('window').value=selected}await read()}
el('read').onclick=()=>read().catch(e=>el('receipt').textContent=e.message);el('window').onchange=el('read').onclick;
el('write').onclick=async()=>{const operation_id=crypto.randomUUID();const payload={operation_id,window:el('window').value,mode:el('mode').value,hex:el('hex').value.replace(/\s+/g,'')};el('write').disabled=true;el('receipt').textContent='Operation '+operation_id+' submitted';try{el('receipt').textContent=JSON.stringify(await api('/api/input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}),null,2);await read()}catch(e){el('receipt').textContent='Operation '+operation_id+': '+e.message}finally{el('write').disabled=false}};
load().catch(e=>el('receipt').textContent=e.message);
</script></html>'''


class InputBench:
    def __init__(self, path, profile, journal, registry=None):
        self.path = path.resolve()
        self.profile = profile
        self.journal = journal.resolve()
        self.registry = registry.resolve() if registry else None
        self.lock = threading.Lock()
        self.operations = {}
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        if self.journal.exists():
            for line in self.journal.read_text(encoding='utf8').splitlines():
                record = json.loads(line)
                self.operations[record['operation_id']] = record

    def inputs(self):
        if self.profile == 'titan-registry':
            if not self.registry:
                raise ValueError('titan-registry profile requires --registry')
            entries = json.loads(self.registry.read_text(encoding='utf8'))
            found = {}
            size = self.path.stat().st_size
            for name, entry in entries.items():
                if not isinstance(entry, dict):
                    continue
                ram = entry.get('ram')
                ram = ram if isinstance(ram, dict) else {}
                for label, address in (('recv', ram.get('recv')),
                                       ('input', entry.get('input_addr'))):
                    if isinstance(address, int) and not isinstance(address, bool) and 0 <= address < size:
                        key = name+'.'+label
                        found[key] = bench.window(key, address, 1, 'input')
            return found
        spec = bench.layout(self.path, self.profile)
        return {w['name']: w for w in spec['windows'] if w['role'] == 'input'}

    def status(self):
        return dict(project='Muhlnickel one-file speaking Titan', path=str(self.path),
                    profile=self.profile, bytes=self.path.stat().st_size,
                    windows=list(self.inputs().values()), journal=str(self.journal),
                    runtime='Variable input and byte readback only')

    def read(self, name):
        w = self.inputs()[name]
        with self.path.open('rb', buffering=0) as stream:
            data = bench.read_at(stream, w['offset'], w['length'])
        return {**w, 'hex': data.hex()}

    def record(self, result):
        with self.journal.open('a', encoding='utf8') as stream:
            stream.write(json.dumps(result, separators=(',', ':'))+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.operations[result['operation_id']] = result

    def write(self, request):
        operation = request['operation_id']
        if not isinstance(operation, str) or not 1 <= len(operation) <= 160:
            raise ValueError('operation_id must be 1..160 characters')
        name, mode = request['window'], request['mode']
        if mode not in ('or', 'replace'):
            raise ValueError('mode is or or replace')
        incoming = bytes.fromhex(request['hex'])
        canonical = dict(window=name, mode=mode, hex=incoming.hex())
        with self.lock:
            if operation in self.operations:
                old = self.operations[operation]
                if old['request'] != canonical or old['path'] != str(self.path):
                    raise ValueError('operation_id already describes a different input')
                if old['phase'] != 'completed':
                    raise ValueError('Prior operation was interrupted; inspect its journal and current bytes before another operation')
                return {**old, 'replayed': True}
            w = self.inputs()[name]
            if not incoming or len(incoming) > w['length']:
                raise ValueError('Input length must fit the published window')
            with self.path.open('r+b', buffering=0) as stream:
                before = bench.read_at(stream, w['offset'], len(incoming))
                supplied = bytes(a | b for a, b in zip(before, incoming)) if mode == 'or' else incoming
                prepared = dict(operation_id=operation, request=canonical, path=str(self.path),
                                profile=self.profile, phase='prepared', at=datetime.now(timezone.utc).isoformat(),
                                offset=w['offset'], before_hex=before.hex(), supplied_hex=supplied.hex(),
                                bytes_before=self.path.stat().st_size)
                self.record(prepared)
                stream.seek(w['offset'])
                if stream.write(supplied) != len(supplied):
                    raise OSError('Short input write; journal retained for reconciliation')
                stream.flush()
                os.fsync(stream.fileno())
                observed = bench.read_at(stream, w['offset'], len(supplied))
            result = {**prepared, 'phase': 'completed', 'observed_hex': observed.hex(),
                      'bytes_after': self.path.stat().st_size, 'replayed': False,
                      'scope': 'Input write and immediate readback only; no native model result inferred'}
            self.record(result)
            return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--profile', default='titan-study-v4')
    parser.add_argument('--journal', type=Path, required=True)
    parser.add_argument('--registry', type=Path)
    parser.add_argument('--port', type=int, default=7882)
    args = parser.parse_args()
    instance = InputBench(args.file, args.profile, args.journal, args.registry)
    instance.inputs()  # Read the actual layout before accepting an input.

    class Handler(BaseHTTPRequestHandler):
        def answer(self, status, body, media='application/json'):
            data = body.encode('utf8') if isinstance(body, str) else json.dumps(body).encode('utf8')
            self.send_response(status)
            self.send_header('Content-Type', media+'; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            try:
                url = urlparse(self.path)
                if url.path == '/':
                    self.answer(200, PAGE, 'text/html')
                elif url.path == '/api/status':
                    self.answer(200, instance.status())
                elif url.path == '/api/window':
                    self.answer(200, instance.read(parse_qs(url.query)['name'][0]))
                else:
                    self.answer(404, {'error': 'Unknown resource'})
            except (ValueError, KeyError, OSError) as exc:
                self.answer(400, {'error': str(exc)})

        def do_POST(self):
            try:
                if self.path != '/api/input':
                    self.answer(404, {'error': 'Unknown resource'})
                    return
                if self.headers.get_content_type() != 'application/json':
                    raise ValueError('Expected application/json input')
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    raise ValueError('Input request must be 1..16384 bytes')
                request = json.loads(self.rfile.read(length))
                self.answer(200, instance.write(request))
            except (ValueError, KeyError, TypeError, OSError) as exc:
                self.answer(400, {'error': str(exc)})

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    current = instance.status()
    print(json.dumps({'url': f'http://127.0.0.1:{server.server_port}/',
                      'path': current['path'], 'bytes': current['bytes'],
                      'profile': current['profile'], 'input_windows': len(current['windows'])}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
