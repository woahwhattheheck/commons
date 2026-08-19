FOUNDRY LISTEN — dry. Additive. No autofab. No titan write.

Button: host/muhl_foundry_listen_add.py
Ran:    python host/muhl_foundry_listen_add.py --dry
Exit:   0
Path:   default is --dry. Listen report only. nring2_fab not invoked.
        --surface not passed (bounded titan read skipped).

WHAT IT SURFACED
  mode:     DRY — listen only, no titan write
  foundry:  muhl_foundry_resident (resident speak register present)
  rings:    1024 two-way nring2_*  cells=32
  catalog (first 8):
    nring2_000  cells=32  senses=2
    nring2_001  cells=32  senses=2
    nring2_002  cells=32  senses=2
    nring2_003  cells=32  senses=2
    nring2_004  cells=32  senses=2
    nring2_005  cells=32  senses=2
    nring2_006  cells=32  senses=2
    nring2_007  cells=32  senses=2
    ... 1024 total

  size_question: not asked (need "<question>" <work_units> <settles>)
  later fab:     cannot size count/cells until the question is given
                 (nring2_fab is not in live host/; not invoked)

WHAT IT DID NOT DO
  No titan write.
  No autofab.
  No size_question inversion (no question / work_units / settles given).
  No --surface bounded read of foundry state or ring recv.
  Offsets came from C:/llm/models/titan_circuits.json only. Fail-closed path not hit.

LATER FAB WOULD NEED (not sized — question missing)
  count / cells / additional rings / electrons_per_ring_per_sense / clock_count
  stay unsized until:
    python host/muhl_foundry_listen_add.py --dry "<question>" <work_units> <settles>
