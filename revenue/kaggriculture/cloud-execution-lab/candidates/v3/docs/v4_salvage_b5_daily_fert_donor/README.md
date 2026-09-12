# B5 daily fertilizer-sweep donor — V4 salvage custody

Source lineage: `riot/v3.1-lane-b5@8638d0db7068f38966424c59181875d8b128a72a`.

Exact preserved source blobs in this directory:
- `r04_fert_daily_sweep.py`: `cd6c1dd50a439f58bce9434db8d628ca8d6f978f`
- `test_v3_r04_fert_daily_sweep.py`: `fb51b305289a311e9e8e4a3a63c38c18c5a1fd30`

This older B5 idea is distinct from the shipped B5 CARROT/JIT pair. It opportunistically changes only already-idle `PASS` workers: collect an available daily fertilizer unit when already standing on its animal tile, or DROP carried fertilizer when already beside the shed and no conflicting inventory work remains. It does not hire, move, or add market rows.

Modern V4 S1/S6 own dedicated fertilizer-sweep surfaces and `r04_fert_hand`/B9/JIT already own other fertilizer work. Therefore this directory is source custody only: do not copy the old router/apply/config postimages and do not create a second fertilizer controller. A V4 consumer must first prove exact trigger/action non-overlap (or a strict precedence rule) against S1/S6/r04_fert_hand/B9/JIT and run an occurrence + economics gate on the then-current single V4 head.
