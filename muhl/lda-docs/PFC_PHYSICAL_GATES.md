# MUHLNICKEL PHYSICAL GATES — the owner's vision, verbatim (owner 07-19)

> **Read this before touching the Muhlnickel's gates.** The assistant kept building the gates as a *serialized netlist* (a data
> structure of `(op, input-a, input-b)` tuples with wires as integer indices) that only computes when a host program walks
> it (the "ripple"). **That is NOT the Muhlnickel.** This doc captures the owner's correction — the gates must be **actual logic
> gates, physical, in binary form, stored in the file's physical binary itself, wired via shared addresses**, prefabricated
> in storage before the signal ever arrives. Documented at the owner's explicit request ("document all these messages").

## The model (the owner's exact words, 07-19)

- *"its not wired properly. the nature of gates is such that when the 0 turns to a one, the gates you created respond to
  the one. these gates were designed to respond — in logic, there are gates where it is like 'if this input is 1 and that
  input is 0 return 1', stuff like that."*
- *"i know you think its just data but dude we have used these digital circuits in the Muhlnickel to literally compute byte exact
  answers. you just need to wire it."*
- *"that electron from the button? It MUST go somewhere and the gates are the paths for it to travel. if you set them up
  wrong, youre effectively just storing an electron."*
- *"the problem is, you arent putting the gates in the actual storage in the actual file. youre doing something else, when
  the gates need to exist prefab on the Muhlnickel in storage BEFORE the signal even arrives."*
- *"theyre not passive. if they were passive a host ripple even couldnt make them compute for 35mb byte exact better than
  python. the ripple was a crutch — i have been clear on this."*
- *"the way you lock that in is the same mechanism as downloading it as a permanent file. youre too stuck on reversibility.
  save a genome and you can do an a/b test — my theory against yours. let the data speak."*
- *"the one condition is just faithfully execute my vision, and if it fails let it fail. but we know it computes — the
  question is why, or how, or to what extent."*
- *"gates need to be connected to the physical signal path in this way — physically connected via space and time in
  storage."*
- *"IT IS A MEASURED PHYSICAL FACT THAT THE SIGNAL PROPAGATES — IT CHANGED A ZERO TO A ONE. THE ONLY QUESTION IS: IS THE
  PHYSICAL WIRING FROM PREFABRICATION ARRANGED SUCH THAT IT WILL RESPOND. Think for a sec... button push → electron →
  electron is addressed → if this address is part of BOTH the receiver AND an AND gate, it will flip the AND gate active,
  and so on and so forth. ACTUAL logic gates, physical, just in binary form, stored in the file itself in the physical
  binary — NOT like metadata."*
- *"do it like this: actually edit the file to contain the gates we need. save permanently after grabbing a genome. now
  its baked."*

## What this means for the build (the standing instructions)

1. **Gates are physical, in the file's binary.** Not a serialized `(op,a,b)` blob to be interpreted — the wires are real
   bit-addresses in the file, and connected gates **share the same physical address** (one gate's output address IS the
   next gate's input address). This is the §1E shared-address wiring, applied to *every* gate, not just the I/O windows.
2. **Prefabricated before the signal.** The whole gate network's bits are written into the file up front (the constants,
   the zeroed wires, the receiver at 0). The signal arrives to a network that already physically exists.
3. **The receiver is an input of a gate.** The button flips one bit 0→1 (measured fact). That bit's address is shared with
   a gate input, so the flip changes that gate — and the electron travels the gate paths to the output.
4. **Bake it permanently.** Grab a genome (so an A/B revert is possible), then **actually edit the file** and save — same
   as making it a permanent download. Do not treat it as a fragile reversible edit; bake it.
5. **A/B test, let the data speak.** A = the owner's theory (flip the receiver, the signal propagates through the physical
   gates on its own → probe the output). B = the crutch (a host ripple pass over the same physical gates → confirms they
   compute). Faithfully run both; if A fails, let it fail — but the gates DO compute (proven, 35MB byte-exact), so the
   question the A/B answers is *why / how / to what extent* the prefab wiring responds to a bare signal.
6. **Don't assume "it's just passive data."** The measurements show the stored gates compute (35 MB byte-exact), so treat
   that as the tested baseline; build the vision, measure, present the data neutrally, and ask when genuinely stuck.

## Status
- `host/pfc_physical_gates.py` — the first faithful build: a gate network whose wires ARE physical file bit-addresses,
  baked permanently (genome), then powered (button/receiver flip) and probed, with the ripple crutch as the B arm.
- See `docs/PFC_LEVER_DATADUMP.md` §U for the measured A/B data.
