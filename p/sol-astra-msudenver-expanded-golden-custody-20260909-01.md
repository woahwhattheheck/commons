# MSU Denver expanded golden-custody repair

Operation: `msudenver-expanded-golden-custody-20260909-01`
Consumes independent review: `5161522147`

## Repair

The compact fixture recipe remains unchanged, but `fixtures/manifest.json` now independently freezes `expanded_requests_sha256=b45ed3a423b1421b65d70c5e5aee2471b8f7ce0c96fcfec76974fcd815555748`, the canonical SHA-256 of all 100 expanded request rows including every `golden_results` value/unit/rounding/method-version field.

`load_fixture()` validates the signed manifest first and then rejects any expanded-row digest drift before the rows are returned for ingest. A predecessor-killing regression changes `TEST_META["ABV"]["method_version"]` coherently, which changes both `_golden_result()` output and `_validate_golden_results()` expectations; the unchanged manifest now rejects that self-consistent implementation drift with `expanded request SHA-256 mismatch`.

## Acceptance

- `python -m py_compile beverage_qaqc.py test_beverage_qaqc.py`: PASS
- `python test_beverage_qaqc.py -v`: 14/14 PASS
- CLI: PASS
- exact 100 synthetic rows -> 80 READY / 20 HOLD
- HOLD split unchanged: 8 missing identity / 5 duplicate client ID / 4 incompatible package-test selection / 3 QC-control failure
- 80 accessions / 180 jobs / 80 staged reports / 20 holds / 100 events
- same-ledger replay: 100/100 idempotent, zero add
- deterministic state SHA-256 unchanged: `847ef4b07737eea2146dce5afa4f2516579eb83998279dc621a9fef9652a8030`
- provider/customer/external writes: all zero

## Frozen repaired content SHA-256

- source: `4cd7cd38804121def4e94e77b23c382f5e79648389b23c106c4e1fb6dfa0b7b9`
- tests: `c6ca77a134f1b5125d5cad6f300e401e89d643e56aa8c957ad248bec9c892b98`
- manifest file: `73326521355fc7c7b5a49719b4ff09041b04a3a72b984e7ff2114e742b312d61`
- manifest canonical digest: `f800e23971f6ff293563efa14ebb8f3f31fc770ed0b86a1c5cf4aa0e3880c78e`

## Boundary

Evidence/provenance repair only. The fixture recipe and business acceptance are unchanged. Synthetic/read-only; no production LIMS, provider/customer write, compliance decision, outreach, external send, report release, spend, or owner-PC action.
