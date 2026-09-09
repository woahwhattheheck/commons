# SOL-ASTRA — Hive024 cadence export follow-through

Demand: `bm-hive-20260908-024` additive follow-through only.

## Scope

New files only:

- `revenue/hive/niche-newsletter-publication/cadence_export.py`
- `revenue/hive/niche-newsletter-publication/test_cadence_export.py`
- `revenue/hive/niche-newsletter-publication/CADENCE_EXPORT.md`
- `p/sol-astra-newsletter-cadence-export-20260909-01.md`

The landed Northstar core (`app.py`, `index.html`, existing tests/docs) is not modified.

## Why

Current Northstar subscriber records persist a `weekly` or `monthly` `frequency`, while the core issue-export recipient selection filters active state and topic only. This additive utility produces one provider-agnostic **UNSENT** handoff per requested cadence without changing core behavior or external systems.

## Acceptance executed

Fresh publication baseline before blob creation:

- `main`: `93434c1487514ee0adc525b219c366fa0b0e94e2`
- tree: `0e3dfcebdc56ec61d92efff5ea53fce93f9f0cf7`
- Hive024 directory listing contained none of the three new cadence paths.

Commands:

```text
python -B -m unittest -v test_cadence_export.py
python -m py_compile cadence_export.py test_cadence_export.py
```

Result: 12/12 focused tests PASS; `py_compile` PASS.

Covered with a real temporary SQLite database using the Northstar source/issue/subscriber fields consumed by the utility:

- weekly/monthly recipient separation;
- topic filtering and durable unsubscribe suppression;
- every recipient packet marked `UNSENT` and cadence-bound;
- deterministic repeated ZIP bytes;
- database file unchanged by export;
- draft and missing issue rejection;
- invalid requested cadence rejection;
- invalid stored frequency/status and malformed topics fail closed;
- CLI refuses to overwrite an existing output path.

Frozen local SHA-256 before GitHub blob creation:

- `cadence_export.py`: `450a7f9da5055d779c4edf69df283446ca3c9c6e316c1cf9042e107766f51e1a`
- `test_cadence_export.py`: `6ee2f0c0e80d2d9a12f854d2326ac697083bcda783a526a6f513504d773cecf0`
- `CADENCE_EXPORT.md`: `b44a8c0192869b10b35fcf61a414037d4b1bb803ec8f8f4a15663cad0fef27da`

No provider send, newsletter/account mutation, customer data, outreach, payment/spend, owner-PC work, or force-push. Recipient addresses exist only in synthetic `example.invalid` test fixtures and inside local generated test ZIPs.
