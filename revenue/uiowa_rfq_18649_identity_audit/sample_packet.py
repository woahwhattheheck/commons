"""Synthetic conservation packet. These are not University records or findings."""
from copy import deepcopy
import json


def packet():
    def record(namespace, kind, identifier, revision='v1'):
        return {'namespace': namespace, 'kind': kind, 'id': identifier, 'revision': revision,
                'synthetic': True, 'source_locators': [f'synthetic://{namespace}/{kind}/{identifier}/{revision}'],
                'payload': {'null_value': None, 'empty_value': '', 'flags': [False, 0, 0.0],
                            'note': 'FICTION — prepared solely for a conservation test'},
                'extension': {'unknown': {'retained': ['α', None, 1]}, 'version': 1}}
    source1 = record('registry-A', 'source', 'EVID-01')
    source2 = record('registry-B', 'source', 'EVID-01')
    source3 = record('registry-A', 'source', 'EVID-01', 'v2')
    observation = record('analysis', 'observation', 'OBS-1')
    finding = record('analysis', 'finding', 'F-1')
    recommendation = record('roadmap', 'recommendation', 'R-1')
    service = record('inventory', 'service', 'SVC-1')
    def key(row):
        return {name: row[name] for name in ('namespace', 'kind', 'id', 'revision')}
    def link(identifier, left, right):
        return {'link_id': identifier, 'relation': 'synthetic_reference_only', 'from': key(left),
                'to': right, 'extension': {'follow_up': None, 'state': 'UNKNOWN'}}
    return {'schema': 'uiowa.identity-map.v1',
            'records': [source1, source2, source3, observation, finding, recommendation, service, deepcopy(source1)],
            'equivalences': [{'decision_id': 'DECISION-1', 'relation': 'same_entity', 'left': key(source1),
                              'right': key(source2), 'reason': 'Fictional retained crosswalk only; not factual verification.',
                              'evidence_locators': ['synthetic://crosswalk/1'],
                              'extension': {'reviewer_role': 'Synthetic assessor', 'detail': None}}],
            'links': [link('LINK-1', observation, key(source1)), link('LINK-2', finding, key(observation)),
                      link('LINK-3', recommendation, key(finding)), link('LINK-4', service, {'kind': 'source', 'id': 'EVID-01'}),
                      link('LINK-5', observation, {'namespace': 'registry-A', 'kind': 'source', 'id': 'MISSING', 'revision': 'v1'})],
            'scenario': 'SYNTHETIC — no University evidence; eight inputs, seven occurrences, one collision, five links, two unresolved.',
            'envelope_extension': {'unset': None, 'empty': [], 'counts': [True, 1, 1.0]}}


if __name__ == '__main__':
    print(json.dumps(packet(), sort_keys=True, indent=2, ensure_ascii=False))
