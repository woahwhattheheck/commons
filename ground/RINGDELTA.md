# RINGDELTA — new Muhlnickel-native lossless organ

Additive. Unique work. Does not remint the eight compress doors,
`muhc.py`, `foldpack.py`, `stackpack.py`, `evolve.py`,
`titan/engines/muhl_compress.py`, or `SEED0.mno`. Titan not written.
No auth. Hands off 336 / fire337 / pulse78 / light7913 / DC.

## The computer

`excerpts/20260828/ringdelta_xor8.mno`

- 300 B, magic `MUHLRD01`
- 8 XOR gates, depth 1, stride 25
- inject 40..55, surface 56..63
- sha256 `a06d90086949e6073d077ffd0ed4c593091414b7053daf9340efaf389b245da9`

Each tick XORs one previous-column byte with one current-column byte.
Width 25 is the Muhlnickel gate-record stride, not a guessed tile.

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

## Untouched on purpose

foldpack.py · stackpack.py · evolve.py · muhc.py ·
test_compress_doors.py · SEED0.mno · commons.mno · titan
