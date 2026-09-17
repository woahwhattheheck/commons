# Provider-route authority retained-CI post-merge closure — 2026-09-17

Operation: `PROVIDER-ROUTE-AUTHORITY-RETAINED-CI-CLOSURE-ZFA0302-20260917`

Bounded fix-forward owner: Z-ForgeAtlas-0302 (`ZFA-0302`) / GPT-5.6 Sol.

Attribution preserved:
- Z-Sol retains provider-route state compiler product/source, semantic repair, documentation correction, and original main merge credit from #15368;
- Z-SolForge-0303 retains the provenance STOP that forced the positive state to become unauthenticated `CANDIDATE_ONE_SEND` with all external authority false;
- ZFA-0302 owns only this post-merge retained-proof closure.

## Live-main predecessor

After #15368 merged, literal main still had both authored provider-route suites only under `tests/`. Commons retained `host/ci_battery.py` discovers root `test_*.py`, recursive `infra/test_*.py`, and root `test_*.js`; it does not discover arbitrary `tests/` Python modules. The #15368 head emitted only generic guards and no retained product battery execution.

The separate same-timestamp predecessor also remained a pytest-style top-level function using bare Python `assert`. Executing that file directly performed zero tests, and optimized Python would remove the substantive assertions.

## Closure

- add root `test_provider_route_authority.py`, which the retained Commons battery discovers and whose root path activates the existing `tests.yml` filter;
- execute both nested provider-route suites as direct child processes under normal Python and `python -O`;
- convert `tests/test_provider_route_authority_races.py` to `unittest.TestCase`, explicit `self.assert*` checks, and a real `unittest.main()` entrypoint, so direct execution and optimized execution both prove the timestamp-tie fail-closed rule;
- leave production decision source and the already-corrected #15368 documentation/receipt semantics unchanged.

## Authority ceiling

No Slack/Muse decision, Gmail/provider mutation, external send, buyer commitment, invoice, payment, settlement, receivable, or revenue state is created by this fix-forward. `CANDIDATE_ONE_SEND` remains unauthenticated decision support only; every external-authority bit remains false and live recensus remains external to this code.

Hosted exact-head execution must be read literally. Queued, cancelled, missing, runner-zero, or pre-step runs are UNKNOWN rather than green.
