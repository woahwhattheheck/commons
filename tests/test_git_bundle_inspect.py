"""Real Git interoperability plus deterministic malformed-input/delta coverage."""
import base64
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

import pytest

MODULE = Path(__file__).resolve().parents[1]/'host/git_bundle_inspect.py'
spec = importlib.util.spec_from_file_location('git_bundle_inspect_under_test', MODULE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def size(value):
    result = bytearray()
    while True:
        part = value & 127
        value >>= 7
        result.append(part | (128 if value else 0))
        if not value:
            return bytes(result)


def packed(kind, data, prefix=b'', declared=None):
    length = len(data) if declared is None else declared
    result = bytearray([(kind << 4) | (length & 15)])
    length >>= 4
    if length:
        result[0] |= 128
    while length:
        result.append((length & 127) | (128 if length >> 7 else 0))
        length >>= 7
    return bytes(result) + prefix + zlib.compress(data)


def bundle(items, algorithm='sha1', prerequisites=(), capabilities=(), version=None, pack_version=2, count=None, tail=b''):
    version = version or (3 if algorithm == 'sha256' else 2)
    header = f'# v{version} git bundle\n'.encode()
    if version == 3:
        header += f'@object-format={algorithm}\n'.encode()
    header += b''.join(b'@'+line+b'\n' for line in capabilities)
    header += b''.join(b'-'+oid.encode()+b' fixture prerequisite\n' for oid in prerequisites)
    header += b'0'*(64 if algorithm == 'sha256' else 40) + b' refs/heads/fixture\n\n'
    payload = b'PACK'+struct.pack('>II', pack_version, len(items) if count is None else count)+b''.join(items)+tail
    return header+payload+hashlib.new(algorithm,payload).digest()


def delta(base, result):
    assert len(result) < 128
    return size(len(base))+size(len(result))+bytes([len(result)])+result


def git(root, *arguments, data=None):
    return subprocess.run(['git', '-C', str(root), *arguments], input=data,
                          capture_output=True, check=True, timeout=30).stdout


@pytest.mark.parametrize('algorithm', ['sha1', 'sha256'])
def test_real_full_bundle_matches_every_git_object(tmp_path, algorithm):
    repo = tmp_path/'repo'; repo.mkdir()
    git(repo, 'init', '-q', '--object-format='+algorithm)
    git(repo, 'config', 'user.name', 'Fixture')
    git(repo, 'config', 'user.email', 'fixture@invalid.example')
    for index in range(5):
        (repo/'data.txt').write_text('shared data\n'*500+f'change {index}\n')
        (repo/f'new-{index}.txt').write_text(f'new {index}\n')
        git(repo, 'add', '.')
        git(repo, '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', f'fixture {index}')
    archive = tmp_path/'full.bundle'
    git(repo, 'bundle', 'create', str(archive), '--all')
    manifest, objects = module.inspect_bundle(archive.read_bytes())
    assert manifest['unresolved_pack_objects'] == 0
    assert manifest['resolved_pack_objects'] == len(objects)
    assert manifest['object_format'] == algorithm
    assert manifest['git_restore_verified'] is False
    for oid, (kind, payload) in objects.items():
        assert git(repo, 'cat-file', kind, oid) == payload
        assert git(repo, 'hash-object', '-t', kind, '--stdin', data=payload).decode().strip() == oid
    assert any(row['representation'].endswith('delta') for row in manifest['objects'])


@pytest.mark.parametrize('algorithm', ['sha1', 'sha256'])
def test_real_thin_bundle_recovers_new_blob_and_records_prerequisite(tmp_path, algorithm):
    repo = tmp_path/'repo'; repo.mkdir()
    git(repo, 'init', '-q', '--object-format='+algorithm)
    git(repo, 'config', 'user.name', 'Fixture')
    git(repo, 'config', 'user.email', 'fixture@invalid.example')
    (repo/'old.txt').write_text('line of stable content\n'*500)
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'base')
    base = git(repo, 'rev-parse', 'HEAD').decode().strip()
    (repo/'old.txt').write_text('line of stable content\n'*500+'small edit\n')
    unique = b'new independent payload\x00\xff'
    (repo/'new.bin').write_bytes(unique)
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'candidate')
    archive = tmp_path/'thin.bundle'
    git(repo, 'bundle', 'create', str(archive), 'HEAD', '^'+base)
    manifest, objects = module.inspect_bundle(archive.read_bytes())
    assert manifest['prerequisites'][0]['oid'] == base
    assert manifest['status'] == 'PARTIAL_THIN_PACK'
    assert manifest['unresolved_pack_objects'] > 0
    assert any(data == unique for _, data in objects.values())
    supplied = []
    for row in manifest['objects']:
        if row['resolved'] or 'base_oid' not in row:
            continue
        oid = row['base_oid']
        kind = git(repo, 'cat-file', '-t', oid).decode().strip()
        supplied.append((kind, git(repo, 'cat-file', kind, oid)))
    recovered, all_objects = module.inspect_bundle(archive.read_bytes(), bases=tuple(supplied))
    assert recovered['unresolved_pack_objects'] == 0
    for oid, (kind, data) in all_objects.items():
        assert git(repo, 'cat-file', kind, oid) == data


@pytest.mark.parametrize('algorithm', ['sha1', 'sha256'])
def test_forward_reference_and_chained_deltas(algorithm):
    original, second, third = b'first', b'second', b'third'
    id1 = module.object_id('blob', original, algorithm)
    id2 = module.object_id('blob', second, algorithm)
    data = bundle([packed(7, delta(second, third), bytes.fromhex(id2)),
                   packed(7, delta(original, second), bytes.fromhex(id1)),
                   packed(3, original)], algorithm)
    manifest, objects = module.inspect_bundle(data)
    assert manifest['resolved_pack_objects'] == 3
    assert {data for _, data in objects.values()} == {original, second, third}


def test_offset_delta_and_duplicate_object():
    first = packed(3, b'abc')
    data = bundle([first, packed(6, delta(b'abc', b'xyz'), bytes([len(first)])), packed(3, b'abc')])
    manifest, objects = module.inspect_bundle(data)
    assert manifest['resolved_pack_objects'] == 3 and len(objects) == 2
    assert objects[module.object_id('blob', b'xyz', 'sha1')] == ('blob', b'xyz')


def test_supplied_base_is_verified_by_its_derived_id():
    oid = module.object_id('blob', b'old', 'sha1')
    data = bundle([packed(7, delta(b'old', b'new'), bytes.fromhex(oid))])
    partial, objects = module.inspect_bundle(data, bases=(('blob', b'wrong'),))
    assert partial['unresolved_pack_objects'] == 1 and objects == {}
    complete, objects = module.inspect_bundle(data, bases=(('blob', b'old'),))
    assert complete['resolved_pack_objects'] == 1
    assert list(objects.values()) == [('blob', b'new')]


def test_delta_copy_and_default_64k_copy():
    assert module.apply_delta(b'abcdef', b'\x06\x05\x91\x01\x03\x02XY', 100) == b'bcdXY'
    base = bytes(range(256))*256
    assert module.apply_delta(base, size(len(base))+size(len(base))+b'\x80', 65536) == base


@pytest.mark.parametrize('bad', [b'', b'\x04\x01\x01x', b'\x03\x01\x00', b'\x03\x04\x91\x01\x04',
                                b'\x03\x02\x03abc', b'\x03\x02\x02x', b'\x03\x02\x01x', b'\x03\x01\x81'])
def test_malformed_delta_is_rejected(bad):
    with pytest.raises(module.BundleError):
        module.apply_delta(b'abc', bad, 100)


@pytest.mark.parametrize('change', [
    lambda x: b'not a bundle',
    lambda x: x[:-1],
    lambda x: x[:-20]+b'x'*20,
    lambda x: x.replace(b'# v2', b'# v1', 1),
    lambda x: x.replace(b'0'*40, b'z'*40, 1),
    lambda x: x.replace(b'refs/heads/fixture', b'bad name', 1),
])
def test_bad_header_or_checksum_is_rejected(change):
    with pytest.raises(module.BundleError):
        module.inspect_bundle(change(bundle([packed(3, b'hello')])) )


@pytest.mark.parametrize('data', [
    bundle([packed(0, b'')]), bundle([packed(5, b'')]),
    bundle([packed(3, b'abc', declared=2)]), bundle([packed(3, b'abc', declared=4)]),
    bundle([packed(3, b'abc')], count=0), bundle([], count=1),
    bundle([packed(3, b'abc')], tail=b'extra'),
    bundle([packed(3, b'abc')], pack_version=1),
    bundle([packed(6, b'anything', b'\x00')]),
    bundle([packed(6, b'anything', b'\x01')]),
    bundle([b'\x33invalid-zlib']),
])
def test_malformed_pack_with_valid_checksum_is_rejected(data):
    with pytest.raises(module.BundleError):
        module.inspect_bundle(data)


@pytest.mark.parametrize('limit', [
    replace(module.Limits(), input_bytes=1), replace(module.Limits(), header_bytes=10),
    replace(module.Limits(), object_bytes=2), replace(module.Limits(), total_bytes=2),
    replace(module.Limits(), objects=0),
])
def test_resource_limits(limit):
    with pytest.raises(module.BundleError):
        module.inspect_bundle(bundle([packed(3, b'hello')]), limits=limit)


def test_delta_expansion_limit():
    base = b'x'*100
    oid = module.object_id('blob', base, 'sha1')
    data = bundle([packed(7, size(100)+size(100)+b'\x90\x64', bytes.fromhex(oid))])
    with pytest.raises(module.BundleError, match='total limit'):
        module.inspect_bundle(data, bases=(('blob', base),), limits=replace(module.Limits(), total_bytes=150))


def test_unknown_capability_and_promisor_metadata():
    with pytest.raises(module.BundleError, match='Unsupported required'):
        module.inspect_bundle(bundle([], version=3, capabilities=(b'mystery=1',)))
    manifest, _ = module.inspect_bundle(bundle([], version=3, capabilities=(b'filter=blob:none',)))
    assert manifest['capabilities']['filter'] == 'blob:none'
    assert not manifest['git_restore_verified']


def test_cli_base64_export_and_no_overwrite(tmp_path, capsys):
    raw = bundle([packed(3, b'hello\x00world')])
    input_file = tmp_path/'input.b64'; input_file.write_bytes(base64.encodebytes(raw))
    output = tmp_path/'output'
    arguments = [str(input_file), '--base64', '--sha256', hashlib.sha256(raw).hexdigest(), '--output', str(output)]
    assert module.main(arguments) == 0
    manifest = json.loads((output/'manifest.json').read_text())
    oid = manifest['objects'][0]['oid']
    assert (output/'objects'/f'{oid}.blob').read_bytes() == b'hello\x00world'
    assert module.main(arguments) == 2
    assert (output/'objects'/f'{oid}.blob').read_bytes() == b'hello\x00world'
    assert module.main([str(input_file), '--base64', '--sha256', '0'*64]) == 2
    input_file.write_bytes(b'%%%')
    assert module.main([str(input_file), '--base64']) == 2


def test_cli_partial_exit_still_exports_available_object(tmp_path, capsys):
    raw = bundle([packed(3, b'available'), packed(7, delta(b'old', b'new'), bytes.fromhex(module.object_id('blob', b'old', 'sha1')))])
    path = tmp_path/'thin.bundle'; path.write_bytes(raw)
    output = tmp_path/'partial'
    assert module.main([str(path), '--fail-on-unresolved', '--output', str(output)]) == 3
    assert len(list((output/'objects').iterdir())) == 1
    assert json.loads((output/'manifest.json').read_text())['unresolved_pack_objects'] == 1


def test_large_incompressible_payload_crosses_inflater_chunks():
    payload = b''.join(hashlib.sha256(str(i).encode()).digest() for i in range(3000))
    manifest, objects = module.inspect_bundle(bundle([packed(3, payload), packed(3, b'tail')]))
    assert manifest['resolved_pack_objects'] == 2
    assert objects[module.object_id('blob', payload, 'sha1')][1] == payload


def distance(value):
    """Encode Git's biased big-endian OFS_DELTA distance."""
    result = bytearray([value & 127])
    while value >> 7:
        value = (value >> 7) - 1
        result.append(128 | (value & 127))
    return bytes(reversed(result))


@pytest.mark.parametrize('payload_length', [257, 32768, 200000])
def test_multibyte_offset_delta_and_chained_offsets(payload_length):
    payload = b''.join(hashlib.sha256(str(i).encode()).digest() for i in range((payload_length + 31)//32))[:payload_length]
    first = packed(3, payload)
    middle = packed(6, delta(payload, b'middle'), distance(len(first)))
    last = packed(6, delta(b'middle', b'final'), distance(len(middle)))
    assert len(distance(len(first))) > 1
    manifest, objects = module.inspect_bundle(bundle([first, middle, last]))
    assert manifest['resolved_pack_objects'] == 3
    assert objects[module.object_id('blob', b'final', 'sha1')] == ('blob', b'final')


@pytest.mark.parametrize('bad', [-1, True, 1.2, '20', sys.maxsize])
def test_programmatic_limits_reject_invalid_values(bad):
    with pytest.raises(module.BundleError):
        module.Limits(object_bytes=bad)


def test_cli_aggregate_supplied_base_limit_is_checked_while_loading(tmp_path, monkeypatch, capsys):
    archive = tmp_path/'fixture.bundle'; archive.write_bytes(bundle([]))
    supplied = tmp_path/'base'; supplied.write_bytes(b'x' * (700 * 1024))
    reads = []
    original = module._read
    def recorded(path, maximum):
        reads.append((path, maximum))
        return original(path, maximum)
    monkeypatch.setattr(module, '_read', recorded)
    assert module.main([str(archive), '--max-total-mib', '1',
                        '--base-object', f'blob:{supplied}', '--base-object', f'blob:{supplied}']) == 2
    assert reads[-1] == (supplied, 1024 * 1024 - 700 * 1024)


def test_cli_invalid_huge_limit_returns_controlled_error(tmp_path, capsys):
    archive = tmp_path/'fixture.bundle'; archive.write_bytes(bundle([]))
    assert module.main([str(archive), '--max-input-mib', str(sys.maxsize)]) == 2
    assert 'platform-sized' in capsys.readouterr().err


def test_pack_version_three_and_tag_payload():
    payload = b'object '+b'0'*40+b'\ntype blob\ntag fixture\n\nfixture annotation\n'
    manifest, objects = module.inspect_bundle(bundle([packed(4, payload)], pack_version=3))
    assert manifest['pack_version'] == 3
    assert list(objects.values()) == [('tag', payload)]
    assert manifest['git_restore_verified'] is False


def test_every_truncated_prefix_fails_without_successful_export():
    raw = bundle([packed(3, b'data')])
    for count in range(len(raw)):
        with pytest.raises(module.BundleError):
            module.inspect_bundle(raw[:count])


def test_large_compressed_payload_cannot_hide_declared_size_overrun():
    raw = bundle([packed(3, b'x' * (2 * 1024 * 1024), declared=1)])
    with pytest.raises(module.BundleError, match='declared size'):
        module.inspect_bundle(raw)
