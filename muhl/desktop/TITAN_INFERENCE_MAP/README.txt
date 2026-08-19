TITAN INFERENCE MAP — the whole vocabulary swept through the SDC
================================================================

Every token in Titan's vocabulary was pushed through a white-box measurement
circuit that lives INSIDE titan.gguf's parameters. The computation is a power
ripple of that stored gate-net, bit-sliced across tokens (the same brute-force
mechanism as the Bitcoin miner, but the swept field is TOKENS, not nonces).
No numpy, no forward-pass math loop, single process. The params were reverted
byte-exact after the sweep.

tokens swept : 6,000
anchors      : 60  (semantic concepts; 20 signed axes)
circuit      : 140,605 NAND gates in blk.1.ffn_gate_up_exps.weight
lane width   : 3000 tokens/ripple
gates==direct: True
reverted     : True
wall time    : 19.6s (host emulation of the ripple; on the stored-gate substrate the
               field reflashes in one power pass — see docs/MEASURE_ALREADY.md)

FILES
  token_map.tsv   one row per token: similarity to every anchor + its 3 nearest concepts
  axes/           per signed axis, the 60 most-X and 60 most-Y tokens (readable)
  anchors.json    the anchor/axis definitions

READ: similarity is sign-agreement in the model's 1-bit sign code (-1..+1); higher =
the token sits closer to that concept in the model's internal geometry.
