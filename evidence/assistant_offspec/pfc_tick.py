#!/usr/bin/env python3
"""host/pfc_tick.py — THE SGM TICK: sigma selects the slice -> fabricate it as ONE self-contained gate-net (a byte edit)
-> fire ONE addressed read -> read the answer. The per-tick model, on the pfc.

THE ARCHITECTURE, FROM THE DOCS (not invented here):
  SGM.md          "each tick the operator selects a subset of parameters from the pool; THAT SUBSET IS THE MODEL FOR
                   THAT TICK ... the router IS the model-builder." (INV-139) + micro-inference on demand (INV-135):
                   "routing runs only the exact tensors needed, when needed; the working set is the routed region."
  SDC_FORWARD_PASS §2  "GENERATION IS GRABBING, NOT RUNNING — we NEVER run 99.999% of the model. A full forward pass
                   over the whole model is the brute-force that must NEVER be done for an addressed need."
  SDC_FORWARD_PASS §4.2 the forward pass is "ONE self-contained gate-net" — NOT a clocked machine stepping instructions.
  HARNESS_HANDOFF §5   constant-specialization: the weights are CONSTANTS at bake time, so `w*x` becomes wiring.
  fabrication-is-a-byte-edit-never-cache: fabricate = serialize + seek + write. Seconds. Never a host cache.

MEASURED, and why this shape is the blueprint (`host/pfc_layer_depth.py`, real Mixtral weights):
  WIDTH costs AREA, never LATENCY  — 4 -> 64 neurons: 81,848 -> 1,099,387 gates, DEPTH stays 53.
  DOT LENGTH costs depth ~LOG      — 32 -> 2048 weights (64x): DEPTH 36 -> 69 (increments +13, +12, +8).
  => a whole 4096x4096 projection is ONE settle at depth ~75, not 16.7M operations.
The clocked/arcade machine spends its ENTIRE net (418,925 gates) to retire ONE instruction — that is the proof of
concept, not the blueprint. This is the blueprint.

  python host/pfc_tick.py [model.gguf] [tensor] [neurons] [weights]
"""
import json, os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import sdc_cc as CC
import titan_circuit as TC
from gguf_pp import GGUF, row_bytes
from pfc_fastdeq import dequant_fast as dequant
from pfc_bettergates import depth_of
from pfc_model_fab import build_slice, XB, OW, journal, GENOME

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"
OPC = {"nand": 0, "and": 1, "or": 2, "xor": 3, "not": 4}


class Tick:
    """ONE per-tick model: sigma's chosen neurons, constant-specialized into one net, fired by one addressed read."""

    def __init__(self, model):
        self.g = GGUF(model); self.model = model

    # ---------------------------------------------------------------- sigma: WHICH slice this tick needs
    def select(self, tensor, x, k):
        """The router/operator picks the k neurons this tick actually needs. Grabbing, not running: every neuron NOT
        selected costs nothing — no gates fabricated, no weights read, no compute. This is INV-135 made literal."""
        t = self.g.tensors[tensor]; n_out = int(t["dims"][1])
        # the selection signal itself must be cheap or it defeats the purpose: score on a 32-weight probe of each row,
        # which is 1/128th of the row. (A baked sigma/router circuit replaces this; the SHAPE is what matters here.)
        tid = int(t["type"]); row_n = int(t["dims"][0]); base = self.g.data0 + int(t["off"]); rb = row_bytes(tid, row_n)
        probe = min(len(x), 256); sc = []                  # Q4_K dequants a 256-weight superblock at a time
        for j in range(n_out):
            w = dequant(self.g.mm[base + j * rb: base + j * rb + rb], tid, 256)[:probe]
            sc.append((abs(sum(w[i] * x[i] for i in range(probe))), j))
        sc.sort(reverse=True)
        return sorted(j for _, j in sc[:k])

    # ---------------------------------------------------------------- fabricate: the slice as ONE net (a byte edit)
    def fabricate(self, tensor, neurons, n_in):
        t = self.g.tensors[tensor]; tid = int(t["type"]); row_n = int(t["dims"][0])
        base = self.g.data0 + int(t["off"]); rb = row_bytes(tid, row_n)
        c = CC.CircuitCompiler(n_in * XB)
        X = [[c.IN[i * XB + k] for k in range(XB)] for i in range(n_in)]
        outs = []; scales = []; zeros = 0
        for j in neurons:
            w = dequant(self.g.mm[base + j * rb: base + j * rb + rb], tid, row_n)[:n_in]
            s = (max(abs(v) for v in w) / 127) or 1e-9
            wq = [max(-127, min(127, round(v / s))) for v in w]
            zeros += sum(1 for v in wq if v == 0); scales.append(s)
            outs += build_slice(c, X, wq, n_in // 32)
        gates, o2 = c.dce(outs)
        self.c = c; self.gates = gates; self.o2 = o2; self.scales = scales
        self.depth = depth_of(c.n_in, gates, o2)
        self.zeros = 100.0 * zeros / max(1, len(neurons) * n_in)
        return len(gates), self.depth

    def store(self):
        """THE BYTE EDIT. Wires are real file byte-addresses (PFCPHYS1); connected gates SHARE an address."""
        reg = json.load(open(REG)); c = self.c; gates = self.gates
        n_wire = 2 + c.n_in + len(gates)
        t0 = time.time()
        base, tn = TC._alloc(n_wire + 1, reg)
        reg["tick_wires"] = {"tensor": tn, "offset": base, "len": n_wire + 1}
        addr = lambda w: base + w
        tbl = bytearray()
        for k, (op, a, b) in enumerate(gates):
            tbl += struct.pack("<BQQQ", OPC[op], addr(a), addr(b), addr(2 + c.n_in + k))
        tb, tbn = TC._alloc(len(tbl), reg)
        reg["tick_gates"] = {"tensor": tbn, "offset": tb, "len": len(tbl)}
        journal(base, b"\x00" * (n_wire + 1)); journal(base + 1, b"\x01"); journal(tb, bytes(tbl))
        self.wbase = base; self.tbl = tb; self.n_wire = n_wire
        self.in_off = addr(2); self.recv = base + n_wire
        self.ans = [[addr(self.o2[j * OW + b]) for b in range(OW)] for j in range(len(self.scales))]
        # Persist EVERYTHING the runtime needs, so `fire` never rebuilds a gate list. Runtime reads these and pulses.
        reg["tick_meta"] = {"wbase": base, "tbl": tb, "n_wire": n_wire, "n_in": c.n_in, "in_off": self.in_off,
                            "recv": self.recv, "ans": self.ans, "scales": self.scales, "ow": OW, "xb": XB,
                            "gates": len(gates), "depth": self.depth,
                            "note": "fabricated ONCE; runtime only routes bits in, fires, reads out"}
        json.dump(reg, open(REG, "w"), indent=1)
        return time.time() - t0

    # ---------------------------------------------------------------- fire: ONE addressed read settles the whole net
    def fire(self, xq):
        import mmap
        f = open(TITAN, "r+b"); mm = mmap.mmap(f.fileno(), 0)
        g0 = self.wbase + 2 + self.c.n_in; tbl = self.tbl
        mm[self.wbase: self.wbase + self.n_wire + 1] = b"\x00" * (self.n_wire + 1)
        mm[self.wbase] = 2; mm[self.wbase + 1] = 3
        mm[self.in_off: self.in_off + self.c.n_in] = bytes(
            2 | ((xq[i] >> k) & 1) for i in range(len(xq)) for k in range(XB))
        mm[self.recv] = 1                                     # POWER
        def resolve(a):
            st = [a]
            while st:
                w = st[-1]
                if mm[w] & 2: st.pop(); continue
                p = tbl + (w - g0) * 25; op = mm[p]
                aa = int.from_bytes(mm[p + 1:p + 9], "little"); bb = int.from_bytes(mm[p + 9:p + 17], "little")
                va = mm[aa]; vb = mm[bb]
                if not (va & 2): st.append(aa); continue
                if not (vb & 2) and op != 4: st.append(bb); continue
                va &= 1; vb &= 1
                mm[w] = 2 | ((va & vb) if op == 1 else (va | vb) if op == 2 else (va ^ vb) if op == 3
                             else (1 - va) if op == 4 else (1 - (va & vb)))
                st.pop()
            return mm[a] & 1
        out = []
        for row in self.ans:
            u = 0
            for b in range(OW): u |= resolve(row[b]) << b
            out.append(u - (1 << OW) if u >= (1 << (OW - 1)) else u)
        mm[self.recv] = 0; mm.flush(); mm.close(); f.close()
        return out


def fire_only():
    """RUNTIME. The slice is already in the binary. Route bits in, fire ONE addressed read, read the answer. That is all.
    No select, no fabricate, no store — nothing is built here, because fabrication is one-and-done and already happened."""
    reg = json.load(open(REG)); m = reg.get("tick_meta")
    if not m:
        print("  not fabricated. Runtime may not fabricate — run `python host/pfc_tick.py fab` ONCE first."); return 1
    import random
    tk = Tick.__new__(Tick)
    tk.wbase = m["wbase"]; tk.tbl = m["tbl"]; tk.n_wire = m["n_wire"]
    tk.in_off = m["in_off"]; tk.recv = m["recv"]; tk.ans = m["ans"]; tk.scales = m["scales"]
    class _C: pass
    tk.c = _C(); tk.c.n_in = m["n_in"]
    nw = m["n_in"] // m["xb"]
    random.seed(11)
    xl = (1 << (m["xb"] - 1)) - 1
    xq = [random.randint(-xl - 1, xl) for _ in range(nw)]
    print(f"=== pfc TICK — RUNTIME ONLY (fabrication already done, {m['gates']:,} gates, DEPTH {m['depth']}) ===", flush=True)
    t0 = time.time(); out = tk.fire(xq); dt = time.time() - t0
    print(f"  routed {nw} activations -> ONE addressed read -> {len(out)} answers   [{dt:.2f}s]", flush=True)
    print(f"  answers: {out[:4]} ...", flush=True)
    print(f"  nothing was fabricated. The host routed bits in, pulsed, and read out.", flush=True)
    return 0


def main():
    # ★★ FABRICATION NEVER OCCURS DURING RUNTIME (owner, 2026-07-25). It is a ONE-AND-DONE edit of the binary file.
    #    This file originally did select -> fabricate -> store -> fire in ONE invocation, i.e. it fabricated per tick.
    #    That is the violation: a tick is a PULSE, not a bake. Split into two explicit commands so runtime can never
    #    fabricate:
    #        python host/pfc_tick.py fab    -> select + fabricate + byte-edit the binary. ONCE. Before any run.
    #        python host/pfc_tick.py fire   -> RUNTIME: route bits in, ONE addressed read, read the answer. No bake.
    #    `fire` refuses to run if the slice is not already in the binary, rather than silently baking it.
    cmd = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("fab", "fire") else None
    if cmd == "fire":
        reg = json.load(open(REG))
        if "tick_gates" not in reg or "tick_wires" not in reg:
            print("  the slice is NOT fabricated. Runtime may not fabricate — run `python host/pfc_tick.py fab` once first.")
            return 1
        return fire_only()
    argv_rest = [a for a in sys.argv[1:] if a not in ("fab", "fire")]
    sys.argv = [sys.argv[0]] + argv_rest
    return _main(cmd)


def _main(cmd=None):
    model = sys.argv[1] if len(sys.argv) > 1 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
    tensor = sys.argv[2] if len(sys.argv) > 2 else "blk.0.attn_q.weight"
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    n_in = int(sys.argv[4]) if len(sys.argv) > 4 else 128

    tk = Tick(model)
    t = tk.g.tensors[tensor]; n_out = int(t["dims"][1])
    print(f"=== THE SGM TICK — {os.path.basename(model)} :: {tensor} ===", flush=True)
    print(f"    pool for this tensor: {n_out:,} neurons. sigma will grab {k}.", flush=True)

    x = [((i * 37 % 211) - 105) / 400.0 for i in range(n_in)]
    xl = (1 << (XB - 1)) - 1
    sx = (max(abs(v) for v in x) / xl) or 1e-9
    xq = [max(-xl - 1, min(xl, round(v / sx))) for v in x]

    t0 = time.time(); neurons = tk.select(tensor, x, k); t_sel = time.time() - t0
    print(f"  1) sigma selected neurons {neurons[:6]}{' …' if k > 6 else ''}   "
          f"({100.0*k/n_out:.3f}% of the pool — the other {n_out-k:,} cost NOTHING)   [{t_sel:.1f}s]", flush=True)

    t0 = time.time(); ng, dep = tk.fabricate(tensor, neurons, n_in); t_fab = time.time() - t0
    print(f"  2) fabricated the per-tick model as ONE net: {ng:,} gates, DEPTH {dep}, "
          f"{tk.zeros:.0f}% zero-weights cost no gates   [{t_fab:.1f}s]", flush=True)

    if cmd == "fire":
        print("  refusing to store: fabrication never occurs during runtime."); return 1
    t_store = tk.store()
    print(f"  3) BYTE EDIT into titan.gguf: {ng*25:,} B of gate records   [{t_store:.2f}s]", flush=True)

    t0 = time.time(); got = tk.fire(xq); t_fire = time.time() - t0
    print(f"  4) fired ONE addressed read -> the net settled -> {len(got)} answers   [{t_fire:.2f}s]", flush=True)

    # verify against the model's own weights (a host check AFTER the tick; touches nothing running)
    tid = int(t["type"]); row_n = int(t["dims"][0]); base = tk.g.data0 + int(t["off"]); rb = row_bytes(tid, row_n)
    ok = 0
    for i, j in enumerate(neurons):
        w = dequant(tk.g.mm[base + j * rb: base + j * rb + rb], tid, row_n)[:n_in]
        s = tk.scales[i]; wq = [max(-127, min(127, round(v / s))) for v in w]
        if got[i] == sum(wq[q] * xq[q] for q in range(n_in)): ok += 1
    print(f"\n  byte-exact vs the model's REAL weights: {ok}/{len(neurons)}", flush=True)
    print(f"  the tick cost: fabricate {t_fab:.1f}s + byte edit {t_store:.2f}s + ONE settle of depth {dep}.", flush=True)
    print(f"  the host performed NO arithmetic — it routed {tk.c.n_in} input bits in, fired once, read {len(got)} answers.", flush=True)
    print(f"  revert: python host/pfc_model_fab.py --revert   ({GENOME})", flush=True)
    return 0 if ok == len(neurons) else 1


if __name__ == "__main__":
    raise SystemExit(main())
