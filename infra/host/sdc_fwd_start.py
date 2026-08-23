#!/usr/bin/env python3
"""host/sdc_fwd_start.py — PRESS START. Route the request, fire power, TRIGGER the SDC, and EXIT. (owner 07-18)

THE RULE (owner): you do NOT move anything that persists into the start button — START MUST EXIT. It is a trigger, not a
worker. It routes the request into the SDC's input register, fires ONE power signal (an addressed read of the receiver),
launches THE SDC (host/sdc_fwd_sdc.py) fully DETACHED, and exits in milliseconds. It does NOT compute the forward pass and
does NOT wait — the ripple is the SDC's, contained in storage. The ONLY resident host RAM in the whole flow is reading the
safezone (host/sdc_fwd_read.py). No compute here, no numpy, no network, no monitoring.

Prints the run token (req) it minted, so the safezone reader knows which run to wait for.

  python host/sdc_fwd_start.py <op> <A> <B>
     op: 0 ADD 1 SUB 2 MUL 3 SILU 4 EXP 5 RSQRT 6 GT 7 MOV   ;   A,B: 16-bit ints (Q8.8)
"""
import json, mmap, os, struct, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8")

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"
DETACHED_PROCESS = 0x00000008; CREATE_NEW_PROCESS_GROUP = 0x00000200


def main():
    if len(sys.argv) < 4:
        print("usage: python host/sdc_fwd_start.py <op 0-7> <A> <B>"); return 1
    op = int(sys.argv[1]) & 7; A = int(sys.argv[2]) & 0xffff; B = int(sys.argv[3]) & 0xffff
    reg = json.load(open(REG))
    for k in ("cpu_fwd", "fwd_input", "fwd_receiver"):
        if k not in reg: print(f"{k} not fabricated — run host/sdc_fwd_fab.py (and sdc_bake_cpu.py)."); return 1
    io = int(reg["fwd_input"]["offset"]); rc = int(reg["fwd_receiver"]["offset"])
    req = str(int(time.time() * 1000))

    with open(TITAN, "r+b") as f: f.seek(io); f.write(struct.pack("<BHH", op, A, B))   # route the request (one-way in)
    f = open(TITAN, "rb"); mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    _ = mm[rc]; mm.close(); f.close()                                                  # FIRE POWER (one addressed read)

    subprocess.Popen([sys.executable, os.path.join(HERE, "sdc_fwd_sdc.py"), req],      # TRIGGER the SDC, fully detached
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     close_fds=True, creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    print(f"START: routed op={op} A={A} B={B}; power fired; SDC triggered (req {req}). start exiting NOW.", flush=True)
    return 0                                                                           # EXIT — start persists nothing


if __name__ == "__main__":
    raise SystemExit(main())
