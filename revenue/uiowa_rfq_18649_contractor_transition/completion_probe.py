"""Independent fictional transition evidence probes; no external actions."""
import copy, importlib, json, pathlib, sys

def closed_packet():
    return {
        'packet_id': 'SYNTHETIC-REVIEW-ONLY',
        'transition': {'departing_ref': 'SYN-PERSON-001'},
        'people': [
            {'id': 'SYN-PERSON-001', 'role': 'contractor', 'employment_type': 'contractor', 'service': 'ESS', 'account_name': 'syn-c-1', 'synthetic': True},
            {'id': 'SYN-PERSON-002', 'role': 'lead', 'employment_type': 'staff', 'service': 'ESS', 'account_name': 'syn-s-2', 'synthetic': True},
        ],
        'applications': [{'id': 'SYN-APP-001', 'name': 'Fictional App', 'service': 'ESS', 'owner_ref': 'SYN-PERSON-001', 'successor_ref': 'SYN-PERSON-002', 'synthetic': True}],
        'service_identities': [], 'runbooks': [],
        'access_changes': [{'id': 'SYN-CHG-001', 'subject_ref': 'SYN-PERSON-001', 'target_ref': 'SYN-APP-001', 'action': 'REASSIGN_OWNER', 'status': 'COMPLETED', 'completed_at': '2026-09-15', 'evidence_ref': 'synthetic://review/evidence-1', 'synthetic': True}],
    }

def cases():
    clean = closed_packet()
    yield 'clean_control', clean, True
    for name, val in [('missing_date', None), ('blank_date', ''), ('impossible_date', '2026-02-30'), ('unparseable_date', 'not-a-date')]:
        p = copy.deepcopy(clean)
        if val is None:
            p['access_changes'][0].pop('completed_at')
        else:
            p['access_changes'][0]['completed_at'] = val
        yield name, p, False
    p = copy.deepcopy(clean); p['access_changes'][0]['action'] = 'NOT_AN_ACTION'
    yield 'unknown_action', p, False
    p = copy.deepcopy(clean); p['access_changes'].append(copy.deepcopy(p['access_changes'][0]))
    yield 'duplicate_change', p, False
    p = copy.deepcopy(clean); p['access_changes'][0]['successor_ref'] = 'SYN-PERSON-999'
    yield 'broken_change_reference', p, False
    p = copy.deepcopy(clean); p['applications'][0]['successor_ref'] = 'SYN-APP-001'
    yield 'successor_is_application', p, False
    p = copy.deepcopy(clean); p['people'][1].pop('role')
    yield 'invalid_successor_record', p, False
    p = copy.deepcopy(clean); p['access_changes'][0].pop('action')
    yield 'missing_action', p, False
    p = copy.deepcopy(clean); p['access_changes'][0]['evidence_ref'] = ['synthetic://review/evidence-1']
    yield 'list_locator', p, False

def main():
    root = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    transition = importlib.import_module('transition')
    results = []
    for name, packet, expected in cases():
        try:
            report, issues = transition.build(packet)
            results.append({'case': name, 'expected_closed': expected, 'observed_closed': report.transition_closed(), 'states': [i['state'] for i in report.items], 'issues': [i.code for i in issues], 'matched': report.transition_closed() is expected})
        except Exception as e:
            results.append({'case': name, 'expected_closed': expected, 'exception': type(e).__name__, 'message': str(e), 'matched': False})
    print(json.dumps({'python_optimized': not __debug__, 'cases': results}, indent=2))
    return 0 if all(row['matched'] for row in results) else 1

if __name__ == '__main__': raise SystemExit(main())
