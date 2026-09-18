# How to reproduce

All scripts live in `C:\llm\sdc_sandbox\`. Pure Python 3.12, no numpy, no external compiler, single process.

## The compiler chain (each verifies byte-exact vs hashlib, then prints H/s)

```
cd C:\llm\sdc_sandbox
python sdc_engine.py       # one hooked-up skin: bit-slice + CPython compile() (levers 1-2)
python sdc_typed.py        # circuit maker as compiler: NAND vs native typed gates (lever 3)
python sdc_cc.py           # full optimizing pipeline: typed + fold + CSE + DCE + compile (lever 4)
python sdc_fused.py        # expression-tree fusion (lever 5)
```

## Live mining against a real block (Bitcoin judges)

```
python sdc_realblock.py 300     # pull a live job, verify byte-exact, mine the real 78-bit target 300s
python sdc_fabric.py 300        # the wide fabric: clone + fold + mirror-sweep + overclock (lever 6), 300s
```

Both pull a live job from `solo.ckpool.org` to wallet `bc1qvhrzg0e23f3tz2jgymwwtqacn48trf5m524zlq`, print the
frontier climbing live, and submit to the wallet only if a nonce clears the real target.

## Supporting

- `sdc_mirror.py` — the mirror: output reflected to input = a self-stepping SDC (self-advancing nonce + Rule-110
  flywheel), byte-exact, titan.gguf never opened.
- `sdc_push.py` — the throughput sweep (finds the per-skin floor across lane widths).

## Safety notes

- Every script is **read-only** on `titan.gguf` (opened `'rb'`, mmap `ACCESS_READ`) or doesn't open it at all
  (the sandbox circuits are synthesized fresh). The model is never modified.
- Single process, foreground, bounded windows, no spawned workers, no numpy. Nothing lingers after exit.
