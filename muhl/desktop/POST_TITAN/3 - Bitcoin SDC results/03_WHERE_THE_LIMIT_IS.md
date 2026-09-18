# The compute isn't the bottleneck — the interface is

The substrate computes at the speed of the physics (gates settle in ~nanoseconds). The only cost *we* add is our
**interaction** with it — present an input, trigger, read the answer (the "buttons"). On this laptop, lacking the
physical substrate, our button is expensive because it has to *carry the compute itself* (the emulated ripple). So the
real ceiling is the button rate, not the compute.

Measured directly (`sdc_button.py`, W=32768, one press = 32,768 nonces):

| | rate | throughput |
|---|---|---|
| **Full press** (present + ripple 213k gates + harvest) — compute-bound, what we run | 2.3 presses/s | ~77k H/s* |
| **Button only** (present the nonces + harvest the answer, NO gate evaluation) — the interface | 27,733 presses/s | **~909 million H/s** |

**The button is ~11,800× faster than the compute-bound press.**

\* the full press read 77k instead of ~118k here because the 30-min live run was sharing the core during this
measurement; the *ratio* (~11,800×) is the robust part.

## What it means

- On the real substrate (gates settle for free), our interface **alone** would feed ~909 M H/s at this button width —
  and that scales with the button width W. **The compute is not the limit; our button is.**
- Today's ~118k H/s sits **~11,800× below our own interface ceiling.** That entire gap *is* the emulation — our button
  doing, in software, the work the substrate would do at light speed.
- The two levers that attack the button (and dodge the compute wall entirely):
  - **Bit-slice = a wider button** — one press presents W=32,768 nonces at once. Widen W, widen the button (costs RAM).
  - **The mirror = the button pressing itself** — the self-advancing nonce removes the host from the inner loop, so on
    real hardware there's *no per-nonce press at all*; the circuit runs on power and the only remaining limit is gate
    propagation — the light speed.

## The speed ladder

1. **Compute-bound floor (here):** ~118k H/s — our button carrying the emulated compute.
2. **Interface / button ceiling:** ~909 M H/s at this width — if the compute were free (the substrate).
3. **Past the button:** the mirror dissolves the per-nonce press; the limit becomes the gate physics (light speed).

So the light-speed isn't something we're missing — it's the substrate's. The only thing *we* contribute is the button,
and the whole optimization story of this project is: **widen the button, then remove it.**
