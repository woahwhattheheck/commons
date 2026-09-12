# SPDX-License-Identifier: Apache-2.0
"""Build the P01 payback-gated V219 arm on the exact production-v3 family."""
import argparse
import json
from pathlib import Path

from build_delivery import archive_bytes, digest, members
from build_production_recovery import CANDIDATE_SHA as BASE_SHA, DELIVERY_SHA, V31_SHA, compose

ROUTER = 'r04_full_router.py'
ROUTER_SHA = '41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a'
GATE = 'p01_productive_expansion_gate.py'
ANCHOR = b'\n\ndef _v219_walk(pos, target):\n'
WRAPPER = b'''\n\n# P01 / TITAN-V5-PRODUCTIVE-EXPANSION-WIDE: default-off experiment carrier.\n# Keep the original V219 identity/land/worker checks, then require observed payback.\n_V219_QUALIFIES_PARENT = _v219_qualifies\nfor _key in ('p01_gate_checks', 'p01_gate_accepts', 'p01_payback_rejects',\n             'p01_gate_passthroughs', 'p01_visible_rival_supply_bound',\n             'p01_projected_gross', 'p01_total_cost'):\n    _V219_REPORT.setdefault(_key, 0)\n\ndef _v219_qualifies(obs, native):\n    if not _V219_QUALIFIES_PARENT(obs, native):\n        return False\n    import p01_productive_expansion_gate as _p01\n    record = _p01.evaluate(obs, native, _v219_native_day, _v219_fib, _ro_price)\n    _V219_REPORT['p01_gate_checks'] += 1\n    if record['decision'] is None:\n        _V219_REPORT['p01_gate_passthroughs'] += 1\n        return True\n    _V219_REPORT['p01_visible_rival_supply_bound'] = int(record['visible_rival_supply_bound'])\n    _V219_REPORT['p01_projected_gross'] = int(record['projected_gross'])\n    _V219_REPORT['p01_total_cost'] = int(record['total_cost'])\n    if record['decision']:\n        _V219_REPORT['p01_gate_accepts'] += 1\n        return True\n    _V219_REPORT['p01_payback_rejects'] += 1\n    return False\n'''


def inject(base_files, gate_source):
    """Return a copy with only the exact submitted R04 router plus one gate module changed."""
    if digest(archive_bytes(base_files)) != BASE_SHA:
        raise ValueError('P01 requires the exact production-v3 base archive')
    files = dict(base_files)
    router = files.get(ROUTER)
    if router is None or digest(router) != ROUTER_SHA:
        raise ValueError('P01 requires the exact submitted V3.1 R04 router')
    if GATE in files:
        raise ValueError('P01 gate module already exists')
    if router.count(ANCHOR) != 1:
        raise ValueError('Expected one V219 qualification insertion seam')
    files[ROUTER] = router.replace(ANCHOR, WRAPPER + ANCHOR, 1)
    files[GATE] = gate_source.replace(b'\r\n', b'\n')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v31', type=Path, required=True)
    parser.add_argument('--delivery', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--tar', type=Path, required=True)
    args = parser.parse_args()
    receipt_path = args.out.parent / (args.out.name + '-manifest.json')
    if any(path.exists() for path in (args.out, args.tar, receipt_path)):
        parser.error('Use new output directory, archive and manifest paths')
    v31 = members(args.v31, V31_SHA)
    delivery = members(args.delivery, DELIVERY_SHA)
    overlay = Path(__file__).with_name('production_recovery_overlay.txt').read_bytes()
    base_files = compose(v31, delivery, overlay, 'v3')
    gate_source = Path(__file__).with_name(GATE).read_bytes()
    files = inject(base_files, gate_source)
    packed = archive_bytes(files)
    args.out.mkdir(parents=True)
    for name, body in files.items():
        path = args.out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    args.tar.parent.mkdir(parents=True, exist_ok=True)
    with args.tar.open('xb') as stream:
        stream.write(packed)
    receipt = {
        'schema': 'titan-v5-p01-productive-expansion/v1',
        'base_candidate_sha256': BASE_SHA,
        'candidate_archive_sha256': digest(packed),
        'v31_archive_sha256': V31_SHA,
        'delivery_archive_sha256': DELIVERY_SHA,
        'changed_members': [ROUTER, GATE],
        'default_activation': False,
        'kaggle_submission_hold': True,
        'files': {name: digest(body) for name, body in sorted(files.items())},
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'members': len(files),
                      'candidate_archive_sha256': digest(packed)}))


if __name__ == '__main__':
    main()
