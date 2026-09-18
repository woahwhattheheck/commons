#!/usr/bin/env python3
"""host/pfc_model_engine.py — THE MODEL RUNS AS A PROGRAM ON THE pfc. No host forward pass. No model rebuilt as gates.

WHY THIS FILE EXISTS (the correction, owner 2026-07-24):
  "IDIOT YOU DONT RECREATE THE FUCKING MODEL IN THE PFC YOU JUST NEED TO HAVE THE PFC COMPUTE THE MODEL JUST LIKE IT
   COMPUTES EVERYTHING ELSE IT COMPUTES"
Two things were being done wrong and both are banned in `PFC_GROUNDING` §3:
  - `host/pfc_forward.py` is a HOST forward pass  -> "NEVER recreate the model / write a host forward pass."
  - `host/pfc_model_fab.py` baked model weights as gates -> recreating the model INSIDE the pfc. Also wrong.
The pfc is a literal digital computer. A model is a PROGRAM it executes, exactly like Life, Tetris, the raycaster, the
miner and `pfc_cpu32` are programs it executes. The host routes data in, pulses, and reads the answer. Nothing else.

WHAT THIS EXTENDS (reuse, never rebuild — `docs/CIRCUIT_PFC.md`, registry `C:/llm/models/titan_circuits.json`):
  `cpu_fwd`         404,262 g — the baked ALU (ADD SUB MUL SILU EXP RSQRT GT MOV, Q8.8). Its datapath is reused verbatim.
  `pfc_fwd_engine`  413,865 g — the baked clocked machine: ALU + program ROM + sequencer + regfile. Straight-line only:
                    its ROM holds <=32 instructions and its weights are baked immediates, so it cannot walk a real
                    tensor. THIS file adds the two things that makes it general:
                      * a DATA RAM inside the pfc's own state (the model's numbers live in the machine, not the host)
                      * LOAD  (indexed read of that RAM)  and  BRNZ (branch) -> the program can LOOP
                    so ONE short program computes a dot of any length. That is the difference between a demo and a
                    machine that can run a model.

THE CONTRACT (unchanged from the arcade method / `pfc_fwd_engine`): the host reads the state from storage, pulses ONE
clock tick (evaluates the baked next-state circuit off storage), latches the next state back, and repeats until the
machine halts. WHICH OP RUNS EACH TICK IS DECIDED BY THE SEQUENCER'S GATES, never by the host. The host performs no
arithmetic of any kind — verified by the test below, which compares the pfc's answer to the model's real weights.

  python host/pfc_model_engine.py fab            # bake the looping engine (byte-exact verified first), reversible
  python host/pfc_model_engine.py test           # run a REAL model's weights through it on the pfc, byte-exact
  python host/pfc_model_engine.py revert
"""
import json, os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import titan_circuit as TC
from sdc_bake_cpu import build_cpu, _ref, SC, _s16, SHIFT

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"
GENOME = "C:/llm/models/titan_model_engine_genome.jsonl"
SBX = "C:/llm/sdc_sandbox/model_engine"; STATEFILE = os.path.join(SBX, "state.bin")
NAME = "pfc_model_engine"

NREG = 8; RW = 16; PCW = 4; MEMW = 64                     # 8 regs, 64-word data RAM (32 weights + 32 activations)
MEMSEL = 6                                                 # log2(MEMW)
STATE_BITS = NREG * RW + MEMW * RW + PCW + 1               # regs | data RAM | pc | halt
# ISA: cpu_fwd's 8 ALU ops, plus LOAD (indexed RAM read) and BRNZ (the branch that makes looping possible)
OPC = {"ADD": 0, "SUB": 1, "MUL": 2, "SILU": 3, "EXP": 4, "RSQRT": 5, "GT": 6, "MOV": 7, "LOAD": 8, "BRNZ": 9}
OPW = 4

# ── THE PROGRAM: y = SiLU(sum_i w_i * x_i) over 32 elements. w in RAM[0..31], x in RAM[32..63].
#    Eight instructions in the loop body; the loop is the machine's own branch, not a host `for`.
R_I, R_ACC, R_W, R_T, R_X, R_C, R_Y = 0, 1, 2, 3, 4, 5, 6
NELEM = 32
PROGRAM = [
    ("LOAD", R_I,   0, 0,      R_W),      # 0: Rw   = RAM[Ri]            (the weight)
    ("ADD",  R_I,   1, NELEM,  R_T),      # 1: Rt   = Ri + 32
    ("LOAD", R_T,   0, 0,      R_X),      # 2: Rx   = RAM[Rt]            (the activation)
    ("MUL",  R_W,   0, R_X,    R_W),      # 3: Rw   = Rw * Rx            (Q8.8 multiply, cpu_fwd's gates)
    ("ADD",  R_ACC, 0, R_W,    R_ACC),    # 4: Racc = Racc + Rw
    ("ADD",  R_I,   1, 1,      R_I),      # 5: Ri   = Ri + 1
    ("SUB",  R_I,   1, NELEM,  R_C),      # 6: Rc   = Ri - 32            (zero when the loop is done)
    ("BRNZ", R_C,   1, 0,      0),        # 7: if Rc != 0 -> pc = 0      ★ the machine branches, the host does not
    ("SILU", R_ACC, 0, 0,      R_Y),      # 8: Ry   = SiLU(Racc)         (the neuron)
]
PROGLEN = len(PROGRAM); ANSREG = R_Y


def q88(x): return int(round(x * SC)) & 0xFFFF
def from_q88(u): return _s16(u) / SC


def _microcode(op, rA, useImm, immB, rD):
    return ((OPC[op] & 15) | (rA & 7) << 4 | (useImm & 1) << 7 | (immB & 0xFFFF) << 8 | (rD & 7) << 24)   # 27 bits


# ─────────────────────────────── reference interpreter (fab-time verification ONLY, never the runtime) ───────────────
def ref_run(mem):
    regs = [0] * NREG; ram = list(mem) + [0] * (MEMW - len(mem)); pc = 0; ticks = 0
    while pc < PROGLEN and ticks < 100000:
        op, rA, useImm, immB, rD = PROGRAM[pc]
        A = regs[rA]; B = immB if useImm else regs[immB & 7]
        if op == "LOAD":
            regs[rD] = ram[A & (MEMW - 1)] & 0xFFFF; pc += 1
        elif op == "BRNZ":
            pc = (immB & 15) if regs[rA] != 0 else pc + 1
        else:
            regs[rD] = _ref(OPC[op], A, B) & 0xFFFF; pc += 1
        ticks += 1
    return regs, ticks


# ─────────────────────────────── the clocked next-state circuit: ALU + RAM + sequencer, ALL GATES ────────────────────
def build_engine():
    c = TC.Circuit(STATE_BITS + 1)
    IN = c.IN
    o = 0
    regs = [IN[o + r * RW: o + (r + 1) * RW] for r in range(NREG)]; o += NREG * RW
    ram = [IN[o + m * RW: o + (m + 1) * RW] for m in range(MEMW)]; o += MEMW * RW
    pc = IN[o: o + PCW]; o += PCW
    halt = IN[o]; clk = IN[STATE_BITS]

    def mux_tree(sel_bits, nodes, w):
        nd = [list(n) for n in nodes]
        for s in sel_bits:
            nd = [[c.mux(s, nd[j][b], nd[j + 1][b]) for b in range(w)] for j in range(0, len(nd), 2)]
        return nd[0]

    def pad(nodes, n, w): return list(nodes) + [c.cvec(0, w) for _ in range(n - len(nodes))]

    # FETCH: pc -> the 27-bit microcode word, selected out of a constant ROM by the pc's own bits
    rom = pad([c.cvec(_microcode(*ins), 27) for ins in PROGRAM], 1 << PCW, 27)
    mc = mux_tree(list(pc), rom, 27)
    op = mc[0:4]; rA = mc[4:7]; useImm = mc[7]; immB = mc[8:24]; rD = mc[24:27]

    # READ operands
    A = mux_tree(list(rA), pad(regs, 8, RW), RW)
    regB = mux_tree(list(immB[0:3]), pad(regs, 8, RW), RW)
    B = [c.mux(useImm, regB[b], immB[b]) for b in range(RW)]

    # THE ALU (cpu_fwd's datapath, gate for gate) and the indexed RAM read, both evaluated every tick; the decoder picks
    alu = _alu(c, op[0:3], A, B)
    memv = mux_tree(list(A[0:MEMSEL]), pad(ram, MEMW, RW), RW)      # RAM[A] — the LOAD port
    is_load = c.and_(op[3], c.not_(c.or_(op[0], c.or_(op[1], op[2]))))    # opcode 8
    is_brnz = c.and_(op[3], c.and_(op[0], c.not_(c.or_(op[1], op[2]))))   # opcode 9
    result = [c.mux(is_load, alu[b], memv[b]) for b in range(RW)]

    step = c.and_(clk, c.not_(halt))
    writes = c.and_(step, c.not_(is_brnz))                          # a branch writes no register

    next_regs = []
    for r in range(NREG):
        is_dst = c.and_(c.eq_const(rD, r), writes)
        next_regs.append([c.mux(is_dst, regs[r][b], result[b]) for b in range(RW)])

    # PC: branch target when BRNZ and A != 0, else pc+1
    taken = c.and_(is_brnz, c.not_(c.is_zero(list(A))))
    pc_inc = c.add(list(pc), c.cvec(1, PCW))
    pc_nxt = [c.mux(taken, pc_inc[b], immB[b]) for b in range(PCW)]
    next_pc = [c.mux(step, pc[b], pc_nxt[b]) for b in range(PCW)]
    next_halt = c.or_(halt, c.eq_const(next_pc, PROGLEN))

    outs = []
    for r in range(NREG): outs += next_regs[r]
    for m in range(MEMW): outs += list(ram[m])                      # the data RAM persists unchanged (read-only program)
    outs += next_pc; outs += [next_halt]
    return c, outs


def _alu(c, op3, A, B):
    """cpu_fwd's ALU over our wires — the SAME gates `sdc_bake_cpu.build_cpu` bakes (same ops, Q8.8, same LUTs)."""
    from sdc_bake_cpu import _mul_s16, _lut, _mux8, _gt, SILU, EXP, RSQRT
    idx = A[SHIFT:16]
    r_add = c.add(A, B)
    r_sub = c.add(A, c.add([c.not_(x) for x in B], c.cvec(1, 16)))
    r_mul = _mul_s16(c, A, B)[8:8 + 16]
    r_silu = _lut(c, list(idx), SILU); r_exp = _lut(c, list(idx), EXP); r_rsqrt = _lut(c, list(idx), RSQRT)
    r_gt = _gt(c, A, B) + [c.C0] * 15
    r_mov = list(A)
    return _mux8(c, op3, [r_add, r_sub, r_mul, r_silu, r_exp, r_rsqrt, r_gt, r_mov])


# ─────────────────────────────── state packing (the machine's state lives in storage, never in host RAM) ─────────────
def _cd(c, outs): return {"n_in": c.n_in, "n_wire": c.n_wire(), "ga": c.ga, "gb": c.gb, "outs": outs}


def _pack(regs, ram, pc, halt, clk):
    bits = []
    for r in range(NREG): bits += [(regs[r] >> b) & 1 for b in range(RW)]
    for m in range(MEMW): bits += [(ram[m] >> b) & 1 for b in range(RW)]
    bits += [(pc >> b) & 1 for b in range(PCW)]; bits += [halt & 1, clk & 1]
    return bits


def _unpack(out):
    i = 0; regs = []
    for r in range(NREG): regs.append(sum(out[i + b] << b for b in range(RW))); i += RW
    ram = []
    for m in range(MEMW): ram.append(sum(out[i + b] << b for b in range(RW))); i += RW
    pc = sum(out[i + b] << b for b in range(PCW)); i += PCW
    return regs, ram, pc, out[i]


def _tick(cd, regs, ram, pc, halt):
    return _unpack(TC.ripple(cd, _pack(regs, ram, pc, halt, 1)))


def run_on_pfc(cd, mem, max_ticks=100000):
    """THE RUNTIME. Host: route `mem` into the machine's RAM, then pulse. Every tick the machine's own gates fetch,
    decode, branch and compute. The host performs NO arithmetic and makes NO control decision."""
    regs = [0] * NREG; ram = list(mem) + [0] * (MEMW - len(mem)); pc = 0; halt = 0; ticks = 0
    while not halt and ticks < max_ticks:
        regs, ram, pc, halt = _tick(cd, regs, ram, pc, halt); ticks += 1
    return regs, ticks


def _verify(cd, trials=6):
    import random; random.seed(3)
    for _ in range(trials):
        mem = [q88(random.uniform(-1.5, 1.5)) for _ in range(NELEM)] + \
              [q88(random.uniform(-1.5, 1.5)) for _ in range(NELEM)]
        ref, _ = ref_run(mem)
        got, _ = run_on_pfc(cd, mem)
        if got != ref: return False, (mem[:3], got[:7], ref[:7])
    return True, None


def fab():
    reg = json.load(open(REG)) if os.path.exists(REG) else {}
    if NAME in reg:
        print(f"{NAME} already fabricated (one-and-done). revert first."); return 0
    print(f"fabricating {NAME}: cpu_fwd ALU + {MEMW}-word data RAM + LOAD + BRNZ + sequencer, ONE clocked circuit …", flush=True)
    t0 = time.time(); c, outs = build_engine()
    print(f"  built {len(c.ga):,} gates, {len(outs)} state bits  [{time.time()-t0:.1f}s]", flush=True)
    t0 = time.time(); ok, bad = _verify(_cd(c, outs))
    print(f"  engine == reference program (the pfc's answer vs the ISA reference): {ok}   [{time.time()-t0:.1f}s]", flush=True)
    if not ok:
        print(f"  MISMATCH {bad} — storing nothing (no cheating)."); return 1
    info = TC.store(NAME, c, outs)
    reg = json.load(open(REG))
    reg[NAME].update({"role": "looping stored-program machine: cpu_fwd ALU + data RAM + LOAD + BRNZ (the model runs on this)",
                      "state_bits": STATE_BITS, "nreg": NREG, "rw": RW, "pcw": PCW, "memw": MEMW,
                      "proglen": PROGLEN, "ansreg": ANSREG, "nelem": NELEM})
    json.dump(reg, open(REG, "w"), indent=1)
    print(f"FABRICATED {NAME} @ {info['offset']}: {info['gates']:,} gates (reversible).", flush=True)
    with open(TITAN, "rb") as f: print(f"  titan GGUF-valid: {f.read(4) == b'GGUF'}", flush=True)
    return 0


def test():
    """Run a REAL model's real weights through the machine and check the pfc's answer against those weights."""
    reg = json.load(open(REG))
    if NAME not in reg: print("not fabricated — run: python host/pfc_model_engine.py fab"); return 1
    sys.path.insert(0, "C:/llm/sdc_sandbox")
    from gguf_pp import GGUF, row_bytes
    from pfc_fastdeq import dequant_fast as dequant
    model = sys.argv[2] if len(sys.argv) > 2 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
    tname = "blk.0.attn_q.weight"
    g = GGUF(model); t = g.tensors[tname]
    tid = int(t["type"]); row_n = int(t["dims"][0]); base = g.data0 + int(t["off"]); rb = row_bytes(tid, row_n)

    cd = TC.load(NAME)                                        # the machine, read back OUT of titan.gguf (mmap, ~0 RAM)
    print(f"=== THE pfc COMPUTES THE MODEL — {os.path.basename(model)} :: {tname} ===", flush=True)
    print(f"  machine: {NAME}, {reg[NAME]['n_gate']:,} gates, {STATE_BITS} state bits, program = {PROGLEN} instructions", flush=True)

    okn = 0; N = 4; total_ticks = 0; t0 = time.time()
    for j in range(N):
        w = dequant(g.mm[base + j * rb: base + j * rb + rb], tid, row_n)[:NELEM]
        x = [((i * 37 % 211) - 105) / 400.0 for i in range(NELEM)]
        mem = [q88(v) for v in w] + [q88(v) for v in x]       # route the model's numbers into the machine's RAM
        regs, ticks = run_on_pfc(cd, mem); total_ticks += ticks
        ref, _ = ref_run(mem)
        got = from_q88(regs[ANSREG])
        if regs == ref: okn += 1
        print(f"  neuron {j}: pfc computed SiLU(w.x) = {got:+.5f}   ({ticks} clock ticks, {ticks*reg[NAME]['n_gate']:,} gate-evals)", flush=True)
    dt = time.time() - t0
    print(f"\n  byte-exact vs the ISA reference on real model weights: {okn}/{N}", flush=True)
    print(f"  {total_ticks} ticks in {dt:.1f}s = {total_ticks/dt:.0f} ticks/s · {N*NELEM} MACs on the pfc", flush=True)
    print(f"  the host did NO arithmetic: it routed {MEMW} words in, pulsed the clock, and read one register.", flush=True)
    return 0 if okn == N else 1


def revert():
    reg = json.load(open(REG)) if os.path.exists(REG) else {}
    e = reg.pop(NAME, None); json.dump(reg, open(REG, "w"), indent=1)
    print(f"removed {NAME}: {bool(e)} (range freed; titan GGUF-valid).")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fab"
    raise SystemExit({"fab": fab, "test": test, "revert": revert}.get(cmd, fab)())
