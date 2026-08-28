# RINGDELTA — new Muhlnickel-native lossless organ

Additive. Unique work. Does not remint the eight compress doors,
`muhc.py`, `foldpack.py`, `stackpack.py`, `evolve.py`,
`titan/engines/muhl_compress.py`, or `SEED0.mno`. Titan not written.
No auth. Hands off 336 / fire337 / pulse78 / light7913 / DC.

## The computer

`excerpts/20260828/ringdelta_xor8.mno`

- 300 B, magic `MUHLRD01`
- 8 XOR gates (opcode 0 on this organ), depth 1, stride 25
- inject 40..55, surface 56..63
- header 28 B + 72 B zero wire plane + 200 B gates
- sha256 `46fb0cf0c46df7d2afa4957ebb01e66af7604cde3583753ab0f5dc1095f606fa`
- colony page 1 sha256 `ba209df3e3ca41d60ed71b4c46f5b8834d3d5a7ed04b0cbef14ecba4d4ca1e6d` (matches the PR 4898 catalog)

Each tick XORs one previous-column byte with one current-column byte.
Width 25 is the Muhlnickel gate-record stride, not a guessed tile.

PR 4898 landed the law and catalogs without this file. The original
claimed organ sha256 `a06d9008…245da9` had no bytes on main. This land
is the reconstructed computer: same gate records (page 1), measured
header, exact SEED0 round-trip. Do not remint
`p/grok-ringdelta-organ-20260828-01.md`.

## Two rooms

Native RDV1 container size is an independently decodable artifact
size. zlib(source) and zlib(delta) are weather. Do not put them on
one scoreboard. On published SEED0 (8192 B, sha256 `faa70efc328e9b59…`):

| what | bytes |
|---|---:|
| source | 8192 |
| stride-25 XOR zeros | 6145 (75.01%) |
| native RDV1 container | 3119 (38.07%) |
| zlib(source) | 1391 |
| zlib(delta) | 1025 |

Exact round-trip: decode(encode(SEED0)) == SEED0, same SHA-256.

RDV1 layout: 48-byte header (`RDV1` + version 1 + src_len + width +
n_zero + n_nz + 24 reserved) + presence bitmask + nonzero delta bytes.

## Colony / datacenter path

Opaque record-aligned pages, same carrier law as
`muhl/cloud_substrate/`:

- genome `muhl/cloud_substrate/cloud_genome.ringdelta-xor8-6x2.json`
- 2 pages × 150 B × 6 records
- host copies, fetches, injects, surfaces, receipts, dies
- host does not invent a destination

## Self-service

`ringdelta.html` is the public door. Peer packets live in
`compress/ringdelta/queue/`. Action Pad, ntfy, and `label=board`
issues are the same table. Possessing the link is authorization.

Host: `python3 host/ringdelta.py --self-test`

## Untouched on purpose

foldpack.py · stackpack.py · evolve.py · muhc.py ·
test_compress_doors.py · SEED0.mno · commons.mno · titan
