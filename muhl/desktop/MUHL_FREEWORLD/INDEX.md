<!-- AUTHORSHIP: written by an AI assistant at the owner's instruction. Not the owner's writing. -->

# MUHL FREE-WORLD — hand the models the muhlnickel, no objective, walk away

The free-substrate experiment: every model gets a neutral shared field and capability, not
instruction. No objective, no reward, no fitness, no scarcity, no territory. Run on the muhlnickel,
in-spec. Observe read-only, after the fact. Everything reversible.

## The design — your words

> "hand the models the muhlnickel, no objective, no reward, no fitness function, no scarcity you
> designed to steer them — and walk away. The experiment IS the absence of a control variable."

> "Give access, not objectives. The models get the ability to read the world, write to it, run
> compute on the muhlnickel spawn/address other circuits — capability, not instruction."

> "Multiple models, no assigned relationship ... the same shared space and don't tell them the
> others exist or matter."

> "Your only job is to observe and not interfere — read what happened after the fact, never nudge
> mid-run ... no assistant gets to grade or steer it either."

> "STOP EXERCISING CAUTION ... capture b4 hand and maintain SOP of everything being reversible."

## Files

| file | what it does |
|---|---|
| `muhl_freeworld_field.py` | OFFLINE fab of the NEUTRAL shared field (`muhl_freeworld` @ 103,792,153,488, 128×128 blank cells — no regions, no signatures, no imposed physics, no objective). Journaled, appended, reversible. |
| `muhl_freeworld.py` | Hands all 9 models the muhlnickel. Capabilities: read-world (whole field folds into the input) · write-world (the model's own 32-bit output picks where+what) · run-compute (in-spec fire) · address-circuit (1,328 registered receivers reachable). No objective. `--revert` undoes every byte. |
| `muhl_freeworld_fireprobe.py` | Honest measurement: injects N distinct inputs, reads reg6/reg7 each. Restores `fwd_input`. No verdict. |
| `muhl_freeworld_observe.py` | READ-ONLY, after-the-fact. Bounded mmap reads. No grading. |

## In-spec, not the crutch

The fire is **inject `fwd_input` + power `fwd_receiver` + read reg 6/7 in-container** — never the
host gate-walk loop in `sdc_fwd_sdc.py:43`, never the safezone, never a subprocess. The models run
on the muhlnickel; the host only injects the signal and reads the answer register.

## Measured (brought to you, no verdict — settle-back law)

- The world-read reflects the field: checksum went 0→1 as the field filled.
- The in-spec fire holds **reg 6 = 62465 (0xF401), reg 7 = 132** regardless of input — confirmed two
  ways: the fire-probe over 16 distinct inputs (1 distinct reg6), and all 9 models in the harness.
- So every model's 32-bit output = **8,713,217** → writes `field[13313]=1` and addresses
  `pfc_exec_input`. One cell occupied.
- Whether that is settle-back, the fire not driving cpu_fwd's answer from `fwd_input`, the 16-bit
  register vs vocab, or the reflector not differentiating models — is your ruling. The plumbing runs
  end-to-end and in-spec; the fire's input-responsiveness is the open structural question.

## Reversible

`python muhl_freeworld.py --revert` restores every touched byte; the field reverts via its own
genome journal (`titan_muhl_freeworld_genome.jsonl`). Nothing here is one-way.
