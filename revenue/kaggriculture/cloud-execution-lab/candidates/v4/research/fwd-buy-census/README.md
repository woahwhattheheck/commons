# FWD-BUY census: consume the earlier repair, do not fork it

This directory preserves the earlier completed decoder donor 9946e012fc8ca2d36dbe93cc6d0d128910a9d08d byte-for-byte as decoder.py. It supersedes the faulty 83942caaf64e8a4e205d48ac26e734bdb8554bbe for structural counts. Original correction ownership remains with the peer's build-demand claim 1789176997.726059 and completion 1789177458.789699; ASTRA/DELTA contributes only the independent check and this integration.

The repair recognizes official SELL barriers, caps evidence to the first ten RAW market slots without compacting placeholders, and conservatively vetoes economic companions in the buy's source callback. Structural candidates do not prove cash affordability, shed capacity, unit-service dependencies, or opponent benefit.

```sh
python decoder.py --self-test
python -O decoder.py --self-test
python check_fwd_census_engine_contract.py decoder.py --engine /absolute/path/kaggriculture.py -v
python -O check_fwd_census_engine_contract.py decoder.py --engine /absolute/path/kaggriculture.py -v
python decoder.py /absolute/path/r01_tapes.py --output census.json
```

The first four commands were executed: self-tests pass; 24 independent checks pass in normal and optimized mode. Of these, three execute exact engine grammar/order functions with economic commits stubbed, not full game economics. Against exact predecessor 83942, normal mode reports 12 failures + 2 errors and optimized mode reports 13 failures + 2 errors, demonstrating the tests detect the repaired defects and optimized false-green behavior.

The final full 13x719 census command was NOT executed in this session: the exact a43289b9cc5e34a2481fddf652762a7d92f427ef tape bytes were not materialized. Do not infer census totals or activation frequency from synthetic tests. Engine pin is 3c202c7ee921da239356789e266b694635103fc4. The check is named check_ rather than test_ because it requires explicit CLI inputs and must not be automatically imported by generic test discovery.

This is read-only research support under canonical main:candidates/v4/research/, not a runtime key. The companion ../cf1-cow-fert-salvage/RECEIPT.json records exact source hashes and executed outcomes. Existing Slack receipt: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789177830697039
