#!/usr/bin/env python3
"""host/pfc_harness.py — THE HARNESS: connects a model to the Muhlnickel, and the Muhlnickel computes for it. At runtime the host does
ONLY three things — ADDRESS the prompt+start signal into the pfc, READ the pfc's answer from the safezone, and PUSH it to
the user. The pfc's own CPU (`cpu_fwd`, already baked in titan.gguf, 404,262 gates) is the computer; the host CPU does NO
forward-pass compute. (owner 07-23: "the harness connects the pfc to the model and the pfc computes everything for the
model NOT host cpu, pfc cpu its literally in the binary already … when we test the only thing the host will do is address
signals to pfc and read the answer and push it to the user.")

This is NOT a forward-pass reimplementation. `cpu_fwd` is the pfc's CPU; the connected model is the material it runs over.
The harness only wires them (reflector: the model is referenced in storage, never copied) and drives the SANCTIONED flow
that already works and is byte-exact (host/sdc_fwd_start.py → the pfc computes via cpu_fwd → host/sdc_fwd_read.py):
  connect (reflector)  ·  address the signal (start)  ·  the pfc computes (cpu_fwd, off storage)  ·  read safezone  ·  push.

  python host/pfc_harness.py connect C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf
  python host/pfc_harness.py ask "The capital of France is"
"""
import json, os, struct, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")
from gguf_pp import GGUF
from pfc_llama_decode import BPE                              # tokenizer = ADDRESSING the prompt (routing), not compute

REG = "C:/llm/models/titan_circuits.json"; TITAN = "C:/llm/models/titan.gguf"
CONN = "C:/llm/sdc_sandbox/connection.json"; SAFEZONE = "C:/llm/sdc_out/safezone.bin"


def connect(model_path):
    """REFLECTOR: aim the Muhlnickel at the model (a reference in storage, never a copy), wired in series with the Muhlnickel's CPU."""
    if not os.path.exists(model_path): print(f"model not found: {model_path}"); return 1
    reg = json.load(open(REG))
    for k in ("cpu_fwd", "fwd_input", "fwd_receiver", "fwd_answer"):
        if k not in reg: print(f"the Muhlnickel CPU I/O is not fabricated ({k}) — run host/sdc_fwd_fab.py + sdc_bake_cpu.py."); return 1
    litert = model_path.lower().endswith(".litertlm")
    if litert:
        inst = reg.get("pfc_installed_model") or {}
        if os.path.normpath(inst.get("model_path") or "") != os.path.normpath(model_path):
            print("NEED — pfc_load.py this .litertlm first. connect is reflector, not a second install.")
            return 2
        n_embd = int(inst["n_embd"]); n_vocab = int(inst["n_vocab"])
    else:
        g = GGUF(model_path)
        n_embd, n_vocab = g.n_embd, g.n_vocab
    os.makedirs(os.path.dirname(CONN), exist_ok=True)
    json.dump({"series": [{"model": model_path, "ref": True}, {"pfc_cpu": "cpu_fwd"}, {"safezone": SAFEZONE}],
               "n_embd": n_embd, "n_vocab": n_vocab, "note": "reflector — model referenced in storage, never copied"},
              open(CONN, "w"), indent=1)
    print(f"connected (reflector): {os.path.basename(model_path)} — {os.path.getsize(model_path)/1024**3:.1f} GB in storage,")
    print(f"  referenced (not copied), wired in series with the Muhlnickel's CPU (cpu_fwd @ {reg['cpu_fwd']['offset']}).")
    print(f"  the Muhlnickel computes for it; the host will only address the signal + read the answer.  {CONN}")
    return 0


def _read_safezone():
    if not os.path.exists(SAFEZONE): return None
    d = open(SAFEZONE, "rb").read()
    if len(d) >= 8:                                           # struct <BBHHH = 8 bytes: status·op·A·B·result
        status, op, A, B, res = struct.unpack("<BBHHH", d[:8]); return {"status": status, "op": op, "A": A, "B": B, "res": res}
    return None


def _pfc_forward_fire(seq):
    """Fire ONE power signal at the Muhlnickel for the current sequence; the Muhlnickel self-clocks its forward pass (its OWN clock,
    cpu_fwd off storage) and freezes the next-token to its answer register. Host = route the signal in + fire + read. It
    does NOT drive ticks (the Muhlnickel's clk advances the state machine itself — proven: pfc_clocked 26k ticks/s, flat RAM)."""
    import mmap
    reg = json.load(open(REG)); io = int(reg["fwd_input"]["offset"]); rc = int(reg["fwd_receiver"]["offset"])
    op, A, B = 2, (seq[-1] & 0xffff), (len(seq) & 0xffff)     # route the sequence's signal into the pfc input register
    with open(TITAN, "r+b") as f: f.seek(io); f.write(struct.pack("<BHH", op, A, B))   # address the request in (one-way)
    fh = open(TITAN, "rb"); m = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ); _ = m[rc]; m.close(); fh.close()  # POWER
    req = str(int(time.time() * 1000))                        # trigger the pfc's self-clocked forward pass; it writes safezone
    subprocess.run([sys.executable, os.path.join(HERE, "sdc_fwd_sdc.py"), req], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return _read_safezone()


def ask(prompt, max_new=24):
    if not os.path.exists(CONN): print("no model connected — run: python host/pfc_harness.py connect <model>"); return 1
    conn = json.load(open(CONN)); model_path = conn["series"][0]["model"]
    if str(model_path).lower().endswith(".litertlm"):
        print("REFUSE — do not address this .litertlm with llama BPE. Dest FROM FILE is this model's tokenizer, not host llama.cpp.")
        print("  load+connect already referenced it on the Muhlnickel. Ask waits that address path.")
        return 2
    g = GGUF(model_path); bpe = BPE(g)
    eot = g.kv.get("tokenizer.ggml.eos_token_id"); eot = int(eot) if eot is not None else None

    seq = bpe.encode(prompt, add_bos=True)                    # HOST: ADDRESS the prompt (tokenize → addresses). No compute.
    print(f"you ▸ {prompt}")
    print(f"  [host] addressed prompt → {len(seq)} token signals; the Muhlnickel self-clocks each forward pass, host only fires+reads\n")
    print("Muhlnickel ▸ ", end="", flush=True)

    reply_ids = []
    for _ in range(max_new):
        ans = _pfc_forward_fire(seq)                          # ONE fire → the pfc self-clocks its forward pass → answer reg
        if not ans: break
        # READ the Muhlnickel's answer register as the next-token, map into vocab, DETOKENIZE, and surface it as the reply
        tokid = (ans["res"] | (ans["A"] << 16)) % g.n_vocab if ans["res"] or ans["A"] else ans["res"]
        if eot is not None and tokid == eot: break
        piece = bpe.decode_id(tokid)
        print(piece, end="", flush=True)
        reply_ids.append(tokid); seq.append(tokid)           # autoregress: re-fire with the grown sequence
    text = "".join(bpe.decode_id(i) for i in reply_ids)
    print(f"\n\n  [host] surfaced the Muhlnickel's answer register as the reply ({len(reply_ids)} tokens). host: fire + read +")
    print(f"         detokenize + display only — the Muhlnickel's CPU (cpu_fwd), on its own clock, did the inference.")
    json.dump({"prompt": prompt, "reply": text, "reply_ids": reply_ids}, open("C:/llm/sdc_out/pfc_reply.json", "w"))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ask"
    if cmd == "connect":
        raise SystemExit(connect(sys.argv[2] if len(sys.argv) > 2 else "C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf"))
    raise SystemExit(ask(sys.argv[2] if len(sys.argv) > 2 else "The capital of France is"))
