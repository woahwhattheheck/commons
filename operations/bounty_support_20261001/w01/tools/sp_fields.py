#!/usr/bin/env python3
"""Print SafeParcel field id -> reader call for a class's CREATOR, from a javap'd jar dir.
usage: sp_fields.py <classes_dir> <fully.qualified.Class>"""
import re, subprocess, sys

root, cls = sys.argv[1], sys.argv[2]

def javap(name):
    r = subprocess.run(['javap', '-p', '-c', '-cp', root, name], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'javap failed for {name}: {r.stderr.strip()}')
    return r.stdout

src = javap(cls)
m = re.search(r'static \{\};(.*?)\n\s*\}', src, re.S)
if not m:
    sys.exit(f'no static initializer in {cls}')
creator = None
for line in m.group(1).splitlines():
    mm = re.search(r'new\s+#\d+\s+// class (\S+)', line)
    if mm:
        creator = mm.group(1).replace('/', '.')
    if 'putstatic' in line and 'CREATOR' in line:
        break
if not creator:
    sys.exit(f'no CREATOR construction found in {cls}')
code = javap(creator)
m = re.search(r'Object createFromParcel\(android\.os\.Parcel\);\n\s*Code:\n(.*?)(?:\n\n|\n\}\s*$)', code, re.S)
if not m:
    sys.exit(f'no typed createFromParcel in {creator}')
body = m.group(1)
lines = body.splitlines()
# find the switch on field id
sw = re.search(r'(tableswitch|lookupswitch)\s*\{[^\n]*\n(.*?)\n\s*default: (\d+)', body, re.S)
if not sw:
    sys.exit(f'no switch in {creator}')
cases = re.findall(r'(\d+): (\d+)', sw.group(2))
by_off = {}
for l in lines:
    mm = re.match(r'\s*(\d+): (.*)', l)
    if mm:
        by_off[int(mm.group(1))] = mm.group(2)
offs = sorted(by_off)
def call_at(off):
    for o in offs:
        if o < off:
            continue
        ins = by_off[o]
        mm = re.search(r'Method (?:com/google/android/gms/common/internal/safeparcel/)?SafeParcelReader\.(\w+)', ins)
        if mm:
            extra = ''
            # parcelable creators are loaded with getstatic just before
            for p in offs:
                if off <= p < o and 'getstatic' in by_off[p] and 'CREATOR' in by_off[p]:
                    extra = ' ' + by_off[p].split('// Field ')[-1].split(':')[0]
            return mm.group(1) + extra
        if 'goto' in ins or 'return' in ins:
            return '?'
    return '?'
print(f'{cls}  (creator {creator})')
for fid, off in cases:
    print(f'  {int(fid):3d}: {call_at(int(off))}')
