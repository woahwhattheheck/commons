"""Muhlnickel Titan workbench: bounded byte inspection and physical wiring.

Standard-library instruments. Source containers are opened read-only. No gate
evaluation, inference, training, model imports, or runtime token loop.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
GATE = struct.Struct('<BQQQ')
# This map is specific to AUTOFAB0 and the appended v4 organ, not universal.
AFB_OPS = {0: 'NAND', 1: 'AND', 2: 'OR', 3: 'XOR', 4: 'NOT'}


def now():
    return datetime.now(timezone.utc).isoformat()


def integer(value):
    return int(value, 0)


def emit(value, destination=None):
    text = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    if destination:
        target = Path(destination).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        # Every output is new: never overwrite a container or an earlier receipt.
        with target.open('x', encoding='utf-8') as stream:
            stream.write(text)
    else:
        print(text, end='')


def read_at(stream, offset, length):
    if offset < 0 or length < 0:
        raise ValueError('negative byte window')
    stream.seek(offset)
    data = stream.read(length)
    if len(data) != length:
        raise ValueError(f'short read at {offset}: requested {length}, got {len(data)}')
    return data


def digest_region(stream, offset, length):
    h = hashlib.sha256()
    stream.seek(offset)
    remaining = length
    while remaining:
        data = stream.read(min(65536, remaining))
        if not data:
            raise ValueError(f'short region at {offset}')
        h.update(data)
        remaining -= len(data)
    return h.hexdigest()


def load_project(args):
    config = Path(args.project).resolve()
    project = json.loads(config.read_text(encoding='utf-8'))
    roots = dict(desktop=str(Path.home() / 'Desktop'),
                 workstation=str(config.parent),
                 llm='C:/llm',
                 models='C:/llm/models',
                 research=str(config.parent.parent / 'research' / '2026-09-27-muhlnickel-study'))
    for item in args.root:
        key, value = item.split('=', 1)
        roots[key] = value
    return project, roots


def artifact(args):
    project, roots = load_project(args)
    entry = project['artifacts'][args.artifact]
    path = Path(args.file or entry['path'].format_map(roots)).resolve()
    return project, entry, path


def window(name, offset, length, role='state'):
    return dict(name=name, offset=offset, length=length, role=role)


def table(name, offset, count):
    return dict(name=name, offset=offset, count=count, length=count * GATE.size)


def layout(path, profile):
    size = path.stat().st_size
    tables, windows, symbols, ops = [], [], {}, {}
    details = {}
    with path.open('rb') as stream:
        if profile == 'titan-study-v4':
            header = read_at(stream, 0, 192)
            if header[:8] != b'MUHLPKG1':
                raise ValueError('expected the study artifact MUHLPKG1 prefix')
            prefix = struct.unpack_from('<Q', header, 184)[0]
            base = (prefix + 4095) & ~4095
            organ = read_at(stream, base, 16384)
            if organ[:8] != b'MUHLAFB1' or struct.unpack_from('<II', organ, 8) != (1, 25):
                raise ValueError('unrecognized appended organ geometry')
            afb, tbl, ring, aperture, end, tail, scratch, recv, bus, power, n, total = struct.unpack_from('<12Q', organ, 16)
            text_len = struct.unpack_from('<I', organ, 116)[0]
            if text_len > len(organ) - 120 or total != size:
                raise ValueError('organ length/registry disagrees with current file')
            registry = json.loads(organ[120:120 + text_len])
            tables = [table('autofab', tbl, 4117), table('ring', ring, 78),
                      table('aperture', aperture, 8), table('start_bridge', tail, 1)]
            fwd, rev = registry['ring_charge']
            windows = [window('start', recv, 1, 'input'), window('power', power, 1),
                       window('ring_forward', fwd, 32, 'input'), window('ring_reverse', rev, 32, 'input'),
                       window('ring_control', rev + 32, 8), window('autofab_score', afb + 159, 1)]
            reader = registry.get('reader')
            if reader:
                tables += [table('reader', reader['record_base'], reader['records']),
                           table('score_bridge', reader['correctness_bridge_record'], 1)]
                windows += [window('target0', reader['target_table'], 8, 'input'),
                            window('cursor', reader['cursor'], 8), window('hit0', reader['hit0'], 1)]
            candidate = registry.get('candidate_loop')
            if candidate:
                tables += [table('candidate_bridges', candidate['bridge_record_base'], candidate['bridge_records'])]
                windows += [window('candidate', candidate['candidate_surface'], candidate['bridge_records'])]
            if sum(t['count'] for t in tables) != n:
                raise ValueError('record count differs from registry')
            ops = AFB_OPS
            details = dict(registry_offset=base, registry_status=registry.get('status'),
                           prefix_bytes=prefix, decoded_from='in-file MUHLAFB1 registry')
        elif profile == 'autofab0':
            if size % 25:
                raise ValueError('AUTOFAB0 gate-first file has trailing partial record')
            tables = [table('records', 0, size // 25)]
            ops = AFB_OPS
            details = dict(decoded_from='AUTOFAB0_BITS.md / gate-first 25-byte physical rows',
                           addressed_destinations_may_extend_beyond_file=True)
        elif profile in ('reader1', 'visible6'):
            sidecar = path.with_suffix('.layout.json')
            spec = json.loads(sidecar.read_text(encoding='utf-8'))
            if spec.get('header_bytes_in_container') != 0:
                raise ValueError('expected headerless sidecar geometry')
            if profile == 'reader1':
                tables = [table('records', 0, spec['n_gate'])]
                details['logical_cursor'] = spec['cursor']
                details['logical_target_table_file'] = spec['table']
                details['address_warning'] = 'Bare records: logical wires overlap container record bytes. Do not treat logical offsets as physical state windows without the consumer contract.'
            else:
                tables = [table('records', spec['gates'], spec['n_gate'])]
                windows = [window('state_head', spec['state'], min(64, spec['state_len'])),
                           window('observation_head', spec['obs'], min(64, spec['obs_len']), 'output')]
            details.update(decoded_from=str(sidecar), sidecar_sha256=hashlib.sha256(sidecar.read_bytes()).hexdigest(),
                           opcode_map='numeric only; not inferred from another container family')
        else:
            raise ValueError(f'unknown profile {profile}')
        for region in tables + windows:
            if region['offset'] < 0 or region['offset'] + region['length'] > size:
                raise ValueError(f'{region["name"]} is outside current file')
    for w in windows:
        for index in range(w['length']):
            symbols[w['offset'] + index] = w['name'] + (f'[{index}]' if w['length'] > 1 else '')
    return dict(size=size, tables=tables, windows=windows, symbols=symbols, ops=ops, details=details)


def rows(path, descriptor):
    with path.open('rb') as stream:
        stream.seek(descriptor['offset'])
        for index in range(descriptor['count']):
            raw = stream.read(25)
            if len(raw) != 25:
                raise ValueError('short record')
            op, a, b, dest = GATE.unpack(raw)
            yield dict(table=descriptor['name'], index=index,
                       record_offset=descriptor['offset'] + 25 * index,
                       opcode=op, a=a, b=b, out=dest)


def annotate(row, spec, bits=False):
    row = dict(row)
    row['operation'] = spec['ops'].get(row['opcode'], f'opcode:{row["opcode"]}')
    row['address_names'] = {k: spec['symbols'].get(row[k]) for k in ('a', 'b', 'out')}
    row['self_feedback'] = row['out'] in (row['a'], row['b'])
    row['addresses_within_file'] = all(0 <= row[k] < spec['size'] for k in ('a', 'b', 'out'))
    row['output_record_target'] = None
    for t in spec['tables']:
        relative = row['out'] - t['offset']
        if 0 <= relative < t['length']:
            index, byte = divmod(relative, 25)
            field = 'opcode' if byte == 0 else 'a' if byte < 9 else 'b' if byte < 17 else 'out'
            field_byte = byte if byte == 0 else byte-1 if byte < 9 else byte-9 if byte < 17 else byte-17
            row['output_record_target'] = dict(table=t['name'], index=index,
                                               record_offset=t['offset'] + index*25,
                                               field=field, byte_in_field=field_byte)
            if row['address_names']['out'] is None:
                row['address_names']['out'] = f'{t["name"]} record {index}.{field}[byte {field_byte}]'
            break
    if bits:
        raw = GATE.pack(row['opcode'], row['a'], row['b'], row['out'])
        row['raw_bits'] = ' '.join(f'{b:08b}' for b in raw)
    return row


def selected(args):
    project, entry, path = artifact(args)
    return project, entry, path, layout(path, entry['profile'])


def cmd_status(args):
    project, roots = load_project(args)
    result = dict(project=project['project'], exclude_projects=project['exclude_projects'], observed_at=now(), artifacts=[])
    for name, entry in project['artifacts'].items():
        path = Path(entry['path'].format_map(roots))
        result['artifacts'].append(dict(name=name, path=str(path), exists=path.exists(),
                                       bytes=path.stat().st_size if path.exists() else None,
                                       role=entry['role'], recorded_status=entry['recorded_status']))
    root_list = HERE / 'ROOTS.tsv'
    if root_list.exists():
        with root_list.open(encoding='utf-8-sig', newline='') as stream:
            entries = list(csv.DictReader(stream, delimiter='\t'))
        result['root_catalog'] = dict(entries=len(entries), existing=sum(Path(r['path']).is_dir() for r in entries),
                                     meaning='Root inventory is not full content reading')
    emit(result, args.out)


def cmd_tools(args):
    project, roots = load_project(args)
    catalog = json.loads((Path(args.project).resolve().parent / 'TOOLS.json').read_text(encoding='utf-8'))
    found = []
    for item in catalog['tools']:
        if args.query and args.query.lower() not in json.dumps(item).lower():
            continue
        path = Path(item['path'].format_map(roots))
        found.append({**item, 'resolved_path': str(path), 'exists': path.is_file()})
    emit(dict(project=project['project'], tools=found, source='Static source contracts; execution measurements are separate'), args.out)


def cmd_inspect(args):
    project, entry, path, spec = selected(args)
    counts, writers = Counter(), Counter()
    self_feedback = beyond = total = 0
    table_report = []
    with path.open('rb') as stream:
        for t in spec['tables']:
            table_report.append({**t, 'sha256': digest_region(stream, t['offset'], t['length'])})
        current = [{**w, 'hex': read_at(stream, w['offset'], w['length']).hex()} for w in spec['windows']]
    for t in spec['tables']:
        for row in rows(path, t):
            total += 1
            counts[row['opcode']] += 1
            writers[row['out']] += 1
            self_feedback += row['out'] in (row['a'], row['b'])
            beyond += any(row[k] >= spec['size'] for k in ('a', 'b', 'out'))
    emit(dict(project=project['project'], artifact=args.artifact, path=str(path), observed_at=now(),
              bytes=spec['size'], interpretation='Static addresses and current bytes; no gate execution',
              details=spec['details'], tables=table_report, windows=current, records=total,
              opcode_counts=dict(counts), self_feedback_rows=self_feedback,
              multi_writer_destinations=sum(n > 1 for n in writers.values()),
              records_with_addresses_beyond_file=beyond), args.out)


def cmd_records(args):
    _, _, path, spec = selected(args)
    t = next(t for t in spec['tables'] if t['name'] == args.table)
    if args.start < 0 or args.count < 1 or args.start + args.count > t['count']:
        raise ValueError('record selection outside table')
    descriptor = table(t['name'], t['offset'] + args.start * 25, args.count)
    output = []
    for row in rows(path, descriptor):
        row['index'] += args.start
        output.append(annotate(row, spec, args.bits))
    emit(dict(artifact=args.artifact, path=str(path), records=output), args.out)


def cmd_bytes(args):
    _, _, path, spec = selected(args)
    offset = resolve_address(args.address, spec)
    if args.length < 1 or offset + args.length > spec['size']:
        raise ValueError('byte selection outside file')
    with path.open('rb') as stream:
        raw = read_at(stream, offset, args.length)
    emit(dict(artifact=args.artifact, path=str(path), offset=offset, length=len(raw),
              sha256=hashlib.sha256(raw).hexdigest(),
              bytes=[dict(offset=offset+i, name=spec['symbols'].get(offset+i),
                          hex=f'{value:02x}', bits=f'{value:08b}')
                     for i, value in enumerate(raw)]), args.out)


def cmd_joins(args):
    _, _, path, spec = selected(args)
    outputs, inputs = defaultdict(list), defaultdict(list)
    for t in spec['tables']:
        for row in rows(path, t):
            outputs[row['out']].append(row)
            for address in set((row['a'], row['b'])):
                inputs[address].append(row)
    cross = defaultdict(set)
    for address in outputs.keys() & inputs.keys():
        for producer in outputs[address]:
            for consumer in inputs[address]:
                if producer['table'] != consumer['table']:
                    cross[(producer['table'], consumer['table'])].add(address)
    collisions = []
    for address, writers in sorted(outputs.items()):
        if len(writers) < 2:
            continue
        regions = [t['name'] for t in spec['tables'] if t['offset'] <= address < t['offset']+t['length']]
        collisions.append(dict(address=address, name=spec['symbols'].get(address),
                               destination_record_tables=regions,
                               writers=[annotate(row, spec) for row in writers]))
    emit(dict(artifact=args.artifact, interpretation='Address relationships, not execution. Multiple writers can be deliberate self-editing; inspect their operations and destinations.',
              cross_table_connections=[dict(producer=a, consumer=b, shared_addresses=sorted(addresses))
                                       for (a,b), addresses in sorted(cross.items())],
              multi_writer_destinations=collisions), args.out)


def resolve_address(text, spec):
    for region in spec['windows']:
        if region['name'] == text:
            return region['offset']
    for addr, name in spec['symbols'].items():
        if name == text:
            return addr
    return integer(text)


def cmd_trace(args):
    _, _, path, spec = selected(args)
    address = resolve_address(args.address, spec)
    by_input, by_output = defaultdict(list), defaultdict(list)
    for t in spec['tables']:
        for row in rows(path, t):
            by_output[row['out']].append(row)
            for a in set((row['a'], row['b'])):
                by_input[a].append(row)
    pending, visited, included = deque([(address, 0)]), set(), {}
    frontier = []
    mapping = by_output if args.direction == 'upstream' else by_input
    while pending:
        addr, depth = pending.popleft()
        if addr in visited:
            continue
        visited.add(addr)
        if depth >= args.hops:
            frontier.append(addr)
            continue
        for row in mapping.get(addr, []):
            included[row['record_offset']] = annotate(row, spec)
            next_addresses = (row['a'], row['b']) if args.direction == 'upstream' else (row['out'],)
            pending.extend((a, depth + 1) for a in next_addresses)
    emit(dict(artifact=args.artifact, address=address, address_name=spec['symbols'].get(address),
              direction=args.direction, hop_limit=args.hops, visited_addresses=len(visited),
              root_writer_count=len(by_output.get(address, [])),
              frontier_addresses=frontier, records=list(included.values()),
              interpretation='Physical wiring traversal only; cycles are retained, never evaluated'), args.out)


def cmd_capture(args):
    project, entry, path, spec = selected(args)
    before = path.stat()
    with path.open('rb') as stream:
        windows = [{**w, 'hex': read_at(stream, w['offset'], w['length']).hex()} for w in spec['windows']]
        tables = [{**t, 'sha256': digest_region(stream, t['offset'], t['length'])} for t in spec['tables']]
    after = path.stat()
    emit(dict(schema='muhlnickel.workbench.capture.v1', project=project['project'],
              artifact=args.artifact, profile=entry['profile'], path=str(path),
              observed_at=now(), note=args.note, bytes=after.st_size,
              stable_during_read=(before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
              windows=windows, tables=tables,
              coverage='Named state/input/output windows and complete named record tables only'), args.out)


def cmd_compare(args):
    a = json.loads(Path(args.before).read_text(encoding='utf-8'))
    b = json.loads(Path(args.after).read_text(encoding='utf-8'))
    if a.get('schema') != 'muhlnickel.workbench.capture.v1' or b.get('schema') != a['schema']:
        raise ValueError('expected two workbench captures')
    if (a['profile'], a['artifact']) != (b['profile'], b['artifact']):
        raise ValueError('captures describe different artifact profiles')
    if a['path'] != b['path'] and not args.specimens:
        raise ValueError('different specimen paths; use --specimens for an explicit cross-specimen comparison')
    if not a['stable_during_read'] or not b['stable_during_read']:
        raise ValueError('source changed during a capture; take another bounded capture')
    aw, bw = {w['name']: w for w in a['windows']}, {w['name']: w for w in b['windows']}
    if aw.keys() != bw.keys():
        raise ValueError('captured window sets changed')
    unknown = set(args.host_input) - aw.keys()
    if unknown:
        raise ValueError('unknown declared input window: ' + ', '.join(sorted(unknown)))
    changed = []
    for name, old in aw.items():
        new = bw[name]
        if (old['offset'], old['length']) != (new['offset'], new['length']):
            raise ValueError('window layout changed; inspect the new geometry')
        for index, (x, y) in enumerate(zip(bytes.fromhex(old['hex']), bytes.fromhex(new['hex']))):
            if x != y:
                changed.append(dict(window=name, offset=old['offset'] + index, before=x, after=y,
                                    declared_host_input=name in args.host_input))
    at, bt = {t['name']: t for t in a['tables']}, {t['name']: t for t in b['tables']}
    if at.keys() != bt.keys():
        raise ValueError('captured table sets changed')
    changed_tables = [name for name in at if at[name] != bt[name]]
    emit(dict(before=args.before, after=args.after, observed_at=now(),
              same_source_path=a['path'] == b['path'],
              declared_host_input_windows=args.host_input, changed_bytes=changed,
              changed_record_tables=changed_tables, size_delta=b['bytes'] - a['bytes'],
              changes_outside_declared_inputs=sum(not c['declared_host_input'] for c in changed),
              interpretation='Observed differences only; caller-supplied input labels are not proof of cause. Uncaptured bytes are not covered.'), args.out)


def cmd_html(args):
    project, entry, path, spec = selected(args)
    if not args.out:
        raise ValueError('html requires --out for a new standalone snapshot')
    all_rows = [annotate(row, spec) for t in spec['tables'] for row in rows(path, t)]
    with path.open('rb') as stream:
        signals = [{**w, 'hex': read_at(stream, w['offset'], w['length']).hex()} for w in spec['windows']]
    data = dict(project=project['project'], artifact=args.artifact, path=str(path), observed_at=now(),
                bytes=spec['size'], status=entry['recorded_status'], details=spec['details'],
                tables=spec['tables'], signals=signals, records=all_rows)
    encoded = json.dumps(data, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Muhlnickel Titan workbench</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0e151a;color:#e2ebed;font:15px system-ui,sans-serif}header{padding:28px 36px;background:#15242b;border-bottom:1px solid #34505c}h1{font-size:27px;margin:5px 0 12px}p{line-height:1.6;margin:8px 0}.kicker{color:#8ee6be;font-size:12px;letter-spacing:.12em;text-transform:uppercase}.scope{color:#f6cb85}main{padding:24px 36px}section{margin-bottom:24px}.signals{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:10px}.signal{padding:14px;background:#17272e;border:1px solid #34505c;border-radius:8px}.signal strong{display:block}.signal code{display:block;color:#9ee0cf;word-break:break-all;margin-top:8px}small{color:#9eb0b9}input,select,button{background:#1a2c35;color:#e2ebed;border:1px solid #41606d;border-radius:6px;padding:9px 12px;font:inherit}input{width:min(600px,100%)}button{cursor:pointer}a{color:#92decf}.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;position:sticky;top:0;background:#0e151a;padding:12px 0}table{width:100%;border-collapse:collapse;font:13px ui-monospace,monospace}th,td{padding:9px 10px;text-align:left;border-bottom:1px solid #283e49;vertical-align:top}th{color:#a0b6be}tr:hover{background:#152831}.address{cursor:pointer;color:#91d8cd;text-decoration:underline;text-decoration-style:dotted}.feedback{color:#f6cb85}details{background:#13232c;padding:12px;border-radius:6px}pre{white-space:pre-wrap;word-break:break-all;color:#afc3cc}.tablewrap{overflow:auto}footer{color:#9eb0b9;padding:24px 36px;border-top:1px solid #34505c}
</style><header><div class="kicker">Physical bytes · named signals · address wiring</div><h1>Muhlnickel Titan workbench</h1><p class="scope">Weightless, one-file speaking Titan — separate from Kaggriculture Titan and the Kaggle/ARC agent.</p><p id="summary"></p><small id="source"></small></header><main>
<section><h2>Named byte windows</h2><p>Click a window to show every stored record touching it. Values are from this saved inspection.</p><div id="signals" class="signals"></div></section>
<section><h2>Wiring bench</h2><div class="controls"><input id="query" placeholder="Address, signal, operation, or out:8548720 / in:8548720"><select id="region"><option value="">All record tables</option></select><button id="clear">Clear</button><span id="count"></span></div><p><small>Click an address to follow its writers and readers. A repeated address is a physical connection; this viewer does not execute gates. The table displays up to 300 matching rows at a time.</small></p><div class="tablewrap"><table><thead><tr><th>Table / row</th><th>Record byte</th><th>Operation</th><th>Input A</th><th>Input B</th><th>Output</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<details><summary>Container interpretation and current status</summary><pre id="details"></pre></details></main><footer>This is an inspection snapshot, not a running model or a measured inference/training result. Re-run bench.py html to read fresh file bytes. Source files are opened read-only.</footer>
<script id="data" type="application/json">__DATA__</script><script>
const d=JSON.parse(document.getElementById('data').textContent),q=document.getElementById('query'),region=document.getElementById('region');
document.getElementById('summary').textContent=`${d.artifact} · ${d.bytes.toLocaleString()} bytes · ${d.records.length.toLocaleString()} physical records`;
document.getElementById('source').textContent=`Read ${d.observed_at} from ${d.path}`;
document.getElementById('details').textContent=JSON.stringify({status:d.status,interpretation:d.details,tables:d.tables},null,2);
for(const t of d.tables){const o=document.createElement('option');o.value=t.name;o.textContent=t.name;region.append(o)}
for(const s of d.signals){const el=document.createElement('button');el.className='signal';const label=document.createElement('strong');label.textContent=s.name;const sub=document.createElement('small');sub.textContent=`byte ${s.offset} · ${s.length} bytes · ${s.role}`;const v=document.createElement('code');v.textContent=s.hex;el.append(label,sub,v);el.onclick=()=>{q.value=s.name;region.value='';render()};document.getElementById('signals').append(el)}
function matches(r,text){if(!text)return true;const m=/^(in|out):\s*(0x[0-9a-f]+|\d+)$/i.exec(text);if(m){const n=Number(m[2]);return m[1].toLowerCase()==='out'?r.out===n:r.a===n||r.b===n}if(/^(0x[0-9a-f]+|\d+)$/i.test(text)){const n=Number(text);return [r.a,r.b,r.out].includes(n)||(r.record_offset<=n&&n<r.record_offset+25)}return [r.table,r.operation,...Object.values(r.address_names)].join(' ').toLowerCase().includes(text.toLowerCase())}
function render(){const text=q.value.trim();const found=d.records.filter(r=>(!region.value||r.table===region.value)&&matches(r,text));document.getElementById('count').textContent=`${found.length.toLocaleString()} matching records`;const body=document.getElementById('rows');body.replaceChildren();for(const r of found.slice(0,300)){const tr=document.createElement('tr');for(const value of [`${r.table} / ${r.index}`,r.record_offset,r.operation+(r.self_feedback?' ↺':'')]){const td=document.createElement('td');td.textContent=value;tr.append(td)}for(const key of ['a','b','out']){const td=document.createElement('td');td.className='address';td.textContent=String(r[key]);if(r.address_names[key]){const label=document.createElement('small');label.textContent=' '+r.address_names[key];td.append(label)}td.onclick=()=>{q.value=String(r[key]);region.value='';render()};tr.append(td)}body.append(tr)}}
q.oninput=render;region.onchange=render;document.getElementById('clear').onclick=()=>{q.value='';region.value='';render()};render();
</script></html>'''
    target = Path(args.out).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(template.replace('__DATA__', encoded))
    print(json.dumps(dict(output=str(target), records=len(all_rows), source=str(path))))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', default=str(HERE / 'PROJECT.json'))
    p.add_argument('--root', action='append', default=[], metavar='NAME=PATH')
    subs = p.add_subparsers(dest='command', required=True)
    for name, fn in [('status', cmd_status), ('tools', cmd_tools), ('inspect', cmd_inspect), ('records', cmd_records),
                     ('bytes', cmd_bytes), ('joins', cmd_joins),
                     ('html', cmd_html),
                     ('trace', cmd_trace), ('capture', cmd_capture), ('compare', cmd_compare)]:
        q = subs.add_parser(name)
        q.set_defaults(run=fn)
        q.add_argument('--out', help='Create a new JSON result; existing paths are never overwritten')
        if name not in ('status', 'compare', 'tools'):
            q.add_argument('artifact')
            q.add_argument('--file', help='Use this specimen with the named artifact profile')
        if name == 'tools':
            q.add_argument('query', nargs='?', default='')
        elif name == 'records':
            q.add_argument('table')
            q.add_argument('--start', type=integer, default=0)
            q.add_argument('--count', type=integer, default=8)
            q.add_argument('--bits', action='store_true')
        elif name == 'trace':
            q.add_argument('address', help='Named window byte or integer/hex address')
            q.add_argument('--direction', choices=['upstream', 'downstream'], default='upstream')
            q.add_argument('--hops', type=int, default=3)
        elif name == 'bytes':
            q.add_argument('address', help='Named window byte or integer/hex address')
            q.add_argument('--length', type=integer, default=8)
        elif name == 'capture':
            q.add_argument('--note', default='')
        elif name == 'compare':
            q.add_argument('before')
            q.add_argument('after')
            q.add_argument('--host-input', action='append', default=[])
            q.add_argument('--specimens', action='store_true', help='Compare two specimens with matching named geometry; does not imply causality')
    args = p.parse_args()
    try:
        if args.command == 'trace' and args.hops < 1:
            raise ValueError('hops must be positive')
        args.run(args)
    except (OSError, ValueError, KeyError, StopIteration, struct.error) as exc:
        print(json.dumps(dict(error=str(exc), command=args.command)), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
