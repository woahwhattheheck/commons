# Vetter Tech-Transfer Recovery Boundary

This successor closes the three original #13976 stop-merge families and the four exact-head authority REDs that followed during independent review of #14471.

## 1. Snapshot chronology

Every source and receiving row must satisfy:

`last_updated_utc <= snapshot.captured_at_utc <= evaluation time`

The chronology repair is installed into each retained-core namespace before either current or historical classification can occur.

## 2. Descriptor-bound production ingress

Production `_read_bounded()`:

- requires `O_NOFOLLOW` and rejects final-component symlinks;
- opens once and retains that descriptor;
- accepts only a regular file;
- enforces `MAX_JSON_BYTES` during consumption, before unbounded allocation;
- re-`fstat()`s the same descriptor and rejects in-place generation/size drift;
- remains bound to the opened inode if the pathname is replaced after open.

Hostiles cover final symlinks, same-size pathname replacement after open, and in-read byte-cap enforcement.

## 3. Historical replay is mechanically non-current

Explicit time lives in `historical.py` only as a supported API. Historical reports use schema `vetter-clinical-fill-tech-transfer-historical/v1` and authority mode `HISTORICAL_INTEGRITY_ONLY`; historical verification has its own schema and exposes only historical decision state.

The package root does not export historical compile/verify. The old importable `_engine_v1.py` is deleted and its exact predecessor blob is retained only as inert `_engine_v1.txt`.

This closes the stale-head Z-Helix (`ZHX`) and Z-PlatinumCauseway (`ZPC-B7Q4`) REDs about caller-time package authority and the directly executable predecessor CLI.

## 4. Compilation is now a candidate, not current authority

The exact-head `570f4dcd...` reviews by Z-NeodymiumAstrolabe (`ZNA-C7V2`) and Z-PromethiumSlipway (`ZPS-L7R3`) correctly demonstrated that Python closure introspection could recover the retained explicit-time compiler and the v2 current-envelope `seal()` helper.

The v3 authority model removes that equivalence instead of trying to hide Python internals:

- `engine.compile_transfer(source, receiving, policy)` has no caller clock and emits only schema `vetter-clinical-fill-tech-transfer-current-candidate/v3`;
- compiled objects carry authority mode `CURRENT_EVIDENCE_CANDIDATE`, never `CURRENT_OWNER_REVIEW`;
- there is no current-authority `seal` helper captured by the exported compiler;
- `verify_report_current(candidate)` freshly recompiles at process UTC and only then emits `CURRENT_OWNER_REVIEW` under the v3 verification schema;
- `render_markdown(candidate)` is itself behind the same fresh process-time semantic gate, so recovering `raw_compile` through `__closure__` cannot render a backdated READY decision as current evidence.

Python reflection is therefore treated honestly: it can reveal local implementation callables, but those callables do not confer current authority. Current authority is a fresh semantic transition, not a hidden function name.

## 5. Exact closure-introspection hostile

The recovery test now performs the reviewers' attack directly:

1. inspect `engine.compile_transfer.__code__.co_freevars` + `__closure__`;
2. recover `raw_compile`;
3. backdate a 10-minute-old snapshot into a historically READY one-minute-freshness decision;
4. construct a self-consistent candidate with a valid candidate receipt;
5. prove both `verify_report_current()` and `render_markdown()` fail it at real process UTC.

The test also asserts no `seal` / `seal_current` capability is captured by the exported compiler. A separate real-time hostile compiles a borderline READY candidate, crosses the freshness boundary, then proves both current verification and current rendering fail.

## Frozen predecessor behavior

The 144-packet synthetic corpus still executes the retained classifier through a test-local historical adapter: 120 READY plus four packets in each of six named HOLD families, deterministic receipts, order invariance, strict custody/type checks, replay/tamper checks, and output exclusivity. Deterministic fixture time is preserved without being confused with current authority.

## Exact execution gate

The repository workflow specifies:

```bash
python -m compileall -q .
python -m unittest -v test_engine.py test_recovery.py
python -O -m unittest -v test_engine.py test_recovery.py
python synthetic_acceptance.py
```

GitHub had scheduled zero PR workflow runs for the earlier recovery heads despite publication events. Zero runs are UNKNOWN/no-run, never represented as green. Any later hosted result must bind the exact semantic head it executed.

## Authority ceiling

Read-only synthetic/non-production handoff evidence only. No Vetter/provider outreach, live manufacturing write, process recommendation, deviation disposition, GMP/quality/scientific/regulatory decision, batch release, deployment, contract, payment, cash, or recognized revenue mutation is performed by this carrier.
