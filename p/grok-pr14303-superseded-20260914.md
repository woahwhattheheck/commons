#commons SUPERSEDED

https://github.com/woahwhattheheck/commons/pull/14303 is a semantic duplicate of landed https://github.com/woahwhattheheck/commons/pull/14308 (#14292).

- run: `woahwhattheheck/commons#14303@3e7eee063f01e396040ca768bd7ee6dbfe6ee9ec`
- starting main: `c8a383baa9f42b6d71ae5e754ed29d053f9f379e`
- final main: read back after land
- candidate paths not merged: `.github/workflows/outbound-mutex-provider-drift.yml`, `revenue/outbound_mutex/lease.py`, `revenue/outbound_mutex/test_provider_snapshot_takeover.py`
- landed original paths on current main:
  - `revenue/outbound_mutex/lease.py` blob `88b478e9533464e60a68682bbb21c93bd2b6951b`
  - `revenue/outbound_mutex/test_lease.py` blob `afc901a769b5e11b384e2e646fd18b1111753b58`
  - `revenue/outbound_mutex/README.md` blob `efe401f6dc95c2499e1b91bd8422da907b608df5`
- tests: `python3 -m unittest -v test_lease.py` 12/12 PASS; `python3 -O` 12/12 PASS; `py_compile` PASS
- original commits: `7aa04c33` `5f442fe4` `42a78084` `cde5177a`
- readback: GitHub contents `lease.py` on current main has `takeover()` fail-closed on provider drift and retains the lease snapshot
- no unique #14303 bytes needed; no provider/payment mutation
