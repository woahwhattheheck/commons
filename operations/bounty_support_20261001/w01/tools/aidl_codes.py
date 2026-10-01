#!/usr/bin/env python3
"""List binder interfaces in a javap-able classes dir: descriptor, role (proxy/stub),
and transaction code -> method signature.
usage: aidl_codes.py <classes_dir> <descriptor-prefix>"""
import os, re, subprocess, sys

root, prefix = sys.argv[1], sys.argv[2]
pat = prefix.encode()
cands = []
for d, _, fs in os.walk(root):
    for f in fs:
        if f.endswith('.class'):
            p = os.path.join(d, f)
            if pat in open(p, 'rb').read():
                cands.append(os.path.relpath(p, root)[:-6].replace('/', '.'))

def javap(name):
    r = subprocess.run(['javap', '-p', '-c', '-cp', root, name], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'javap failed for {name}: {r.stderr.strip()}')
    return r.stdout

def methods(src):
    # split into (signature, body)
    out = []
    for m in re.finditer(r'\n  ([^\n]*\)(?: throws [^\n]*)?;)\n    Code:\n(.*?)(?=\n\n|\n\}\s*$)', src, re.S):
        out.append((m.group(1), m.group(2)))
    return out

INT = re.compile(r'\d+: (?:iconst_(\d)|bipush\s+(\d+)|sipush\s+(\d+))')
found = 0
for c in sorted(cands):
    src = javap(c)
    desc = re.findall(r'// String (' + re.escape(prefix) + r'[\w.$]+)', src)
    desc = [d for d in desc if re.search(r'\.I[A-Z]\w*$', d)][:1]
    if not desc:
        continue
    head = src.splitlines()[1] if len(src.splitlines()) > 1 else ''
    ms = methods(src)
    stub = [b for s, b in ms if re.search(r'\(int, android\.os\.Parcel, android\.os\.Parcel, int\)', s)]
    if stub:
        body = stub[0]
        sw = re.search(r'(tableswitch|lookupswitch)\s*\{[^\n]*\n(.*?)\n\s*default: (\d+)', body, re.S)
        lines = {int(a): b for a, b in re.findall(r'\n\s*(\d+): ([^\n]*)', '\n' + body)}
        offs = sorted(lines)
        entries = []
        if sw:
            for code, off in re.findall(r'(\d+): (\d+)', sw.group(2)):
                off = int(off); call = '?'
                for o in offs:
                    if o < off: continue
                    mm = re.search(r'invoke(?:virtual|interface)\s+#\d+\s+// (?:Interface)?Method (\S+)', lines[o])
                    if mm and 'android/os/Parcel' not in mm.group(1) and 'internal/cast/zzc' not in mm.group(1) and 'internal/cast/zzd' not in mm.group(1):
                        call = mm.group(1); break
                entries.append((int(code), call))
        found += 1
        print(f'STUB  {c}  {desc}')
        for code, call in entries:
            print(f'   {code:3d} {call}')
        continue
    entries = []
    for s, b in ms:
        if 'transact' not in b and not re.search(r':\(ILandroid/os/Parcel;\)', b):
            continue
        m = INT.search(b)
        if not m: continue
        code = int(next(g for g in m.groups() if g is not None))
        entries.append((code, s.strip()))
    if entries:
        found += 1
        print(f'PROXY {c}  {desc}')
        for code, s in sorted(entries):
            print(f'   {code:3d} {s}')

if not found:
    sys.exit(f'no binder interfaces with descriptor prefix {prefix} under {root}')
