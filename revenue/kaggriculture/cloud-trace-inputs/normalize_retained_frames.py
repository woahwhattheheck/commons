#!/usr/bin/env python3
"""Align already-retained DELVE frames to the existing candidate-input format.

This data derivation never imports a policy, evaluator or engine. Its only
accepted input is the checksum-bound original DELVE evidence package.
"""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import json
import re
from pathlib import Path
import zipfile

ARCHIVE_SHA = 'aaa2d811a919b6b1c2219082753cfe476a0a0fac7567d3ad1d72c9f373a912f9'
CELLS = {
    'control': ('evaluation/pilot/9965001-p0-control',
                '0d9dae2788d2a3cf39bf519a80bc02bef30181258e969310328da5ffcd02eef8'),
    'sell': ('evaluation/pilot-completion/9965001-p0-sell',
             'b6e5f3a9f180646f653309b4f426313ee324596062e43b6fc7ba1ecf25b34a98'),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def derive(archive: Path, output: Path, arm: str = 'control') -> dict:
    if arm not in CELLS:
        raise ValueError('Choose the retained control or sell cell')
    prefix, trace_sha = CELLS[arm]
    raw = archive.read_bytes()
    require(digest(raw) == ARCHIVE_SHA, 'Not the original retained DELVE package')
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('MANIFEST.json'))['files']
        for name, expected in manifest.items():
            payload = z.read(name)
            require(len(payload) == expected['bytes'] and digest(payload) == expected['sha256'],
                    'Original package member differs: ' + name)
        result_bytes = z.read(prefix + '.json')
        result = json.loads(result_bytes)
        require(result['status'] == 'complete' and result['failure'] is None,
                'Source game is not complete')
        require(result['seed'] == 9965001 and result['candidate_seat'] == 0 and
                result['steps'] == 719 and result['frame_count'] == 720,
                'Wrong original development cell')
        require(result['trace_sha256'] == trace_sha and result['arm'] == arm, 'Wrong retained original trace/arm')
        frames_bytes = z.read(prefix + '.frames.jsonl.gz')
        telemetry_bytes = z.read(prefix + '.telemetry.jsonl.gz')
        for name, payload in [(prefix + '.frames.jsonl.gz', frames_bytes),
                              (prefix + '.telemetry.jsonl.gz', telemetry_bytes)]:
            retained = result['files'][Path(name).name]
            require(len(payload) == retained['bytes'] and digest(payload) == retained['sha256'],
                    'Per-game file digest differs')
        frames = [json.loads(line) for line in gzip.decompress(frames_bytes).splitlines()]
        telemetry = [json.loads(line) for line in gzip.decompress(telemetry_bytes).splitlines()]
        require(len(frames) == 720 and len(telemetry) == 719, 'Incomplete frame/action sequence')
        configuration = frames[0]['configuration']
        require(configuration.get('seed') is None, 'Environment seed exposed in configuration')
        require(all(f['frame'] == i and len(f['state']) == 2 and
                    f['configuration'] == configuration for i, f in enumerate(frames)),
                'Frame/configuration sequence differs')
        inputs, daily, telemetry_witnesses = [], [], []
        trace = hashlib.sha256()
        for step, (before, after, actor) in enumerate(zip(frames, frames[1:], telemetry)):
            require(before['state'][0]['status'] == 'ACTIVE', 'Unexpected pre-call terminal state')
            actions = [state['action'] for state in after['state']]
            require(actor['step'] == step and actor['arm'] == arm and
                    encoded(actor['action']) == encoded(actions[0]),
                    'Candidate action does not match retained telemetry')
            bank = [float(farm['money']) for farm in after['state'][0]['observation']['farms']]
            trace.update(encoded({'step': step, 'actions': actions, 'bank': bank}))
            if (step + 1) % configuration['turnsPerDay'] == 0 or step == 718:
                daily.append({'step': step, 'bank': bank})
            observation = copy.deepcopy(before['state'][0]['observation'])
            # These are the two exact injections in the original cloud-eval play.
            observation['step'] = step
            observation['remainingOverageTime'] = 0
            require(observation['player'] == 0, 'Wrong player observation')
            if 'observation' in actor:
                require(encoded(actor['observation']) == encoded(observation),
                        'Retained reached-state witness disagrees with pre-call input')
                telemetry_witnesses.append(step)
            inputs.append({'step': step, 'seat': 0, 'observation': observation,
                           'configuration': copy.deepcopy(configuration),
                           'expected_action': copy.deepcopy(actions[0])})
        terminal = frames[-1]['state']
        require(all(state['status'] == 'DONE' for state in terminal), 'Missing terminal frame')
        require([state['reward'] for state in terminal] == result['scores'], 'Terminal rewards differ')
        require(daily == result['daily_bank'], 'Retained daily bank sequence differs')
        trace.update(encoded([state['observation'] for state in terminal]))
        require(trace.hexdigest() == trace_sha, 'Original full trace digest differs')
        action_hash = digest(encoded([row['expected_action'] for row in inputs]))
        require(action_hash == result['telemetry']['emitted_actions_sha256'], 'Original action digest differs')
        experiment_bytes = z.read(str(Path(prefix).parent / 'EXPERIMENT.json'))
        experiment = json.loads(experiment_bytes)
        evaluator_source = z.read('source/tree/revenue/kaggriculture/cloud-eval/evaluate.py').decode()
        engine_match = re.search(r'^ENGINE_REF = [\"\']([^\"\']+)[\"\']', evaluator_source, re.MULTILINE)
        require(engine_match is not None, 'Missing exact original interpreter reference')
        source_map = {}
        for role, source in experiment['setup']['source_files'].items():
            matches = [name for name, meta in manifest.items() if meta['sha256'] == source['sha256']]
            require(bool(matches), 'Original source absent from retained package: ' + role)
            source_map[role] = {'sha256': source['sha256'], 'matching_archive_members': matches}
        source_map_bytes = json.dumps(source_map, indent=2, sort_keys=True).encode() + b'\n'
        payload = b''.join(encoded(row) + b'\n' for row in inputs)
        compressed = gzip.compress(payload, mtime=0)
        receipt = {
            'schema': 'titan.recorded-actor-inputs.v1',
            'origin': f'DELVE development9965001 seat0 {arm}, retained full frames; NOT WIDEFIELD9921001',
            'derivation': 'Aligned retained frames only; full original digest rehashed without interpreter execution.',
            'source_archive_sha256': ARCHIVE_SHA,
            'source_record_member': prefix + '.json',
            'source_record_sha256': digest(result_bytes),
            'source_frames_member': prefix + '.frames.jsonl.gz',
            'source_frames_sha256': digest(frames_bytes),
            'source_telemetry_sha256': digest(telemetry_bytes),
            'source_experiment_sha256': digest(experiment_bytes),
            'source_trace_sha256': trace_sha,
            'reconstructed_trace_sha256': trace.hexdigest(),
            'trace_verification_method': 'Rehash existing authored actions/banks and retained final observations, not a simulated reconstruction.',
            'input_jsonl_sha256': digest(payload),
            'output_file_sha256': digest(compressed),
            'source_map_sha256': digest(source_map_bytes),
            'observation_count': len(inputs), 'candidate_seat': 0,
            'original_candidate_seat': 0, 'view_is_original_candidate': True,
            'environment_seed_provenance_only': 9965001,
            'candidate_actor_rng_seed': 20260907, 'candidate_pythonhashseed': 20260907,
            'candidate': {'factory': 'funded_main.make_agent', 'factory_kwargs': {'funded': False},
                          'entry_member': 'runtime/revenue/kaggriculture/cloud-integration-differentials/funded_main.py',
                          'source_map_file': 'SOURCE-MAP.json',
                          'required_original_certificate_member': 'runtime/revenue/kaggriculture/cloud-integration-differentials/seed_funding_original.py',
                          'required_original_certificate_import_name': 'seed_funding.py'} if arm == 'control' else
                         {'factory': 'scheduler.SellScheduler', 'factory_kwargs': {},
                          'entry_member': 'source/tree/revenue/kaggriculture/cloud-titan-composition/vendor/sell/scheduler.py',
                          'source_map_file': 'SOURCE-MAP.json'},
            'opponent': {'label': 'intact Arlene', 'sha256': experiment['setup']['source_files']['opponent']['sha256']},
            'original_scores': result['scores'], 'original_python': experiment['python'],
            'engine_ref': engine_match.group(1),
            'engine_sha256': experiment['engine_sha256'],
            'evaluator_sha256': experiment['setup']['source_files']['evaluator']['sha256'],
            'normalizer_sha256': digest(Path(__file__).read_bytes()),
            'adapter_sha256': digest(Path(__file__).read_bytes()),
            'verified_source_members': len(manifest),
            'candidate_action_correspondences': len(telemetry),
            'retained_reached_state_correspondences': telemetry_witnesses,
            'candidate_internal_state_reconstructed': False,
            'policy_calls': 0, 'engine_interpreter_calls': 0, 'new_game_evaluations': 0,
            'consumer_instruction': ('Load the original mapped closure, initialize make_agent(funded=False) once, and replay the full ordered prefix comparing every expected action. Use recorded actor RNG/PYTHONHASHSEED. Do not use funded=True, current main or the changed certificate for an exact-source claim.' if arm == 'control' else 'Load the original mapped frozen-sell closure, initialize scheduler.SellScheduler() once and call its persistent act with the full prefix. Compare every expected action. Do not use current-main arm fixes or integrated source as the historical actor.'),
            'timing_scope': 'No new actor timing or hosted deadline result. Original measured telemetry remains in the unchanged DELVE package.'}
        output.mkdir(parents=True, exist_ok=True)
        (output/'candidate-inputs.jsonl.gz').write_bytes(compressed)
        (output/'SOURCE-MAP.json').write_bytes(source_map_bytes)
        (output/'ORIGINAL-RESULT.json').write_bytes(result_bytes)
        (output/'candidate-inputs-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
        return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--arm', choices=sorted(CELLS), default='control')
    args = parser.parse_args()
    print(json.dumps(derive(args.archive, args.output, args.arm), indent=2, sort_keys=True))
