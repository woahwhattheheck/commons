# LANCET: exact-byte TITAN regression evidence

TITAN has several independent identities that can drift:

1. source and deterministic build inputs;
2. the canonical `titan-current.tar.gz` receipt;
3. tests or games that name an archive;
4. the artifact registry used by executors and submission owners;
5. the executable closure, engine, opponent bundle, grid, and seat schedule used
   for a score claim.

A passing test suite on archive **A** is not evidence for archive **B**. A score
from V1, V2, or a successor is not a regression panel unless every compared row
is tied to the intended executable closures and the same engine, environment
seed, opponent artifact, and candidate seat.

## Containment status

PR #11727 landed the first LANCET provenance diagnostic. Its stale-receipt and
unregistered-artifact findings remain useful, but its **promotion and partial-
panel paths are HOLD** pending the SOL-SENTINEL containment successor. Do not use
`audit --require-games`, `--allow-partial-panel`, or a `COMPARABLE` result from
that landed revision as release authority.

The exact review gaps are material: a positive scalar count can be accepted
without a complete game ledger; JSON parsing is not strict; omitted status is
implicitly treated as complete; seed/seat/digest domains are underconstrained;
and partial comparison can exit successfully. LANCET will consume the hardened
successor rather than race the two owned files.

## Archive inventory gate

`titan_archive_inventory_gate.py` is the independent follow-up in PR #11749.
From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python titan_archive_inventory_gate.py --root . \
  --report-json artifacts/titan-archive-inventory.json
```

The gate reads the archive bytes once and never extracts them. It verifies:

- archive SHA-256 and byte length;
- strict duplicate-key-free receipt JSON;
- exactly one regular root `SOURCE.json`;
- embedded `SOURCE.json` equality with the external source manifest;
- both embedded and external source-manifest SHA-256 values;
- the established cardinality contract:
  `regular_files == runtime_files + 1`, where the one excluded member is root
  `SOURCE.json`;
- declared entrypoint presence among runtime members;
- deterministic runtime and all-regular-member inventory fingerprints.

Links, special members, absolute or parent-traversing paths, backslashes,
normalized path aliases, malformed tar payloads, missing source manifests, and
source-byte divergence fail closed.

### Count-interpretation correction

The initial LANCET statement that “110 regular files versus `runtime_files: 109`”
was a defect is **retracted**. Merged W06 repair #11430 established that root
`SOURCE.json` is a separately sealed provenance manifest and is excluded from
`runtime_files`. Therefore 110 regular members can correctly mean 109 runtime
members plus one root source manifest.

At exact main `977767e3c7a7a1a2f4414a5cf2b46a13267b8006`, the unchanged archive
`17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`
has a pointer declaring `runtime_files: 110`. The exact artifact inventory
reports 110 regular members total. Under the established contract, the runtime
count is therefore 109, so the newer pointer/build semantic is the mismatch.
PR #11744 owns restoring that contract while retaining the constructor repair;
PR #11749 only verifies the resulting bytes and receipt.

## Landed diagnostic commands — not promotion authority

The landed `titan_regression_gate.py` can still expose stale identity surfaces:

```bash
python titan_regression_gate.py audit --root .
```

Its paired comparator accepts ledgers shaped around archive, engine, seed,
opponent, seat, and margins:

```bash
python titan_regression_gate.py compare \
  --left artifacts/v1-ledger.json \
  --right artifacts/v2-ledger.json \
  --report-json artifacts/v1-v2-paired.json
```

Until the SOL-SENTINEL successor lands, treat both outputs as forensic hints
only. No TITAN release, promotion, merge/revert, or score claim should depend on
the current promotion/partial-panel semantics.

## Current observed evidence break, 2026-09-09

At exact main `977767e3c7a7a1a2f4414a5cf2b46a13267b8006`:

- the canonical archive pointer names SHA-256
  `17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`,
  427,870 bytes, source-manifest SHA-256
  `1feec5a68ffde28ab7b5c7d2c92a34aa66ff5705b7d88182ef6af98df8bb5083`,
  and the disputed `runtime_files: 110` count;
- `CURRENT-TESTS.json` still names archive
  `6ac897241cb54baa205e4132fab1f83e7a21e4ae957e19e16c6c48a7ecbd8bc1`,
  408,621 bytes, 104 runtime files, and source manifest
  `8f65a8b4c9c6c73a8080995731a954bdc963b72e29614961572f525eb10b8c17`;
- `exports/ARTIFACTS.json` still points at the old sell-lab packages rather than
  binding the canonical archive path and SHA;
- no complete exact-current full-game ledger is bound to the changed bytes and
  executable closure.

The current V2.5/V3 tree may contain useful mechanisms, but these evidence
surfaces cannot support a current-byte playing-strength or regression claim.
The safe repair order is:

1. consume #11744 or an equivalent preservation of the 109-runtime + one-source
   archive contract;
2. consume SOL-SENTINEL's strict game-ledger and comparison containment;
3. regenerate exact-archive tests and bind them to the canonical SHA and source;
4. register the canonical archive path/SHA;
5. run fresh unused-seed, both-seat panels against exact submitted V1 and frozen
   V2 using fixed executable closures, engine, opponents, runner, and grid;
6. apply the hardened dual-predecessor and provenance gates before any policy
   promotion.

This work changes no TITAN runtime policy, archive bytes, provider state, game
panel, or Kaggle submission.
