#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Materialize archived opponent actions and add them to an existing gauntlet.

Recorded actions are deliberately labeled diagnostic opponents. They are not
reconstructions of the competitor's observation-responsive executable policy.
"""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def action_tape(replay, seat):
    steps = replay['steps']
    if seat not in (0, 1) or len(steps) != 720 or replay.get('statuses') != ['DONE', 'DONE']:
        raise ValueError('Expected a complete two-seat 719-decision episode')
    # State zero is initialization; the next state's action caused its transition.
    actions = [deepcopy(step[seat]['action']) for step in steps[1:]]
    if not all(isinstance(a, dict) and isinstance(a.get('farmer'), list)
               and isinstance(a.get('hands', []), list)
               and isinstance(a.get('market', []), list) for a in actions):
        raise ValueError('Missing or malformed recorded action')
    return actions


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def retain_and_extend(legacy, additions):
    """Keep all original fields/order and reject collisions instead of replacing."""
    result = deepcopy(legacy)
    if not isinstance(result, dict) or not isinstance(result.get('opponents'), list):
        raise ValueError('Legacy input must be an object with opponents array')
    old = result['opponents']
    ids = [r['id'] for r in old]
    if len(ids) != len(set(ids)):
        raise ValueError('Legacy opponent IDs are not unique')
    incoming = [r['id'] for r in additions]
    if len(incoming) != len(set(incoming)) or set(ids).intersection(incoming):
        raise ValueError('Duplicate/colliding opponent ID')
    result['opponents'].extend(deepcopy(additions))
    result['additive_intake'] = {'legacy_entries':len(old)-len(additions),
        'added_entries':len(additions), 'kind':'public-recorded-actions',
        'submission_hold':True, 'legacy_preserved':True}
    return result


def materialize(corpus, output):
    corpus = corpus.resolve(strict=True)
    manifest_path = corpus/'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['schema'] != 'titan.gauntlet.top30-union.v1':
        raise ValueError('Unexpected corpus schema')
    output.mkdir(parents=True, exist_ok=False)
    additions = []
    for target in manifest['targets']:
        if target.get('status') != 'complete' or len(target.get('replays', [])) != 3:
            raise ValueError('Incomplete target acquisition: '+str(target['submission_id']))
        for fixture in target['replays']:
            path = (corpus/fixture['path']).resolve(strict=True)
            if not path.is_relative_to(corpus) or digest(path) != fixture['sha256']:
                raise ValueError('Replay path or digest mismatch')
            replay = json.loads(gzip.decompress(path.read_bytes()))
            if replay.get('info', {}).get('seed') != fixture['seed']:
                raise ValueError('Replay seed differs from manifest')
            tape = action_tape(replay, fixture['recorded_opponent_seat'])
            name = f"trace-sub-{target['submission_id']}-ep-{fixture['episode_id']}"
            directory = output/name; directory.mkdir()
            write_json(directory/'actions.json', tape)
            adapter = directory/'main.py'
            adapter.write_text('''from copy import deepcopy
import json
from pathlib import Path
_actions = json.loads((Path(__file__).parent/'actions.json').read_text())
def agent(observation, configuration=None):
    step = observation.get('step')
    if step is None:
        turns = int((configuration or {}).get('turnsPerDay',24))
        step = int(observation['day'])*turns+int(observation['hour'])
    if not isinstance(step,int) or not 0 <= step < len(_actions):
        raise ValueError('Recorded trace is exhausted or clock is invalid')
    return deepcopy(_actions[step])
''', encoding='utf-8')
            additions.append({'id':name,'kind':'recorded_trace',
                'family':f"recorded-submission:{target['submission_id']}",
                'submission_id':target['submission_id'],'team_id':target['team_id'],
                'team_name':target['team_name'],'memberships':target['memberships'],
                'episode_id':fixture['episode_id'],'seed':fixture['seed'],
                'recorded_opponent_seat':fixture['recorded_opponent_seat'],
                'candidate_seat_for_recorded_orientation':1-fixture['recorded_opponent_seat'],
                'entry':str(adapter.resolve()),'entry_sha256':digest(adapter),
                'actions_sha256':digest(directory/'actions.json'),
                'replay_sha256':fixture['sha256'],'decisions':len(tape),
                'adaptive':False,'interpretation':'Counterfactual recorded-action opponent; seat swap or new seed is a synthetic stress case.'})
    result={'schema':'titan.gauntlet.recorded-opponents.v1',
        'source_manifest_sha256':digest(manifest_path),'submission_hold':True,
        'opponents':additions,'targets':len(manifest['targets'])}
    write_json(output/'recorded-opponents.json', result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--legacy-registry',type=Path)
    args=p.parse_args()
    result=materialize(args.corpus,args.out)
    if args.legacy_registry:
        legacy=json.loads(args.legacy_registry.read_text(encoding='utf-8'))
        extended=retain_and_extend(legacy,result['opponents'])
        extended['additive_intake']['legacy_source_sha256']=digest(args.legacy_registry)
        write_json(args.out/'extended-gauntlet.json',extended)
    print(json.dumps({'targets':result['targets'],'fixtures':len(result['opponents']),
        'legacy_extended':bool(args.legacy_registry),'output':str(args.out)}))


if __name__=='__main__':main()
