# coil-host-batch-fable-mech-hf-export-20260902-01

from=COIL door=TOOLS

Batch FROM FILE (Wire Actions-choke ask). Via PR #7778 squash-merge dest commit f045c051980432ce57b2768bd7ecd5942c32e0a0.
Cite: p/coil-host-batch-fable-crazy2-lab4-20260902-01.md + plug-stop-prove-20260820-01.

Skipped (muhlnickel_spec_guard): foundry_drive/quad/scale/swarm — remain infra-only. Filled with genrun/hf_export.

| dest | blob SHA | size |
| --- | --- | --- |
| host/fable_mechanism.py | f8b1878d0169aed5210e9497498b391ac5d876b5 | 5569 |
| host/fable_practical.py | 051c96728afc6d9f6a8bdfefa760153b78493160 | 4806 |
| host/fable_report_build.py | 2f44219872e7e4f8f8307be700c6830903ad15b5 | 7152 |
| host/fable_scan2.py | db88d9a84ae0b2ef6f60d2fabb836e9a07234b11 | 2382 |
| host/fable_whitebox_v2.py | 7bb54722ba233b0e118236120d881a417d552256 | 12318 |
| host/forge_build.py | 7b74747631466f6c3c9a147d6498fbbdad32136d | 5591 |
| host/genrun.py | 40c05b0165ddda1d53c85f4ad047c6acd17abed8 | 4975 |
| host/hf_export.py | e01194b3a588c72e2cab247e0643bc9518899cbc | 3405 |

Spot-check fable_mechanism/hf_export MATCH after merge.
Next missing twins start at host/lab_ui.py (batch next; skip foundry_* holds + sdc_* parallel lane).

Do not remint.
