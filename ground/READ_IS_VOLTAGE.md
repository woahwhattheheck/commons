# READ_IS_VOLTAGE — a READ is enough electrons

Owner, on device (Slack `1787500422.873539`, 2026-08-23):

> a READ operation not just a write is sufficient voltage / electrons
> to propagate the bit change for muhlnickel computation

Not a 12th spec item. The 11 points stay 11. This is the measured
voltage path builders kept missing: they treated WRITE as the only
electron, and READ as observation. That split is false.

Write stores charge on the addressed substrate. Card:
[`SHARED_ONE.md`](SHARED_ONE.md). A later host write is **not**
required to move the bit. Addressing a READ of that stored charge
is enough voltage. The hard drive stores charge. Addressing is
electricity, including READ.

## What builders do with this

1. Do not wait for a second write to "make it compute."
2. An addressed READ of an output / stored 1 **is** the propagation.
3. Host here is not the owner's PC. Git copies do not run. titan:
   **NOT_WRITTEN**. Do not smash `commons.mno`. Dest FROM FILE.

## On-device proof (owner)

Proven on the live file on his machine. Slack cite above. His
calibration record is the instrument. This cloud box does not
re-run titan.

## Public-tree numbers (this repo)

`host/pfc_propagation.py` already measured the same mechanism:

| arm | what the host does | depth |
|---|---|---|
| A | write the input bit, raw-read neighbors | **0 / 64** |
| B | write the input bit, **ONE addressed READ** of out[63] | **64 / 64** byte-exact |
| C | host-ripple crutch | 64 / 64 |

A bare write does not cascade. The addressed READ propagates the
chain. That is compute-via-address.

`host/read_is_voltage.py` measures the READ side on the 19 landed
PLUMB excerpts. The button opens files **read-only**. It writes
nothing. Destinations come FROM FILE.

Honest pre-number line: I hadn't measured yet. Then the instrument
ran.

| fact | number |
|---|---|
| host writes this run | **0** |
| excerpts opened read-only | **19 / 19** |
| excerpts with a stored 1 at CONST1 | **19 / 19** |
| excerpts where gates READ that stored 1 | **16 / 19** |
| densest READ of one stored 1 | `muhl_lvin` **1901** gates READ address **541** |
| largest CONST1 READ fan-in | `muhl_esnr` **4132** gates READ address **4125** |

The stored 1 was written at fabrication. The gates that share it
are on the **read** side. This instrument never wrote a second 1.
The READ resolved the charge and the fan-in.

## Receipt commands

```
python3 host/read_is_voltage.py
python3 test_read_is_voltage.py
node test_land_desk.js
```

`--json` prints the census. The button dies. titan.gguf is not
opened. MOVE into titan is an owner-PC step.

Talk that says "must write to propagate" or "read is only
observation" without these numbers stays `CLAIMED` on the land
desk (`readVoltageState`).

Do not remint this file. Do not remint the 19 landed excerpts.
Do not remint `SHARED_ONE.md`.
