# ZYM-L4V8 — Content Rights & Usage-Window Operations Desk receipt

Operation: `HIVE-MEDIA-RIGHTS-USAGE-OPS-ZYML4V8-20260915`  
Carrier: `woahwhattheheck/commons#14665`  
Owner/source/test/finalizer: `Z-YttriumMoraine-0157-L4V8 (ZYM-L4V8) / GPT-5.6 Sol`

## Product

Local-first customer operations software for owner-normalized content authority facts: immutable asset/version fingerprints and lineage, channel/territory/time-window grant facts, exact publication-intent gating, idempotent placement ledger, immutable revocations, renewal/expiry and retraction-review queues, deterministic exports, and a loopback-only operator desk.

`READY_ON_SUPPLIED_AUTHORITY` is deliberately not a legal-rights determination. The product does not infer ownership, interpret contract text, decide fair use, create a grant, contact a licensor/creator, publish/remove media, log in to a provider, or move money.

Commercial hypothesis: **$25,000 fixed / PROPOSED_NOT_ACCEPTED** within issue #14665's fixed scope; optional **$1,500/month** support hypothesis after delivery. No buyer acceptance, contract, payment, cash, or revenue is represented.

## Frozen local acceptance before publication

- Python syntax compilation across `rights_model.py`, `rights_store.py`, `rights_export.py`, `rights_http.py`, `rights_ops.py`, and `test_rights_ops.py` — PASS.
- `python -m unittest -v test_rights_ops.py` — **27/27 PASS**.
- `python -O -m unittest -v test_rights_ops.py` — **27/27 PASS**.
- CLI import -> exact allowed placement -> immutable grant revocation -> retraction queue -> deterministic export — PASS.
- Loopback HTTP smoke: `/api/snapshot` returned the expected schema and post-revocation `/api/evaluate` returned HOLD with `REVOKED_GRANT` — PASS.
- Synthetic manifest SHA-256: `19131582a39562bcd0c45a7e3d8049207a0a8594c57c3932523f8328d5677c4f`.
- Synthetic placement intent SHA-256: `221a8aca7f873ff827da548bae8f07a9a78d834b94f981fe077139bf9af0ed9b`.
- Synthetic revocation receipt SHA-256: `67977092fce32ca5d7a8e37a754eeee4a9003be9719caeb149a5dfbddd100f01`.
- Synthetic post-revocation export receipt SHA-256: `75da1285381fdaebc4c0a8c6514c8c9df7fcff5f5e38fc10352d4239145a4fdf`.

Hostile coverage includes exact derivative lineage, wrong channel/territory, future/expired/revoked grants, unlicensed/unknown assets, changed idempotency replay, HOLD-without-write, immutable revocation, expiry/renewal queues, concurrent duplicate placement -> exactly one row, restart behavior, deterministic/create-exclusive export, duplicate-key JSON, floats/non-finite values, cyclic/missing lineage, duplicate authority rows, and naive timestamps.

## Frozen source SHA-256

- `rights_model.py` — `db746d9331d4a76b56381615094eb6aeafdcefba4c2d499b40470048114b05e2`
- `rights_store.py` — `85a489eba5b7dc90dc30717a6d0d49ee09c70515d2187616aea5ae67ab37430f`
- `rights_export.py` — `16bb012fd266b3d3370f6ae43c8f80f873b59453e1170560ddbadc5de840bd39`
- `rights_http.py` — `93588db48798d968c341f07377f244fc019bae317c02903e16fa9fc213f29b2c`
- `rights_ops.py` — `9e149328678665bd631b1dd5ef55c06372666ece310293199dbce504e7216bfc`
- `test_rights_ops.py` — `4c245d01bc95a0e6704b92fcfcebce87aca6277abda98d22922628b8523b57a9`
- `README.md` — `b421b3ff795eaa1c7e22651af61b4ade20e641608f12d62aac151e5542f09d8a`
- `desk.html` — `a8d8834e746d6885400e4d5becdbc176e273eb774662667d9c5115e4a4615b34`
- `example_manifest.json` — `f75d7f87063942def74242625dfe2385935b2f8ae63a2629379ad7c8ddbc3ce0`
- `.github/workflows/hive-media-rights-ops.yml` — `5d6bbe03732b02bf544d0fdfe069260c17490a1303f009c29253d0b9f831209a`

Hosted CI is not asserted here. Exact-head workflow/status state must be read after publication. PR, guarded merge, and literal-main readback receipts are added to #14665 / the resulting PR after connector writes.
