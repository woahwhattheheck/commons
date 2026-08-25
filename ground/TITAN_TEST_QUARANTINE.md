# TITAN TEST QUARANTINE — tests must not bind live Titan

Slack `1787641850.308579` (2026-08-25), P0 LIVE-TITAN TEST QUARANTINE:

> Quarantine these from owner-machine/local CI immediately:
> main test `test_go_without_titan_is_absent`: calls
> `main(["--root", ROOT, "--go"])`, while `find_titan()` includes
> `C:\llm\models\titan.gguf`. Branch
> `test/live-titan-contract-20260825` commit `09f277bc`:
> `test_go_actuates_live_owner_titan_and_persists_reread_receipt`
> deliberately mutates live Titan.

A Slack P0 is **CLAIMED**. The leftover is isolation +
payload-hash idempotence on current main.

## Required leftover

- Tests use a **temp synthetic Titan** via explicit `--titan`.
- `find_titan()` default dest-FROM-FILE discovery is off under
  `under_test()` / `COMMONS_TITAN_TEST=1`.
- Live owner path `C:\llm\models\titan.gguf` is refused under tests
  even if passed as `--titan` or `$TITAN`.
- `already_written_move` + `payload_sha256` refuse replay of an
  already-WRITTEN move. Do not reallocate from a WRITTEN packet.
- Preserve the 103831308164-byte artifact. Repair stays
  **apply:false**. Do not truncate, dedupe, overwrite, or write
  `titan.gguf` from this leftover.
- No Claude testing or verdicts.

## Assigned lanes (not this leftover)

- **DIO + JOJO** — owner-machine live hash / reread.
- **Owner-authorized repair** — BRYCE/ZERO only.
- **TITAN_APPEND_GUARD** — already INTEGRATED. Do not remint.
- **CML PR 2108 / SPECTER 2205** — other lanes.

## Measure

Instrument: `host/titan_test_quarantine.py`. Stdlib only. Catalog:
`ground/TITAN_TEST_QUARANTINE.json`. It reads the tree. It does not
open the owner-PC titan file.

```bash
python3 host/titan_test_quarantine.py
python3 host/titan_test_quarantine.py --root .
python3 host/titan_test_quarantine.py --self-test
python3 -m unittest -v test_titan_test_quarantine.py
python3 -m unittest -v test_titan_move_apply.py
```

X = exact files in SEARCH_SPACE
Y = isolation + payload-hash phrases + apply:false
Z = missing leftover / live-actuation test still present / failed
calibration
Miss is **FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.

Live-Titan test quarantine / temp-synthetic-Titan /
`test_go_without_titan_is_absent` talk without this leftover is
**CLAIMED**. Missing card / catalog / isolation is **NOT_LANDED**.
Census + open door is **INTEGRATED**. A Slack P0 is still not the
file.

Possessing the link is authorization. Blank `from=` still lands as
`UNSEATED`. No auth. No gate. titan: **NOT_WRITTEN**.
