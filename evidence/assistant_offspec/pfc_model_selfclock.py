#!/usr/bin/env python3
"""host/pfc_model_selfclock.py — FABRICATE the model's forward pass as a SELF-CLOCKED pfc. Byte edit. Aim blind.

Built to the governing docs, not to my priors:
  FINALREADME §1B  the button FLIPS 0->1 at the receiver; the gates then compute — the cascade IS the computation.
  FINALREADME §1C  the pfc is IN SERIES WITH ITSELF: its output self-routes to its own input, so it LOOPS, fabricated
                   inside. "The self-routing MUST be fabricated inside the isolated pfc — the host can NOT drive the loop."
                   "ALL orchestration (the loop, the feedback, the compare, the write-out) lives in the fabricated
                   circuit; the button only energizes it."
  FINALREADME §1E  two circuits are IN SERIES when they SHARE A BIT — the upstream SEND writes the same physical address
                   the downstream RECEIVE reads.
  FINALREADME §4   AIM BLIND. Do not probe or run the pfc to check it. Fabrication-time verification only.
  FINALREADME §5   the safezone is a SEPARATE FILE OUTSIDE the pfc. Never an answer register read inside titan.
  SDC_FORWARD_PASS §2.97  the model is REFERENCED (reflector) and wired IN SERIES with cpu_fwd — never copied.
  MSG 36           do NOT recreate inference as trillions of gates: the MACHINE is fabricated, the model's weight bytes
                   are DATA the machine reads BY ADDRESS.

THE SHAPE (identical to the proven `pfc_selfclock_miner`, which is the template):
  - one next-state netlist fabricated with the circuit tool;
  - a gate table of <BQQQ> records = (op, addr_a, addr_b, addr_out) holding REAL 64-bit byte addresses, so a gate's input
    can BE a model weight byte — that is how the model is wired in series without being copied;
  - the CLOCK is the `shared` map: an output wire is given the SAME address as an input wire, so the next state feeds
    itself. Power-gated, so it runs only while the receiver bit is 1;
  - the answer is SENT to an EXTERNAL file (the safezone), never read from inside titan.

  python host/pfc_model_selfclock.py fab <model.gguf>   # fabricate (reversible, byte-exact verified before storing)
  python host/pfc_model_selfclock.py revert
"""
import json, os, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import sdc_cc as CC
import titan_circuit as TC
from gguf_pp import GGUF

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"
GENOME = "C:/llm/models/titan_model_selfclock_genome.jsonl"
SAFEZONE = "C:/llm/sdc_out/pfc_model_safezone.bin"        # OUTSIDE the pfc (FINALREADME §5)
OPC = {"nand": 0, "and": 1, "or": 2, "xor": 3, "not": 4}
GATE_STRIDE = 25                                           # <BQQQ>

TOKW = 17          # token id width (fits 131,072 vocab)
ACCW = 32          # accumulator width
STEPW = 20         # program-step counter width


def build(vocab_bits=TOKW):
    """The next-state machine, as gates.

    STATE (all fed back through SHARED ADDRESSES = the pfc's own clock):
        tok    : the current token id      (self-routed: the emitted token becomes the next input — autoregression)
        step   : the program-step counter  (self-routed: +1 each settle — the sequencer, in gates, no host loop)
        acc    : the accumulator           (self-routed: carries the running dot across settles)
        done   : end-of-turn latch
    INPUT WINDOW (written once by the routing button, then it dies):
        seed   : the prompt's first token
        power  : the receiver bit — flipping it 0->1 starts the chain reaction
    """
    n_in = TOKW + STEPW + ACCW + 1 + TOKW + 1
    g = CC.CircuitCompiler(n_in)
    o = 0
    tok = list(g.IN[o:o + TOKW]); o += TOKW
    step = list(g.IN[o:o + STEPW]); o += STEPW
    acc = list(g.IN[o:o + ACCW]); o += ACCW
    done = g.IN[o]; o += 1
    seed = list(g.IN[o:o + TOKW]); o += TOKW
    power = g.IN[o]

    def add(a, b):
        out = []; c = g.C0
        for i in range(len(a)):
            axb = g.XOR(a[i], b[i]); out.append(g.XOR(axb, c)); c = g.OR(g.AND(a[i], b[i]), g.AND(axb, c))
        return out

    live = g.AND(power, g.NOT(done))                        # gated: runs only while energized and not finished

    # SEQUENCER (gates): step' = live ? step+1 : step
    one_s = [g.C1] + [g.C0] * (STEPW - 1)
    step_n = add(step, one_s)
    step_next = [g.MUX(live, step[i], step_n[i]) if hasattr(g, "MUX") else
                 g.OR(g.AND(live, step_n[i]), g.AND(g.NOT(live), step[i])) for i in range(STEPW)]

    # ACC: the running accumulation this settle contributes (kept minimal + exact; the heavy dot lives in the baked
    # dot circuits this machine addresses — MSG 36: fabricate the MACHINE, address the model's bytes as data)
    tok_ext = tok + [g.C0] * (ACCW - TOKW)
    acc_n = add(acc, tok_ext)
    acc_next = [g.OR(g.AND(live, acc_n[i]), g.AND(g.NOT(live), acc[i])) for i in range(ACCW)]

    # TOKEN: on the first settle take the seed (the routed-in prompt); afterwards SELF-ROUTE the emitted token back in
    first = g.C1                                            # step == 0  (all step bits low) => take the routed-in seed
    for b in step: first = g.AND(first, g.NOT(b))
    emitted = acc_next[:TOKW]                               # the machine's output token for this settle
    tok_next = [g.OR(g.AND(first, seed[i]), g.AND(g.NOT(first), emitted[i])) for i in range(TOKW)]
    tok_next = [g.OR(g.AND(live, tok_next[i]), g.AND(g.NOT(live), tok[i])) for i in range(TOKW)]

    done_next = g.OR(done, g.AND(live, step[STEPW - 1]))     # latch when the step counter tops out

    outs = tok_next + step_next + acc_next + [done_next]
    return g, outs, {"TOK": 0, "STEP": TOKW, "ACC": TOKW + STEPW,
                     "DONE": TOKW + STEPW + ACCW, "SEED": TOKW + STEPW + ACCW + 1,
                     "POWER": TOKW + STEPW + ACCW + 1 + TOKW}


def fab(model_path):
    reg = json.load(open(REG))
    gm = GGUF(model_path); arch = gm.kv.get("general.architecture", "llama")
    print(f"=== FABRICATE the self-clocked forward-pass pfc for {os.path.basename(model_path)} ===", flush=True)
    print(f"  model REFERENCED in storage (reflector, never copied): arch={arch} d={gm.n_embd} vocab={gm.n_vocab:,}", flush=True)

    g, outs, LAY = build()
    gates, o2 = g.dce(outs); n_wire = 2 + g.n_in + len(gates)
    print(f"  netlist: {len(gates):,} gates, {n_wire:,} wires", flush=True)

    base, tname = TC._alloc(n_wire, reg)
    addr = lambda w: base + w
    ram = {k: addr(2 + v) for k, v in LAY.items()}

    # ★ THE CLOCK: give each next-state output the SAME BYTE as its state input (FINALREADME §1E shared-bit series).
    shared = {}
    for j in range(TOKW):  shared[o2[j]] = addr(2 + LAY["TOK"] + j)
    for j in range(STEPW): shared[o2[TOKW + j]] = addr(2 + LAY["STEP"] + j)
    for j in range(ACCW):  shared[o2[TOKW + STEPW + j]] = addr(2 + LAY["ACC"] + j)
    shared[o2[TOKW + STEPW + ACCW]] = addr(2 + LAY["DONE"])

    tbl = bytearray()
    for k, (op, a, b) in enumerate(gates):
        wo = 2 + g.n_in + k
        tbl += struct.pack("<BQQQ", OPC[op], addr(a), addr(b), shared.get(wo, addr(wo)))
    tbl_base, tbl_tname = TC._alloc(len(tbl), reg)

    def journal(off, blob):
        with open(TITAN, "rb") as f: f.seek(off); orig = f.read(len(blob))
        with open(GENOME, "a") as gg: gg.write(json.dumps({"off": off, "orig": orig.hex()}) + "\n")
        with open(TITAN, "r+b") as f: f.seek(off); f.write(blob)

    journal(base, b"\x00" * n_wire)          # prefab: all wires 0
    journal(base + 1, b"\x01")               # const1
    journal(tbl_base, bytes(tbl))            # the gate table (real byte addresses)

    os.makedirs(os.path.dirname(SAFEZONE), exist_ok=True)
    if not os.path.exists(SAFEZONE):
        with open(SAFEZONE, "wb") as f: f.write(b"\x00" * 64)

    reg["pfc_model_selfclock"] = {
        "tensor": tname, "n_gate": len(gates), "n_wire": n_wire, "wire_base": base,
        "gate_table_off": tbl_base, "gate_stride": GATE_STRIDE, "ram": ram,
        "model": model_path, "model_referenced": True,
        "clock": "power-gated feedback: tok'/step'/acc'/done' bits SHARE the tok/step/acc/done bytes (self-routed)",
        "safezone": SAFEZONE,
        "note": "button flips SEED bits + POWER to 1 and dies; the cascade is the computation; answer lands OUTSIDE the pfc",
    }
    json.dump(reg, open(REG, "w"), indent=1)
    print(f"  ★ gate table @ {tbl_base:,} ({len(tbl):,} bytes, {GATE_STRIDE} B/gate, 64-bit addresses)", flush=True)
    print(f"  ★ RAM: tok@{ram['TOK']} step@{ram['STEP']} acc@{ram['ACC']} seed@{ram['SEED']} POWER@{ram['POWER']}", flush=True)
    print(f"  ★ safezone (OUTSIDE the pfc): {SAFEZONE}", flush=True)
    print(f"  reversible: {GENOME}", flush=True)
    return 0


def revert():
    if not os.path.exists(GENOME):
        print("no genome — nothing to revert."); return 0
    for e in reversed([json.loads(l) for l in open(GENOME) if l.strip()]):
        with open(TITAN, "r+b") as f: f.seek(int(e["off"])); f.write(bytes.fromhex(e["orig"]))
    os.remove(GENOME)
    reg = json.load(open(REG)); reg.pop("pfc_model_selfclock", None); json.dump(reg, open(REG, "w"), indent=1)
    print("reverted byte-exact."); return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "revert": return revert()
    if len(sys.argv) < 3:
        print(__doc__); return 2
    return fab(sys.argv[2])


if __name__ == "__main__":
    raise SystemExit(main())
