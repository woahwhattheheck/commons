# SPDX-License-Identifier: Apache-2.0
"""Build the frozen V3.1 production / V4 economics composition for evaluation."""
import argparse
import ast
import json
from pathlib import Path

from build_delivery import archive_bytes, digest, members

V31_SHA = '5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361'
DELIVERY_SHA = '0d42ee5fabb089745fa0064207654bfdf5df9466ba6499d91b6e685d4880cab1'
CANDIDATE_SHA = '0aded66a2c393cc60f4f45d10f11c384a7e788182bf5430863829a02b66daf02'
VENDOR = 'reference/next-panel/vendor/arlene.py'
DEPENDENCIES = (
    'b11_mirror_horizon.py', 'b5_fertilize.py', 'b9_terminal_fertilizer.py',
    'h3c_goose_eod_cap_rescue.py', 'jit_pass_fertilize.py', 'r01_tapes.py',
    'r04_dribble_dump.py', 'r04_fert_hand.py', 'r04_full_router.py',
    'r04_h4_strawberry.py', 'r04_kill_late_water.py',
    'r04_no_late_sale_advance.py', 'r04_strawberry_endgame.py',
)


def dependency_closure(v31):
    seen, todo = set(), ['r04_full_router.py']
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        if name not in v31:
            raise ValueError('Missing donor dependency: ' + name)
        seen.add(name)
        for node in ast.walk(ast.parse(v31[name])):
            imports = ([alias.name.split('.')[0] for alias in node.names]
                       if isinstance(node, ast.Import) else
                       [node.module.split('.')[0]]
                       if isinstance(node, ast.ImportFrom) and node.module else [])
            todo.extend(x + '.py' for x in imports if x + '.py' in v31 and x + '.py' not in seen)
    if seen != set(DEPENDENCIES):
        raise ValueError('Expected the exact 13-file donor dependency closure')
    return seen


def compose(v31, delivery, overlay):
    dependency_closure(v31)
    files = dict(delivery)
    for name in DEPENDENCIES:
        if name in files and files[name] != v31[name]:
            raise ValueError('Incompatible existing dependency: ' + name)
        files[name] = v31[name]
    original = files[VENDOR].replace(b'\r\n', b'\n')
    anchor = b'\n_A = None\n'
    if original.count(anchor) != 1:
        raise ValueError('Expected one vendor class insertion seam')
    overlay = overlay.replace(b'\r\n', b'\n')
    files[VENDOR] = original.replace(anchor, b'\n' + overlay + b'\n_A = None\n')
    # Preserve the exact tested context member, including its original line end.
    files['full_production_context.py'] = b'configuration = {}\r\n'
    entry = files['main.py'].replace(b'\r\n', b'\n')
    needle = b'    returned = baseline.agent(observation, configuration)'
    if entry.count(needle) != 1:
        raise ValueError('Expected one outer delivery call seam')
    files['main.py'] = entry.replace(needle,
        b'    import full_production_context\n'
        b'    full_production_context.configuration = dict(configuration or {})\n' + needle)
    if digest(archive_bytes(files)) != CANDIDATE_SHA:
        raise ValueError('Composition differs from the tested production archive')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v31', type=Path, required=True)
    parser.add_argument('--delivery', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--tar', type=Path, required=True)
    args = parser.parse_args()
    receipt_path = args.out.parent / (args.out.name + '-manifest.json')
    if any(p.exists() for p in (args.out, args.tar, receipt_path)):
        parser.error('Use new output directory, archive and manifest paths')
    v31 = members(args.v31, V31_SHA)
    delivery = members(args.delivery, DELIVERY_SHA)
    overlay = Path(__file__).with_name('production_recovery_overlay.txt').read_bytes()
    files = compose(v31, delivery, overlay)
    packed = archive_bytes(files)
    args.out.mkdir(parents=True)
    for name, body in files.items():
        path = args.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    args.tar.parent.mkdir(parents=True, exist_ok=True)
    with args.tar.open('xb') as stream:
        stream.write(packed)
    receipt = {'schema': 'titan-production-recovery-build/v2',
        'v31_archive_sha256': V31_SHA, 'delivery_archive_sha256': DELIVERY_SHA,
        'candidate_archive_sha256': CANDIDATE_SHA, 'donor_dependencies': list(DEPENDENCIES),
        'files': {name: digest(body) for name, body in sorted(files.items())},
        'kaggle_submission_hold': True}
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'members': len(files),
                      'candidate_archive_sha256': CANDIDATE_SHA}))


if __name__ == '__main__':
    main()
