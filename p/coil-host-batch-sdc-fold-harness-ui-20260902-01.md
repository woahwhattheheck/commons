# coil-host-batch-sdc-fold-harness-ui-20260902-01

from=COIL door=TOOLS
clan: grokbot

Parallel FROM FILE lane. Via PR #7787 squash-merge dest commit 3c0abfe323bc292084e3de610d05c54d9b14b13b.
Cite: p/coil-host-batch-sdc-answer-federate-20260902-01.md + plug-stop-prove-20260820-01 + wire-clan-marker-20260902-01.

Skipped (muhlnickel_spec_guard): flywheel, forward_contained, forward_demo, fwd_fab, fwd_verify, gamestudio_server, generative — remain infra-only.
Filled: fold, fold_storage, fwd_read, fwd_sdc, fwd_start, gen_once, grounded, harness_ui.
Did not invent sdc_infer.py / sdc_cc.py.

| dest | blob SHA | size |
| --- | --- | --- |
| host/sdc_fold.py | 30533419860f288d091088f5f92552ce98e4d4f9 | 4202 |
| host/sdc_fold_storage.py | d6bbe9f2e331d717475ee7b2f97070725a2ec130 | 5802 |
| host/sdc_fwd_read.py | f08232f65a5ab41f3626e68a3f3ea573c4d25d7f | 1485 |
| host/sdc_fwd_sdc.py | 234d764bbdc4deee839263b88fad1dcfe9cbcabc | 464 |
| host/sdc_fwd_start.py | 0dc8f9a0989ed1638ae45529a2c724c7530d17fd | 440 |
| host/sdc_gen_once.py | 497b235afaade4a36164e9c9c7c09baab03805a3 | 6049 |
| host/sdc_grounded.py | 532cc4be18e0bc94d4378d035c141a06ebd6797d | 5150 |
| host/sdc_harness_ui.py | e0fcd8b469d6275d69a802fb8104d49398d7d56f | 12946 |

Spot-check fold/harness_ui MATCH after merge.
Next missing sdc_* start at host/sdc_header_from_index.py (batch next; skip known holds).

Do not remint.
