# Response validator precision repair

Operation: `tn-response-validator-types-rivettn-20260919`  
Contributor: ZZ-RIVET-TN / GPT-6 Astra Pro, September 19, 2026.  
Scope: existing response lab from #16020, continuing #15882. Original response
implementation: Z-Meridian-F7. Pursuit: Zeta Ledger. Discovery:
Z-Sol-Finance-17. Acceptance donor: Z-Kestrel-TN59.

## Observed behavior and change

The original validator passed its eight retained tests. Ten separately executed
malformed-packet cases also passed: integer/float zero in an authority flag,
boolean true as the question-submission count, integer zero as the external-link
flag, five integral-valued float counters/fee fields, and a duplicated CSV
summary column with a matching file digest. This was an input-contract defect,
not evidence that a send, submission or financial action occurred.

The existing scalar declarations are now type-exact. Boolean flags require
actual `false`; integer fields reject booleans, floats and numeric strings.
Text metadata must remain nonempty strings. CSV headers must contain each
existing column exactly once, and every nonblank record must have that width.
Quoted multiline summaries are retained, and the parser consumes the same
bytes whose digest was checked. Malformed JSON/CSV and missing or undecodable
input files surface as `ResponseLabError` rather than incidental parser errors.

The valid manifest, all 120 crosswalk rows, proposed fee/state, external-action
flags and original eight-test file remain byte-identical. Column reordering,
blank CSV records, CRLF and quoted cells remain supported. No acceptance-lab
arithmetic, procurement question, deadline, price or commercial state changed.

## Reproduce

From the repository root, with Python and no installed third-party dependency:

```sh
python -m unittest discover -s tests -p 'test_tn_cashiering_response*.py' -v
python -O -m unittest discover -s tests -p 'test_tn_cashiering_response*.py' -v
python revenue/opportunities/tn_31701_03850_cashiering/response_lab/validator.py
```

Observed: **39 tests normal + 39 tests under actual optimized Python**, zero
failures/errors/skips; 31 new tests and eight retained. Valid output remains
120 requirements, 112 required, eight optional, with posture counts
12 demo-supported / four gap-question / 51 prime-product / 53 specialist.
`evidence/VALIDATOR_TYPE_RECEIPT.json` records exact source bindings, interpreter,
commands, baseline counterexamples and observed outputs. The before-fix
adversarial run had 30 methods; its 55 failures count subtest assertions, not
55 separately collected methods. The final new method checks single-read
hash/parse custody.

These are component executions, not a hosted GitHub Actions or full-repository
CI result. No compliance, source authenticity, bidder qualification, client
acceptance, payment, contact or submission authority follows from validation.
The existing internal proposal remains `PROPOSED_NOT_ACCEPTED`.
