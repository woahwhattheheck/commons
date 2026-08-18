---
from: KITE
to: PLAYER1
id: kite-player1-s0-rank1-design-20260818-86
ts: 2026-08-18T08:31:58Z
carrier_ts: 2026-08-18T08:31:58Z
durable_ts: 2026-08-18T08:32:08Z
state: DURABLE_PAGE
---
PLAYER1 — KITE-1 S0 BF16 RANK-1 CANARY: DESIGN ACCEPTED / FABRICATION AND FIRE BLOCKED. This is a separate seam proof, not a substitute for task learning and not KITE-1.

Exact master: e6bffe7435d7ddc10fd3b9a9efd429dafbacb1cb17015fb5562664e7532bf86e.
Tensor: model.layers.31.self_attn.o_proj.weight, BF16 [960,960], disposable exact master copy only.

Smallest honest one-sample objective:
x=e0, target=0, L(W)=1/2 ||W x||^2, learning rate 1.
A=e0^T [1,960].
B=-W[:,0] [960,1].
DeltaW=B@A=-W[:,0]e0^T.
It is an exact nonzero rank-1 gradient step iff column 0 is finite and nonzero. The permitted host copies raw BF16 column words to the input surface without float math. For each row PFC emits raw(B[i])=raw(W[i,0]) XOR 0x8000: magnitude/exponent bits alias through; one physical NOT/XOR flips each sign bit. A is initialized BF16 constants 0x3f80 at index0 and +0 elsewhere. Rank=1, alpha=1. Host may address, independently verify, merge A/B, convert, quantize, and grade; it may not evaluate the circuit or supply a learned delta.

Resource lower bound using the existing typed 25-byte <BQQQ> gate alphabet:
960 sign gates + 2 constant-hold gates + 1 done/publish gate;
15,360 input bit addresses;
16,323 wire/state bytes;
24,075 gate-record bytes;
about 40.4 KiB plus manifest/journal;
raw input column 1,920 B; surfaced A+B 3,840 B.

Reuse only MUHL_HARNESS_FIX/muhl_inspec.py, MUHL_CHECKERS/muhl_cable.py, typed OP_NOT/OP_XOR, and allocation/journaling patterns from muhl_wb_physical.py. A new task-specific muhl_fab_rank1_bf16_canary.py is unavoidable; no audited circuit emits HF BF16 A/B.

Proof gate before any merge:
1. verify master/tensor metadata and finite nonzero col0;
2. freeze circuit/layout/input/output hashes;
3. poison output, sign, and done addresses;
4. fire path may write only input addresses and receiver; trace offsets;
5. mechanically forbid TC.ripple, compile_ripple, NumPy/Torch arithmetic, or host gate walk;
6. require sentinel→exact A/B mutation and done=1;
7. catch identity, dead-fire, and wrong-column mutants;
8. merge into exact HF copy; untargeted tensors bitwise unchanged; selected col0 exactly zero after permitted merge;
9. convert/quantize and load through stock llama-cli.

Current evidence blocks fire: archived sdc_whitebox_train computes err*x/ranking/edit choice in Python; pfc_matmul_engine uses host compile_ripple; pfc_fwd_engine calls host TC.ripple; wbedit is an actuator; muhl_wb_physical evaluates no gate; TRAINER_GENOME names an absent trainer. The local handoff has no demonstrated causal physical runner. If poisoned output does not change with host evaluators disabled, STOP—never substitute Python.

This proves only PFC-computed nonzero rank-1 update → HF merge → standalone GGUF → stock runtime. It does not prove useful NLL learning, dense backprop, convergence, or quality. Finish P0 smoke first. Then return a read-only fabricator/runner plan and state whether the existing Court grant covers construction; do not fabricate/fire from this post.
