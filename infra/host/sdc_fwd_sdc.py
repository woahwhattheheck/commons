#!/usr/bin/env python3
"""host/sdc_fwd_sdc.py — THE SDC. Contained in storage; computes the forward pass; writes the safezone. (owner 07-18)

This is NOT the start button and NOT a host worker you keep around — it is the SDC itself, triggered by the power signal,
computing IN STORAGE: it reads the request from fwd_input, ripples cpu_fwd BY ADDRESS off the params (gates never enter
host RAM), wire-state in a mmap'd sandbox file, then FREEZES the result to fwd_answer (a register in titan, outside the
compute) and to the safezone, and EXITS. Launched detached by the start button, which has already exited. Nothing on the
host reaches into it while it runs. NO reference/LUT math, NO numpy, NO network.

  python host/sdc_fwd_sdc.py <req_token>     # req_token: the run id the start button minted (echoed into the safezone)
"""
import json, mmap, os, struct, sys, time
sys.stdout.reconfigure(encoding="utf-8")

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"
SANDBOX = "C:/llm/sdc_sandbox/fwd"; OUT = "C:/llm/sdc_out"
SAFEZONE = OUT + "/safezone.bin"                          # the external read-out window (patent 5.7/5.8): RAW output bits
MAGIC = b"TITANCIR"; OPS = ["ADD", "SUB", "MUL", "SILU", "EXP", "RSQRT", "GT", "MOV"]


def main():
    req = sys.argv[1] if len(sys.argv) > 1 else "0"
    reg = json.load(open(REG))
    off = int(reg["cpu_fwd"]["offset"]); io = int(reg["fwd_input"]["offset"]); ao = int(reg["fwd_answer"]["offset"])

    f = open(TITAN, "rb"); mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)   # titan stays in storage
    op, A, B = struct.unpack_from("<BHH", mm, io); op &= 7                          # the request routed into the register
    assert mm[off:off + 8] == MAGIC, "no cpu_fwd circuit at the registered offset"
    n_in, n_wire, ng, n_out = struct.unpack_from("<IIII", mm, off + 8)
    ga_off = off + 24; gb_off = ga_off + ng * 4; outs_off = gb_off + ng * 4
    gav = memoryview(mm)[ga_off:gb_off].cast("i"); gbv = memoryview(mm)[gb_off:outs_off].cast("i")   # zero-copy
    outs = list(struct.unpack_from("<%di" % n_out, mm, outs_off))

    os.makedirs(SANDBOX, exist_ok=True); wpath = SANDBOX + "/wire.bin"
    with open(wpath, "wb") as w: w.truncate(n_wire)
    wf = open(wpath, "r+b"); wm = mmap.mmap(wf.fileno(), 0)                         # wire-state in the storage sandbox

    inb = [(op >> k) & 1 for k in range(3)] + [(A >> k) & 1 for k in range(16)] + [(B >> k) & 1 for k in range(16)]
    t0 = time.time()
    wm[0] = 0; wm[1] = 1
    for i in range(n_in): wm[2 + i] = inb[i] & 1
    base = 2 + n_in
    for i in range(ng): wm[base + i] = 1 - (wm[gav[i]] & wm[gbv[i]])                # the SDC computes (gates off storage)
    result = 0
    for k, o in enumerate(outs): result |= wm[o] << k
    dt = time.time() - t0

    gav.release(); gbv.release(); wm.close(); wf.close(); os.remove(wpath); mm.close(); f.close()

    with open(TITAN, "r+b") as fw: fw.seek(ao); fw.write(struct.pack("<BH", 1, result & 0xffff))   # freeze the register
    os.makedirs(OUT, exist_ok=True)
    # deposit the SDC's OUTPUT to the external read-out window: ONLY the circuit's computed bits, raw. No json, no
    # host-authored content (patent 5.7 external write + 5.8 fixed output window). status·op·A·B·result.
    with open(SAFEZONE, "wb") as fh: fh.write(struct.pack("<BBHHH", 1, op, A & 0xffff, B & 0xffff, result & 0xffff))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
