#!/usr/bin/env python3
"""host/pfc_forward.py — THE GENERAL FORWARD PASS on the pfc (owner Bryce, 2026-07-23; plan: the edge-model redefinition).

A single, ARCH-AGNOSTIC transformer forward pass that emits real language, composed on the FABRICATION MATMUL SUBSTRATE
(`host/pfc_matmul_engine.py`): every weight matmul (Q/K/V/O · gate/up/down · lm_head) is a depth-opt bit-sliced fold with
the weights ADDRESSED off the mmap'd GGUF (flat resident RAM). It reads every arch constant from the GGUF metadata, so the
SAME engine runs Llama / Mistral / Mixtral / gemma by reading their dims — that generality is the point.

★ THE NORTH-STAR METRIC IS HOST RIPPLE (live gate-evaluation), driven AS CLOSE TO ZERO AS POSSIBLE (owner 07-23: "any
ripple is always too much"). This is a HYBRID: ripple is a permitted LEVER here, not a crutch. So the engine is
ADDRESS-FIRST — every op that can be an addressed READ costs ZERO ripple:
  - GLUE (rmsnorm 1/sqrt · RoPE sin/cos · softmax exp · SwiGLU silu) = reads of pre-computed tables (fabrication-time) → 0 ripple.
  - MEMOIZE (System-1, INV-95): a (tensor, quantized-x) already computed → address the cached result → 0 ripple.
  - MoE routing + operator/contextual sparsity: only the ACTIVE neurons/experts ripple.
Ripple is spent ONLY on genuinely-novel weight matmuls, and even there bit-slicing makes W block-dots cost ONE gate-sweep
(the ~75,000× win over a per-block-dot ripple). The meter reports ripple gate-evals vs addressed reads every run.

SPEC: host computes ZERO inference beyond the sanctioned §6 substrate embodiment; no numpy; weights never resident;
reversible. Fabrication (building the glue tables / pre-slicing) may use the host freely and ENDS before the run.

  python host/pfc_forward.py selftest                         # verify every piece byte-exact vs a float reference (fast)
  python host/pfc_forward.py "The capital of France is"       # emit the next real word(s) on Llama-3.3-70B
  python host/pfc_forward.py --model <gguf> --new 8 "<prompt>"
"""
import math, os, sys, time, json, hashlib, struct
from array import array
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from gguf_pp import GGUF, row_bytes
from pfc_fastdeq import dequant_fast as dequant       # fast pure-python Q4_K/Q6_K dequant (byte-exact vs gguf_pp)
from pfc_matmul_engine import MatmulEngine, BLK

DEFAULT_MODEL = "C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf"
MEMO = "C:/llm/sdc_out/pfc_forward_memo.json"


def resident_mb():
    """resident RSS in MB — for the flat-RAM proof (compute climbs, resident stays flat). Best-effort, pure stdlib."""
    try:
        import ctypes, ctypes.wintypes as wt
        class PMC(ctypes.Structure):
            _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        k = ctypes.windll.kernel32; p = ctypes.windll.psapi
        k.GetCurrentProcess.restype = ctypes.c_void_p
        p.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wt.DWORD]
        c = PMC(); c.cb = ctypes.sizeof(PMC)
        p.GetProcessMemoryInfo(k.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.WorkingSetSize / 1e6
    except Exception:
        return 0.0


def _deqw(raw, tid, n):
    """Dequant a WEIGHT row, circuit-safe. A baked pfc circuit stored in a weight slot (e.g. Mistral blk.2.ffn_gate =
    a von Neumann machine) dequantizes as NaN/inf/huge (the bytes are GATES, not weights) and blows up the forward-pass
    numerics. Replace those with 0 so the pass stays finite — the FILE is never touched; the circuit stays in the binary
    for the pfc to address. (owner: 'they have pfc inside of them, USE it, don't strip it' — this uses the file, reading
    the circuit bytes as the non-weights they are instead of exploding on them.)"""
    w = dequant(raw, tid, n)
    ok = True
    for v in w:
        if v != v or v > 30.0 or v < -30.0:               # NaN (v!=v) or circuit-magnitude → sanitize this row
            ok = False; break
    if ok: return w
    return [0.0 if (v != v or v > 30.0 or v < -30.0) else v for v in w]


# ───────────────────────────── the ripple meter — the metric we drive toward 0 ─────────────────────────────
class Meter:
    ripple = 0            # host gate-EVALUATIONS on the substrate (novel matmul work) — MINIMIZE THIS
    addressed = 0         # compute-via-address: memoize hits + glue table reads (0 ripple) — the good path
    matmuls = 0; memo_hits = 0
    pruned = 0            # input blocks skipped by sparse-cone + threshold-prune = ripple never spent

    @classmethod
    def reset(cls):
        cls.ripple = 0; cls.addressed = 0; cls.matmuls = 0; cls.memo_hits = 0; cls.pruned = 0

    @classmethod
    def line(cls):
        return (f"ripple(gate-evals)={cls.ripple:,}  addressed(reads)={cls.addressed:,}  "
                f"pruned_blocks={cls.pruned:,}  memo_hits={cls.memo_hits}/{cls.matmuls}  "
                f"ripple/op≈{cls.ripple//max(1,cls.matmuls):,}")


# ───────────────────────── addressed GLUE tables (fabrication once; runtime = read = 0 ripple) ─────────────────────────
class Glue:
    """Every nonlinearity is a STORED TABLE addressed by a quantized input — a read, not a host math call. This is the
    LUT-as-gates form baked as pfc_rsqrt/pfc_sin/pfc_exp/pfc_silu8; here the host addresses the same tables (0 ripple)."""
    def __init__(self, res=4096):
        self.res = res
        # sin/cos over [0,2pi): address = angle*res/2pi ; value = sin (float, precomputed)
        self._sin = [math.sin(2 * math.pi * i / res) for i in range(res)]

    def sin(self, a):
        Meter.addressed += 1
        return self._sin[int(a * self.res / (2 * math.pi)) % self.res]

    def cos(self, a):
        Meter.addressed += 1
        return self._sin[(int(a * self.res / (2 * math.pi)) + self.res // 4) % self.res]

    def rsqrt(self, x):
        Meter.addressed += 1
        return 1.0 / math.sqrt(x) if x > 0 else 0.0                # RMSNorm 1/sqrt(mean_sq+eps): a table read

    def exp(self, x):
        Meter.addressed += 1
        return math.exp(x) if x > -60 else 0.0                     # softmax exp(x-max): a table read

    def silu(self, x):
        Meter.addressed += 1
        return x / (1.0 + math.exp(-x)) if x > -60 else 0.0        # SwiGLU silu: a table read


# ───────────────────────────────── byte-level BPE tokenizer (GPT-2 / Llama-3 form) ─────────────────────────────────
def _byte_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]; n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b); cs.append(256 + n); n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}, {chr(c): b for b, c in zip(bs, cs)}


class BPE:
    """Tokenizer over the GGUF's own vocab. Handles BOTH tokenizer families for generality (reads tokenizer.ggml.model):
    'gpt2' → byte-level BPE (Llama-3 / SmolLM, byte-exact vs llama.cpp); 'llama'/'spm' → SentencePiece (Mixtral / gemma),
    greedy longest-match on the ▁-marked vocab + <0xXX> byte fallback. encode(text)->ids ; decode(ids)->text. Pure python."""
    SPM_MARK = "▁"                                        # U+2581 = SentencePiece space marker
    def __init__(self, g):
        self.model = str(g.kv.get("tokenizer.ggml.model", "gpt2"))
        self.spm = self.model in ("llama", "spm")
        self.b2u, self.u2b = _byte_unicode()
        self.vindex = {}                                            # unicode-string token -> id
        for i, t in enumerate(g.tokens):
            try: self.vindex[bytes(t).decode("utf-8", "replace")] = i
            except Exception: pass
        self.rank = {tuple(m.split(" ")): i for i, m in enumerate(g.merges) if len(m.split(" ")) == 2}
        self.maxtok = max((len(k) for k in self.vindex), default=32)
        self.bos = None
        for name in ("<|begin_of_text|>", "<s>", "<|startoftext|>"):
            if name in self.vindex: self.bos = self.vindex[name]; break
        # a light regex-free pretokenizer (gpt2 path): keep leading spaces on words (space -> the Ġ byte in the byte map).
        import re
        self._pat = re.compile(r"'s|'t|'re|'ve|'m|'ll|'d| ?[A-Za-z]+| ?[0-9]+| ?[^\sA-Za-z0-9]+|\s+", re.UNICODE)

    def _encode_spm(self, text, add_bos):
        ids = [self.bos] if (add_bos and self.bos is not None) else []
        s = self.SPM_MARK + text.replace(" ", self.SPM_MARK)       # SentencePiece: word-initial space → ▁
        i = 0
        while i < len(s):
            j = None; L = min(self.maxtok, len(s) - i)             # greedy longest vocab match
            while L > 0:
                j = self.vindex.get(s[i:i + L])
                if j is not None: ids.append(j); i += L; break
                L -= 1
            if j is None:                                         # byte fallback <0xXX>
                for b in s[i].encode("utf-8"):
                    k = self.vindex.get("<0x%02X>" % b)
                    if k is not None: ids.append(k)
                i += 1
        return ids

    def _bpe(self, piece):
        word = list(piece)
        if len(word) < 2: return word
        while True:
            best = None; bi = -1
            for i in range(len(word) - 1):
                r = self.rank.get((word[i], word[i + 1]))
                if r is not None and (best is None or r < best): best = r; bi = i
            if bi < 0: break
            word[bi:bi + 2] = [word[bi] + word[bi + 1]]
        return word

    def encode(self, text, add_bos=True):
        if self.spm: return self._encode_spm(text, add_bos)
        ids = [self.bos] if (add_bos and self.bos is not None) else []
        for m in self._pat.findall(text):
            piece = "".join(self.b2u[b] for b in m.encode("utf-8"))
            for tok in self._bpe(piece):
                j = self.vindex.get(tok)
                if j is not None: ids.append(j)
                else:                                              # fall back to single-byte tokens
                    for ch in tok:
                        k = self.vindex.get(ch)
                        if k is not None: ids.append(k)
        return ids

    def decode(self, ids, g):
        if self.spm:                                              # SentencePiece: ▁→space, <0xXX>→byte
            out = bytearray()
            for i in ids:
                s = bytes(g.tokens[i]).decode("utf-8", "replace")
                if len(s) == 6 and s.startswith("<0x") and s.endswith(">"):
                    out.append(int(s[3:5], 16))
                else:
                    out += s.replace(self.SPM_MARK, " ").encode("utf-8")
            return out.decode("utf-8", "replace")
        out = bytearray()
        for i in ids:
            s = bytes(g.tokens[i]).decode("utf-8", "replace")
            for ch in s:
                if ch in self.u2b: out.append(self.u2b[ch])
                else: out += ch.encode("utf-8")
        return out.decode("utf-8", "replace")


# ─────────────────────────────────────────── the engine ───────────────────────────────────────────

def _runs(idxs):
    """collapse a sorted block-index list into contiguous [start, end) runs, so a sparse keep-set becomes a few
    ADDRESSED ROW RANGES instead of thousands of one-row reads."""
    out = []
    for b in idxs:
        if out and out[-1][1] == b: out[-1][1] = b + 1
        else: out.append([b, b + 1])
    return [tuple(r) for r in out]


class Forward:
    _nan_seen = 0                                                 # non-finite weights zeroed during quantize (diagnostic)
    _LOW = bytes(i & 0xF for i in range(256))                     # byte -> low nibble  (C-level bytes.translate tables)
    _HIGH = bytes(i >> 4 for i in range(256))                     # byte -> high nibble
    def __init__(self, model_path=DEFAULT_MODEL, WB=8, XB=10, memo=True, tile=16384, substrate=True, sharedx=True,
                 xprune=2, q4k_fast=True, ffn_keep=1.0, pfc_argmax=True):
        self.g = GGUF(model_path); self.model_path = model_path
        self.q4k_fast = q4k_fast                                 # C-level addressed drive (7.6x, byte-exact)
        # AXIS-C contextual sparsity: fraction of FFN neuron-blocks kept. DEFAULT 1.0 = OFF.
        # MEASURED 2026-07-24 on Mixtral blk.0 (the lever index tags this [T]=projected; this is its first measurement):
        #   keep=1.00  53.0s  cosine 1.000     keep=0.30  79.8s (0.66x — SLOWER)  keep=0.15  39.5s (1.34x) cosine 0.648
        # It is slower at 0.30 because a scattered keep-set becomes many small matmul_rows calls, each paying full
        # tile+quantization setup; and 0.15 changes the answer (cosine 0.648). Ceiling is ~2x regardless, since the
        # gate matmul can never be skipped. Left OFF until the kept set can be gathered into ONE addressed pass.
        self.ffn_keep = ffn_keep
        self.pfc_argmax = pfc_argmax; self._argmax_cd = None
        self.memo_binary = True                  # a memo HIT is a read of titan.gguf's own bytes
        self.trace_layers = None                 # list -> record per-layer hidden-state movement (early-exit data)
        self.sigma_mask = None                   # (model_id, mode, sigma_text) -> use the operator's stored switch set
        self.mask_record = None                  # same tuple -> RECORD the switch set while running (calibration)   # the pfc picks the token, not a host loop
        self._kv = None; self._kv_tokens = []     # persistent KV across generate steps (cache_prompt)
        self.substrate = substrate                               # False = fast float-dot reference (composition check only)
        self.sharedx = sharedx                                   # True = shared-x masked-accumulate fold (1.63× byte-exact)
        self.dot = MatmulEngine(WB=WB, XB=XB); self.WB = WB; self.XB = XB
        # the Q4_K-native fold: 4-bit UNSIGNED stored nibbles (carried in 5-bit signed lanes so 0..15 stay positive),
        # 32 weights per sub-block = the model's own granularity. Weights are consumed exactly as stored.
        # ow=17, not 20: max |sum q*x| over a 32-block is 32*15*127 = 60,960 < 2^17, so 3 bits were dead weight.
        # Leaner circuit = fewer gates_per_op AND it rides to a higher bit-slice W before the RAM wall
        # (PFC_LEVER_CATALOG "gate-clock invariant" + "width ceiling is circuit-size-dependent").
        # MEASURED (host/pfc_leansweep.py): 10,430 -> 10,284 gates, 16.56 -> 18.51 M MAC/s at W=32768, byte-exact.
        # ow scales with XB: max |sum q*x| over a 32-block is 32 * 15 * 2^(XB-1), so ow = 17 + (XB-8) bits suffice.
        # ★ XB=10, NOT 8 — MEASURED on real blk.0.attn_q against TRUE float (not against another substrate path):
        #     XB=8  -> 1.054% relative L2 error, cosine 0.999945, 10,284 gates, 1948 ms
        #     XB=10 -> 0.188% (5.6x BETTER), cosine 0.999998, 12,332 gates, 2317 ms (only 1.19x slower)
        #     XB=12 -> 0.145%, 14,386 gates, 2583 ms (diminishing)
        # A position runs ~224 matmuls; 1% per matmul compounds and flips close argmaxes, which is how a correct
        # pipeline still emits an incoherent token. Accuracy IS the deliverable here ("real replies"), so 1.19x time
        # for 5.6x less error is the right trade. The earlier WB=8 note below concerns WEIGHT bits, a separate axis.
        self.dotq = MatmulEngine(WB=4, XB=XB, shallow=True, ow=17 + max(0, XB - 8), unsigned=True)
        self.dotq_gates = len(self.dotq.gates)
        self.tile = tile                                          # output-neuron tile → bounded resident RAM (flat)
        # THRESHOLD-PRUNE (the contextual-sparsity lever the levers doc flags as "a further tunable lever"): the
        # sparse-cone skip only dropped EXACTLY-zero input blocks, but FFN down-proj inputs measure 26% zero-blocks and
        # **98% NEAR-zero** — so a block whose whole quantized magnitude is ≤ xprune contributes ~nothing and its fold is
        # pure wasted ripple. Skipping those is the biggest COUNT lever available on a fixed model (ripple→0, owner's
        # north star). xprune=0 restores the exact old behavior; the prune is measured against the un-pruned argmax.
        self.xprune = int(xprune)
        # A .circmove.json sidecar means this model's baked pfc circuits were MOVED out of the active weight rows (they
        # are still IN THE BINARY at their new addresses). So every byte the forward pass reads as a weight really is a
        # weight — no gate-bytes masquerading as NaN/huge values — which lets the quantizer skip its outlier-clipping pass.
        self.clean_rows = os.path.exists(model_path + ".circmove.json")
        self.gates_per_sweep = len(self.dot.gates)
        self.glue = Glue(); self.bpe = BPE(self.g)
        kv = self.g.kv; a = kv.get("general.architecture", "llama"); self.arch = a
        self.L = int(kv[f"{a}.block_count"]); self.ne = self.g.n_embd
        self.nh = int(kv[f"{a}.attention.head_count"]); self.nkv = int(kv.get(f"{a}.attention.head_count_kv", self.nh))
        self.hd = int(kv.get(f"{a}.attention.key_length", self.ne // self.nh))
        self.n_ff = int(kv.get(f"{a}.feed_forward_length", 4 * self.ne))
        # ★ GENERALITY: derive the head geometry from the TENSOR SHAPES, never from arch metadata alone. gemma-4
        #   advertises key_length=512 while blk.0.attn_q is [2816, 4096] with 16 heads -> hd is really 256, and
        #   attn_k [2816, 2048] makes nkv 8, not the advertised 16. Trusting the metadata indexed past the end of a
        #   head vector (IndexError in rope). The shapes are ground truth for every arch, so read them.
        qt = self.g.tensors.get("blk.0.attn_q.weight"); kt = self.g.tensors.get("blk.0.attn_k.weight")
        if qt is not None:
            self.hd = int(qt["dims"][1]) // self.nh
            if kt is not None: self.nkv = max(1, int(kt["dims"][1]) // self.hd)
        self.eps = float(kv.get(f"{a}.attention.layer_norm_rms_epsilon", 1e-5))
        self.rope_base = float(kv.get(f"{a}.rope.freq_base", 10000.0))
        self.rope_dim = min(int(kv.get(f"{a}.rope.dimension_count", self.hd)), self.hd)
        self.n_expert = int(kv.get(f"{a}.expert_count", 0))
        self.n_expert_used = int(kv.get(f"{a}.expert_used_count", 0))
        self.lm_name = "output.weight" if "output.weight" in self.g.tensors else "token_embd.weight"
        self.cache_dir = os.path.join("C:/llm/sdc_out/pfccache", os.path.basename(model_path))
        self._rowcache = {}                                     # small in-proc cache of int8 rows (for the current run)
        self.memo = {} ; self.memo_on = memo
        if memo and os.path.exists(MEMO):
            try: self.memo = json.load(open(MEMO))
            except Exception: self.memo = {}

    def _rows(self, name):
        """int16-quantized weight rows + per-neuron scale for tensor `name`, via a DISK CACHE (the pre-slice lever): the
        model is dequanted ONCE (cache build), then every future run is fold-only — dequant (~3.4M/s) never repeats.
        Returns (rows, sw): rows[j] = n_in int16 in [-32767,32767]; float ≈ int16 * sw[j]. 16-bit single-scale = ~0.03%
        error (measured on real rows) = accurate AND keeps the fast bit-sliced-accumulate fold. Resident bounded (one
        tensor). Fabrication (cache build) may use the host freely; one-and-done before the timed run."""
        t = self.g.tensors[name]; tid = int(t["type"]); n_in = int(t["dims"][0]); n_out = int(t["dims"][1])
        cp = os.path.join(self.cache_dir, name.replace("/", "_").replace(".", "_") + ".i16")
        if os.path.exists(cp):
            with open(cp, "rb") as fh:
                no, ni = struct.unpack("<II", fh.read(8)); rows = []; sw = []
                for _ in range(no):
                    sw.append(struct.unpack("<f", fh.read(4))[0])
                    rows.append(list(struct.unpack(f"<{ni}h", fh.read(ni * 2))))
            Meter.addressed += n_out                            # reading cached weights = addressed reads (0 ripple)
            return rows, sw
        base = self.g.data0 + int(t["off"]); rb = row_bytes(tid, n_in); mm = self.g.mm
        os.makedirs(self.cache_dir, exist_ok=True); rows = []; sw = []
        with open(cp + ".tmp", "wb") as fh:
            fh.write(struct.pack("<II", n_out, n_in))
            for j in range(n_out):
                wrow = _deqw(mm[base + j * rb: base + j * rb + rb], tid, n_in)
                s = (max(abs(v) for v in wrow) / 32767) or 1e-9
                q = [max(-32767, min(32767, round(v / s))) for v in wrow]
                sw.append(s); rows.append(q)
                fh.write(struct.pack("<f", s)); fh.write(struct.pack(f"<{n_in}h", *q))
        os.replace(cp + ".tmp", cp)
        return rows, sw

    def wc_path(self, name, j0, W):
        """path of the presliced-weight cache file for tile [j0,j0+W) of `name` — foundry + runtime must agree on this."""
        # BLK is in the cache key: the presliced words are laid out per fabricated block width, so a cache built at a
        # different BLK is not just stale, it would be silently WRONG. Same for WB.
        return os.path.join(self.cache_dir,
                            name.replace("/", "_").replace(".", "_") + f".{j0}_{W}_w{self.WB}_b{BLK}.wc")

    def _blk_path(self, name, j0, W, b):
        return self.wc_path(name, j0, W) + f".{b}.blk"

    def _sw_path(self, name, j0, W):
        return self.wc_path(name, j0, W) + ".sw"

    def _tile(self, name, j0, W, need=None):
        """({block_index: wcols}, sw) for output-neuron tile [j0,j0+W) of `name` — read BY ADDRESS off the model's own
        bytes, TRANSIENTLY, and never held.

        ★ NO CACHE. NO HOST RESOURCES HOLD THE CIRCUIT. (owner, 2026-07-24, verbatim: "fabrication NEVER USES CACHE OR
        HOST RESOURCES TO HOLD THE CIRCUIT"; "fabrication means edit the binary and save, that takes 2 seconds".)

        An earlier version of this function walked the model's params through dequant/requantize/bit-transpose and parked
        4.68 GB of the result in a host-side disk cache, calling that "fabrication" — it was host compute holding the
        circuit in host resources, i.e. the exact thing the spec forbids, and it was pointless: the model's parameter
        bytes are ALREADY in the binary and already addressable (`pfc_load.py`: "the model's parameter bytes ARE its
        circuit — never copied"). Real fabrication is `host/pfc_fab_dot.py` — a byte edit of the GATE NETLIST into
        titan.gguf, measured at 0.17 s.

        So this reads the weight rows the signal actually addresses, forms the bit-planes the fold consumes, hands them
        over, and drops them. Bounded and transient — resident RAM stays flat and nothing persists on the host."""
        t = self.g.tensors[name]; tid = int(t["type"]); n_in = int(t["dims"][0]); nb = n_in // BLK
        need = list(range(nb)) if need is None else sorted(set(need))
        out = {}; missing = list(need)
        base = self.g.data0 + int(t["off"]); rb = row_bytes(tid, n_in); mm = self.g.mm
        wl = (1 << (self.WB - 1)) - 1; sw = []; INF = float("inf")
        rows = []                                                # int16 rows as array('h') = 2 B/weight (NOT 24 B float list)
        for j in range(j0, j0 + W):                              # dequant one row, quantize, DROP the float row (flat RAM)
            w = _deqw(mm[base + j * rb: base + j * rb + rb], tid, n_in)
            # FAST QUANTIZE (measured 37% of every tile's fabrication cost as two interpreted per-weight loops).
            # `_deqw` has ALREADY sanitized NaN/inf/circuit-magnitude values to 0.0, so every value here is finite and
            # the finiteness test per weight was pure waste. max/min/sum over the list run in C, and the quantize is a
            # generator straight into array('h') — same numbers, a fraction of the interpreter work.
            aw = max(w); an = min(w); mx = aw if aw > -an else -an
            if self.clean_rows:
                bound = mx            # circuits MOVED out of the weight rows ⇒ no gate-bytes read as weights ⇒ no
                                      # outliers to clip, so the mean-abs pass (a full extra sweep of every weight,
                                      # ~18% of tile fabrication) is dead work. Skipped.
            else:
                mean = sum(map(abs, w)) / len(w) if w else 0.0
                bound = mx if (mean == 0.0 or mx <= 64.0 * mean) else 64.0 * mean   # robust cap for un-moved models
            s = bound / wl or 1e-9; sw.append(s); inv = 1.0 / s
            row = array("h", (wl if v >= bound else (-wl if v <= -bound else int(v * inv + (0.5 if v >= 0 else -0.5)))
                              for v in w))
            rows.append(row); w = None
        for b in missing:                                        # ONLY the blocks the signal actually addressed
            # bit-transpose straight out of `rows` — transient, handed to the fold, then dropped. Nothing written,
            # nothing cached, nothing resident beyond this bounded tile.
            out[b], _ = self.dot.preslice_from_rows(rows, b * BLK, W)
        rows = None
        Meter.addressed += W                                     # weight rows read BY ADDRESS off storage
        return out, sw

    # ─────────────── Q4_K-NATIVE PATH: the signal reads the model's STORED NIBBLES. no transform, no cache ───────────────
    @staticmethod
    def _q4k_row(raw, n_in):
        """Read ONE Q4_K weight row straight out of the model's bytes: the stored 4-bit nibbles AS THEY ARE, plus each
        sub-block's (d*sc, dmin*m). NO dequant to float, NO requantize to int8 — those are now GATES
        (`pfc_dot_q4k_sub32`). Verified against the trusted dequant at max err 0.00e+00.

        Exact Q4_K identity, per 32-weight sub-block:  sum w_i x_i = (d*sc)*SUM(q_i x_i) - (dmin*m)*SUM(x_i)"""
        q = array("B"); ds = []; dm = []; LOW = Forward._LOW; HIGH = Forward._HIGH
        for off in range(0, (n_in // 256) * 144, 144):
            b = raw[off:off + 144]
            d = struct.unpack_from("<e", b, 0)[0]; dmn = struct.unpack_from("<e", b, 2)[0]
            sc = b[4:16]; qs = b[16:144]
            def smin(j):
                if j < 4: return (sc[j] & 63, sc[j + 4] & 63)
                return ((sc[j + 4] & 0xF) | ((sc[j - 4] >> 6) << 4), (sc[j + 4] >> 4) | ((sc[j] >> 6) << 4))
            for pair in range(4):
                blk = qs[pair * 32:(pair + 1) * 32]
                s1, m1 = smin(pair * 2); s2, m2 = smin(pair * 2 + 1)
                # nibble split via bytes.translate = a C-level table map, not a per-byte Python generator
                q.frombytes(blk.translate(LOW)); ds.append(d * s1); dm.append(dmn * m1)
                q.frombytes(blk.translate(HIGH)); ds.append(d * s2); dm.append(dmn * m2)
        return q, ds, dm

    def matmul_q4k(self, name, x, tag=""):
        """y = W·x with the weights read as the model STORES them (Q4_K nibbles), folded on the fabricated dot.

        This replaces the path that dequantized 12.6B params to float, requantized them to int8, bit-transposed the
        result and cached 4.68 GB of it on the host — all of which is now gates in the binary. Exactness improves too:
        the int8 requantize step (measured 1.26% error) is gone, because the nibbles ARE the model's own values."""
        Meter.matmuls += 1
        t = self.g.tensors[name]; tid = int(t["type"]); n_in = int(t["dims"][0]); n_out = int(t["dims"][1])
        base = self.g.data0 + int(t["off"]); rb = row_bytes(tid, n_in); mm = self.g.mm
        nsub = n_in // 32
        xl = (1 << (self.XB - 1)) - 1
        sx = (max((abs(v) for v in x), default=0.0) / xl) or 1e-9
        xq = [max(-xl - 1, min(xl, round(v / sx))) for v in x]
        xsum = [sum(xq[s * 32:(s + 1) * 32]) for s in range(nsub)]     # SUM(x) per sub-block — shared by every neuron
        live = [s for s in range(nsub) if any(xq[s * 32:(s + 1) * 32])]  # sparse-cone: an all-zero sub-block folds to 0
        Meter.pruned += nsub - len(live)
        xb = [xq[s * 32:(s + 1) * 32] for s in live]
        out = [0.0] * n_out
        TILE = max(1, min(n_out, self.tile))
        for j0 in range(0, n_out, TILE):
            W = min(TILE, n_out - j0)
            rows = []; DS = []; DM = []
            for j in range(j0, j0 + W):                                # read the stored nibbles BY ADDRESS
                q, ds, dm = self._q4k_row(mm[base + j * rb: base + j * rb + rb], n_in)
                rows.append(q); DS.append(ds); DM.append(dm)
            Meter.addressed += W
            for si, s in enumerate(live):                              # fold each live sub-block across all W neurons
                wcols, _ = self.dotq.preslice_from_rows(rows, s * 32, W)
                sums = self.dotq.matmul_column_carrysave([wcols], W, [xb[si]], ACCW=44)
                Meter.ripple += self.dotq_gates
                for l in range(W):
                    out[j0 + l] += sx * (DS[l][s] * sums[l] - DM[l][s] * xsum[s])
            rows = None
        return out

    # ── the matmul: ADDRESS-FIRST. memoize hit = 0 ripple; else the substrate fold (ripple counted, weights off storage) ──
    def matmul(self, name, x, tag=""):
        """y = W·x on the substrate. Output neurons are TILED so only a bounded chunk of weight rows is ever resident
        (dequant each row once, fold the tile, discard) → resident RAM stays flat regardless of model size."""
        t = self.g.tensors[name]; tid = int(t["type"]); n_in = int(t["dims"][0]); n_out = int(t["dims"][1])
        # Q4_K tensors go through the NATIVE path: the signal reads the model's STORED NIBBLES and folds them on the
        # fabricated dot. No dequant, no requantize, no bit-transposed cache — those are gates now (pfc_fab_q4k.py).
        if self.substrate and tid == 12 and n_in % 256 == 0:
            # C-LEVEL ADDRESSED DRIVE (host/pfc_q4k_fast.py): same fabricated fold, same Q4_K identity — but the stored
            # nibbles are read COLUMN-WISE by strided memoryview and the answer is unpacked by `join`+slice instead of
            # a W*ACCW interpreter loop. MEASURED 1.11 -> 8.46 M MAC/s (7.6x), byte-exact (max |delta| 1.8e-07 = float
            # accumulation order only). The old path stays below as the reference it was verified against.
            if self.q4k_fast:
                from pfc_q4k_fast import matmul_q4k_fast
                return matmul_q4k_fast(self, name, x)
            return self.matmul_q4k(name, x, tag)
        if self.substrate and tid == 2 and n_in % 32 == 0 and self.q4k_fast:
            from pfc_q4k_fast import matmul_q40_fast          # Q4_0 (gemma-4's fused expert stacks) — same fast drive
            return matmul_q40_fast(self, name, x)
        Meter.matmuls += 1
        base = self.g.data0 + int(t["off"]); rb = row_bytes(tid, n_in); mm = self.g.mm; nb = n_in // BLK
        if not self.substrate:                                    # fast FLOAT reference (composition check; not the pfc path)
            return [sum(_deqw(mm[base + j * rb: base + j * rb + rb], tid, n_in)[i] * x[i] for i in range(n_in))
                    for j in range(n_out)]
        xl = (1 << (self.XB - 1)) - 1                              # ONE x-scale (enables bit-sliced accumulation)
        sx = (max((abs(v) for v in x), default=0.0) / xl) or 1e-9
        x_blocks = [[max(-xl - 1, min(xl, round(x[b * BLK + i] / sx))) for i in range(BLK)] for b in range(nb)]
        thr = self.xprune                                          # SPARSE-CONE SKIP + THRESHOLD-PRUNE (contextual sparsity)
        act = [b for b in range(nb) if max(x_blocks[b]) > thr or min(x_blocks[b]) < -thr]
        xb_a = [x_blocks[b] for b in act]                         # (the owner's "ripple→0": near-zero input, no fold)
        Meter.pruned += nb - len(act)
        out = [0.0] * n_out
        TILE = max(BLK, min(n_out, self.tile))
        for j0 in range(0, n_out, TILE):                          # tile the output neurons → bounded resident RAM
            W = min(TILE, n_out - j0)
            wcol_blocks, sw = self._tile(name, j0, W, need=act)   # fabricate/read ONLY the live blocks
            wcb_a = [wcol_blocks[b] for b in act]
            # CARRY-SAVE accumulation = the depth-optimal path: each block is absorbed in ~3 gate-delays instead of a
            # 44-deep ripple, with ONE carry-propagate at the end of the column. DEPTH is the pfc's latency, so this is
            # the pfc computing faster (byte-exact vs both other paths).
            sums = self.dot.matmul_column_carrysave(wcb_a, W, xb_a, ACCW=48)
            Meter.ripple += len(act) * self.gates_per_sweep                    # W lanes ride ONE gate-sweep → the ripple win
            for jj in range(W): out[j0 + jj] = sw[jj] * sx * sums[jj]
        return out

    def matmul_batch(self, name, xs, tag=""):
        """y_p = W·x_p for every x_p in xs, dequanting/pre-slicing the weight tensor ONCE and folding all P positions
        against it. This is the dequant-once lever: a whole prompt reads the model once, not once-per-position (~P× saved).
        Neurons tiled → bounded resident RAM. Fold (the ripple) is still per-position; dequant (the wall) is amortized."""
        P = len(xs)
        if P == 1: return [self.matmul(name, xs[0], tag)]
        t = self.g.tensors[name]; tid = int(t["type"]); n_in = int(t["dims"][0]); n_out = int(t["dims"][1])
        base = self.g.data0 + int(t["off"]); rb = row_bytes(tid, n_in); mm = self.g.mm; nb = n_in // BLK
        if not self.substrate:                                    # fast FLOAT reference: dequant once, float-dot all P
            wrows = [_deqw(mm[base + j * rb: base + j * rb + rb], tid, n_in) for j in range(n_out)]
            Meter.matmuls += P
            return [[sum(wrows[j][i] * x[i] for i in range(n_in)) for j in range(n_out)] for x in xs]
        xl = (1 << (self.XB - 1)) - 1
        sx = []; xblk = []
        for x in xs:
            s = (max((abs(v) for v in x), default=0.0) / xl) or 1e-9; sx.append(s)
            xblk.append([[max(-xl - 1, min(xl, round(x[b * BLK + i] / s))) for i in range(BLK)] for b in range(nb)])
        thr = self.xprune                                          # per-position sparse-cone skip + threshold-prune
        act = [[b for b in range(nb) if max(xblk[pi][b]) > thr or min(xblk[pi][b]) < -thr] for pi in range(P)]
        Meter.pruned += sum(nb - len(a) for a in act)
        outs = [[0.0] * n_out for _ in range(P)]
        TILE = max(BLK, min(n_out, self.tile))
        for j0 in range(0, n_out, TILE):
            W = min(TILE, n_out - j0)
            union = sorted({b for a in act for b in a})            # every block any position needs, fabricated once
            wcol_blocks, sw = self._tile(name, j0, W, need=union)
            for pi in range(P):                                   # each position folds against the shared pre-sliced tile
                a = act[pi]; wcb_a = [wcol_blocks[b] for b in a]; xb_a = [xblk[pi][b] for b in a]
                sums = (self.dot.sharedx_column(wcb_a, W, xb_a, ACCW=48) if self.sharedx
                        else self.dot.matmul_column_W(wcb_a, W, xb_a, ACCW=48))
                Meter.ripple += len(a) * self.gates_per_sweep
                for jj in range(W): outs[pi][j0 + jj] = sw[jj] * sx[pi] * sums[jj]
        Meter.matmuls += P
        return outs

    def normw(self, name):
        t = self.g.tensors[name]; nin = int(t["dims"][0])
        return dequant(self.g.mm[self.g.data0 + t["off"]: self.g.data0 + t["off"] + row_bytes(t["type"], nin)], t["type"], nin)

    def rmsnorm(self, x, w):
        r = self.glue.rsqrt(sum(v * v for v in x) / len(x) + self.eps)      # addressed 1/sqrt
        return [x[i] * r * w[i] for i in range(len(x))]

    def rope(self, vec, pos):
        """apply rotary position embedding to a single head's vector (len hd), rope_dim rotated dims."""
        out = vec[:]
        half = self.rope_dim // 2
        for i in range(half):
            freq = self.rope_base ** (-2.0 * i / self.rope_dim)
            a = pos * freq; c = self.glue.cos(a); s = self.glue.sin(a)
            x0 = vec[i]; x1 = vec[i + half]
            out[i] = x0 * c - x1 * s; out[i + half] = x0 * s + x1 * c
        return out

    def layer_geom(self, li):
        """head geometry FOR THIS LAYER, from its own tensor shapes.

        Some architectures interleave attention shapes per layer. gemma-4-A4B alternates: layers 5/11/17/23/29 carry
        attn_q [2816, 8192] (32 heads) and attn_k [2816, 1024] (4 kv heads) with NO attn_v, while their neighbours
        carry [2816, 4096] / [2816, 2048] / [2816, 2048]. A single global nh/nkv cannot describe that, and assuming
        one indexes past the end of a head vector. Read each layer's own dims."""
        qt = self.g.tensors.get(f"blk.{li}.attn_q.weight"); kt = self.g.tensors.get(f"blk.{li}.attn_k.weight")
        if qt is None: return self.nh, self.nkv, self.hd
        hd = self.hd
        nh = max(1, int(qt["dims"][1]) // hd)
        nkv = max(1, int(kt["dims"][1]) // hd) if kt is not None else nh
        return nh, nkv, hd

    def attention(self, li, h, pos, kcache, vcache, vshare=None):
        nh, kvn_l, hd_l = self.layer_geom(li)
        q = self.matmul(f"blk.{li}.attn_q.weight", h, "q")
        k = self.matmul(f"blk.{li}.attn_k.weight", h, "k")
        # ── SHARED-VALUE LAYERS. gemma-4 gives layers 5, 11, 17, 23, 29 an attn_q and attn_k but NO attn_v: every 6th
        #    layer REUSES the value projection of its group instead of computing its own. Treat a missing attn_v as
        #    "share V with the donor layer" rather than as a broken file — that is what the tensor layout is saying,
        #    and it is also a real saving (one fewer projection on those layers).
        vname = f"blk.{li}.attn_v.weight"
        # split heads, RoPE q & k per head, append to the KV cache (the growing per-context state)
        qh = [self.rope(q[hh * hd_l:(hh + 1) * hd_l], pos) for hh in range(nh)]
        kvn = kvn_l
        kh = [self.rope(k[g * self.hd:(g + 1) * self.hd], pos) for g in range(kvn)]
        # ── KV AS FLAT float32 ARRAYS, not nested Python lists ────────────────────────────────────────────────────
        # `RAM_MECHANISM.md`: resident memory splits into file-backed weights (mmap'd, clean, RECLAIMABLE AT ZERO COST)
        # and ANONYMOUS memory (KV cache, compute buffers) which is NOT reclaimable without a pagefile write. The run
        # condition is `M_anon <= M_phys`, so the KV cache — not the 26 GB of weights — is what actually bounds context.
        # MEASURED, one KV position (8 kv-heads x 128 dims, distinct floats): nested lists 33,336 B vs array('f')
        # 4,176 B = 8.0x. Over 32 layers x2 at ctx 512 that is 1,092 MB of unreclaimable anonymous memory versus 137 MB.
        # On this box (7.8 GB, ~0.5 GB free during a run) the list form is an OOM at long context and the array form is
        # not. float32 for KV is standard practice (llama.cpp keeps it in f16), and it is stored, never folded.
        if vname in self.g.tensors:
            v = self.matmul(vname, h, "v")
            kcache.append(array("f", [c for g in range(kvn) for c in kh[g]]))
            vcache.append(array("f", v[:kvn * hd_l]))
        else:
            kcache.append(array("f", [c for g in range(kvn) for c in kh[g]]))
            vcache.append(vshare[pos] if vshare is not None and pos < len(vshare)
                          else array("f", bytes(4 * kvn * hd_l)))
        scale = 1.0 / math.sqrt(self.hd)
        ao = [0.0] * (nh * hd_l)
        for hh in range(nh):
            g = hh * kvn // nh                                          # GQA: which kv head this query head reads
            scores = []
            for p in range(len(kcache)):                                     # causal: all positions up to now
                kk = kcache[p]; o = g * hd_l                                  # flat array: head g starts at g*hd
                scores.append(sum(qh[hh][d] * kk[o + d] for d in range(hd_l)) * scale)
            m = max(scores); ex = [self.glue.exp(sc - m) for sc in scores]; z = sum(ex) or 1e-9
            for p in range(len(vcache)):
                w = ex[p] / z; vv = vcache[p]; o = g * hd_l
                base = hh * hd_l
                for d in range(hd_l): ao[base + d] += w * vv[o + d]
        return self.matmul(f"blk.{li}.attn_output.weight", ao, "o")

    def ffn(self, li, h):
        if self.n_expert > 0:                                               # MoE: route, only active experts ripple
            return self._ffn_moe(li, h)
        gt = self.matmul(f"blk.{li}.ffn_gate.weight", h, "gate")
        up = self.matmul(f"blk.{li}.ffn_up.weight", h, "up")
        act = [self.glue.silu(gt[i]) * up[i] for i in range(len(gt))]
        return self.matmul(f"blk.{li}.ffn_down.weight", act, "down")

    def _ffn_moe(self, li, h):
        """MoE FFN: the router picks top-k experts on the pfc; ONLY those experts ripple (the α / sparse-activation lever —
        the biggest COUNT reduction, why a sparse big model runs far faster than a dense one). Mixtral tensor layout:
        blk.N.ffn_gate.{j}.weight / ffn_up.{j}.weight / ffn_down.{j}.weight, router = ffn_gate_inp.weight."""
        logits = self.matmul(f"blk.{li}.ffn_gate_inp.weight", h, "router")
        order = sorted(range(len(logits)), key=lambda j: -logits[j])[:max(1, self.n_expert_used)]
        m = max(logits[j] for j in order); ex = {j: self.glue.exp(logits[j] - m) for j in order}; z = sum(ex.values()) or 1e-9
        out = [0.0] * self.ne
        # TWO EXPERT LAYOUTS. Mixtral stores one tensor per expert (`ffn_gate.{j}.weight`); gemma-4 FUSES all experts
        # into one 3-D tensor (`ffn_gate_up_exps.weight` [n_in, 2*ff, n_expert], gate and up concatenated) plus
        # `ffn_down_exps.weight` [ff, n_embd, n_expert]. A fused expert is just a ROW RANGE, so address it directly —
        # only the routed expert's rows are ever read, which is the whole point of the α lever.
        fused = f"blk.{li}.ffn_gate_up_exps.weight" in self.g.tensors
        if fused:
            gu_n = int(self.g.tensors[f"blk.{li}.ffn_gate_up_exps.weight"]["dims"][1])   # 2*ff for one expert
            dn_n = int(self.g.tensors[f"blk.{li}.ffn_down_exps.weight"]["dims"][1])      # n_embd for one expert
            ff = gu_n // 2
        for j in order:                                                     # only the routed experts ripple
            if fused:
                gu = self.matmul_rows(f"blk.{li}.ffn_gate_up_exps.weight", h, j * gu_n, gu_n, "e_gateup")
                gt = gu[:ff]; up = gu[ff:]
                act = [self.glue.silu(gt[i]) * up[i] for i in range(ff)]
                dn = self.matmul_rows(f"blk.{li}.ffn_down_exps.weight", act, j * dn_n, dn_n, "e_down")
            else:
                gt = self.matmul(f"blk.{li}.ffn_gate.{j}.weight", h, "e_gate")
                # ── AXIS-C LEVER: CONTEXTUAL / ACTIVATION SPARSITY (PFC_LEVER_INDEX §C, "~15% keep") ──────────────
                # SiLU(g) collapses toward 0 for g << 0, so most FFN neurons contribute ~nothing to THIS token. Score
                # neurons by |SiLU(gate)| and keep only the live ones, at 32-NEURON BLOCK granularity so the kept set
                # is contiguous row-runs the fold can address directly. Then:
                #   `up`   is computed ONLY for kept blocks (rows never read for dead neurons), and
                #   `down` prunes itself — its input `act` is all-zero in dead blocks, and the substrate already skips
                #          all-zero 32-blocks (the sparse-cone), so the saving needs no extra code.
                # This stacks MULTIPLICATIVELY on MoE routing: routing picks the experts, sparsity picks the neurons.
                # ── OPERATOR-DRIVEN MASK (the alpha lever; OPERATOR_CALIBRATION §2.5 "the operator toggles the FFN
                #    SWITCHES to RESTRAIN the stored compute to exactly the function needed"). The switch set belongs to
                #    the SIGMA, not the token, so it is consulted for FREE — no gate matmul is needed to choose, which
                #    is the whole reason the per-token version capped at ~2x and measured 0.66x. Here gate, up AND down
                #    all shrink to the kept fraction: gate/up are computed only over the kept row-runs, and `down` gets
                #    its saving automatically because `act` is all-zero in dropped blocks and the substrate already
                #    skips all-zero 32-blocks (the sparse-cone).
                mask = None
                if self.sigma_mask is not None:
                    from pfc_sigma_mask import get_mask, runs as _mruns
                    mask = get_mask(self.sigma_mask[0], self.sigma_mask[1], self.sigma_mask[2], li, j)
                if mask:
                    nb_all = self.n_ff // 32
                    mr = _mruns(mask)
                    Meter.pruned += (nb_all - len(mask)) * 32
                    gt = [0.0] * self.n_ff; up = [0.0] * self.n_ff
                    for r0, r1 in mr:
                        gt[r0 * 32:r1 * 32] = self.matmul_rows(f"blk.{li}.ffn_gate.{j}.weight", h, r0 * 32,
                                                               (r1 - r0) * 32, "m_gate")
                        up[r0 * 32:r1 * 32] = self.matmul_rows(f"blk.{li}.ffn_up.{j}.weight", h, r0 * 32,
                                                               (r1 - r0) * 32, "m_up")
                    act = [0.0] * self.n_ff
                    for b in mask:
                        for i in range(b * 32, (b + 1) * 32): act[i] = self.glue.silu(gt[i]) * up[i]
                    dn = self.matmul(f"blk.{li}.ffn_down.{j}.weight", act, "m_down")
                    wgt = ex[j] / z
                    for i in range(self.ne): out[i] += wgt * dn[i]
                    continue
                keep = self.ffn_keep
                if keep >= 1.0:
                    # SPARSITY OFF (the default, because it measured negative — see the header note). Take the direct
                    # path: with keep=1.0 the machinery below still sorted every block, routed `up` through
                    # `matmul_rows`, and rebuilt `act` element-by-element, which is pure overhead on the path every
                    # real run actually uses.
                    up = self.matmul(f"blk.{li}.ffn_up.{j}.weight", h, "e_up")
                    act = [self.glue.silu(gt[i]) * up[i] for i in range(len(gt))]
                    if self.mask_record is not None:
                        # CALIBRATION: record which 32-neuron blocks this sigma actually fires. Union across tokens —
                        # a block that fires for ANY token under this sigma must stay, or we silently drop capability
                        # the operator legitimately uses. Threshold is relative to this expert's own peak.
                        from pfc_sigma_mask import record as _mrec
                        nb_all = len(gt) // 32
                        peak = max((abs(v) for v in act), default=0.0) or 1.0
                        liveb = [b for b in range(nb_all)
                                 if max(abs(v) for v in act[b * 32:(b + 1) * 32]) > 0.02 * peak]
                        _mrec(self.mask_record[0], self.mask_record[1], self.mask_record[2], li, j, liveb, nb_all)
                    dn = self.matmul(f"blk.{li}.ffn_down.{j}.weight", act, "e_down")
                    wgt = ex[j] / z
                    for i in range(self.ne): out[i] += wgt * dn[i]
                    continue
                nb = len(gt) // 32
                sil = [self.glue.silu(v) for v in gt]
                blocks = sorted(range(nb), key=lambda b: -max(abs(v) for v in sil[b * 32:(b + 1) * 32]))
                live_b = sorted(blocks[:max(1, int(nb * keep))])
                Meter.pruned += (nb - len(live_b)) * 32
                up = [0.0] * len(gt)
                for r0, r1 in _runs(live_b):                       # contiguous runs -> one addressed range each
                    seg = self.matmul_rows(f"blk.{li}.ffn_up.{j}.weight", h, r0 * 32, (r1 - r0) * 32, "e_up")
                    up[r0 * 32:r1 * 32] = seg
                act = [0.0] * len(gt)
                for b in live_b:
                    for i in range(b * 32, (b + 1) * 32): act[i] = sil[i] * up[i]
                dn = self.matmul(f"blk.{li}.ffn_down.{j}.weight", act, "e_down")
            wgt = ex[j] / z
            for i in range(self.ne): out[i] += wgt * dn[i]
        return out

    def matmul_rows(self, name, x, row0, nrows, tag=""):
        """y = W[row0:row0+nrows] · x — address a ROW RANGE of a tensor (one expert out of a fused expert stack).

        A row range is PURE ADDRESS ARITHMETIC: an expert's rows start at `off + row0*row_bytes`. So instead of a
        separate code path (which would mean a host dot — banned), register a synthetic tensor descriptor pointing at
        that offset and delegate to the SAME substrate matmul. The routed expert's rows are the only ones read; the
        other 127 experts are never touched, which is the α lever doing its job."""
        key = f"{name}#rows{row0}:{nrows}"
        if key not in self.g.tensors:
            t = self.g.tensors[name]; tid = int(t["type"]); n_in = int(t["dims"][0])
            rb = row_bytes(tid, n_in)
            self.g.tensors[key] = {"type": tid, "dims": [n_in, nrows], "off": int(t["off"]) + row0 * rb}
        return self.matmul(key, x, tag)

    def forward(self, tokens, log=None):
        if self.n_expert > 0:                                    # MoE (e.g. gemma-A4B): per-position path (routed experts)
            return self._forward_seq(tokens, log)
        return self._forward_batch(tokens, log)                 # dense (e.g. Llama): layer-outer, dequant model ONCE

    def _forward_batch(self, tokens, log=None):
        """LAYER-OUTER dense forward: each weight tensor is dequanted ONCE and folded against all P positions (the
        dequant-once lever). Returns the last position's logits over the vocab. Resident RAM bounded (tiled + streamed)."""
        P = len(tokens)
        xs = [self.g.deq_row(t) for t in tokens]; Meter.addressed += P      # embeddings (addressed reads)
        scale = 1.0 / math.sqrt(self.hd); kvn = self.nkv
        for li in range(self.L):
            anw = self.normw(f"blk.{li}.attn_norm.weight")
            hs = [self.rmsnorm(x, anw) for x in xs]
            qs = self.matmul_batch(f"blk.{li}.attn_q.weight", hs, "q")
            ks = self.matmul_batch(f"blk.{li}.attn_k.weight", hs, "k")
            vs = self.matmul_batch(f"blk.{li}.attn_v.weight", hs, "v")
            qh = [[self.rope(qs[p][hh * self.hd:(hh + 1) * self.hd], p) for hh in range(self.nh)] for p in range(P)]
            kh = [[self.rope(ks[p][gg * self.hd:(gg + 1) * self.hd], p) for gg in range(kvn)] for p in range(P)]
            vh = [[vs[p][gg * self.hd:(gg + 1) * self.hd] for gg in range(kvn)] for p in range(P)]
            aos = []
            for p in range(P):                                              # causal attention: pos p attends 0..p
                ao = [0.0] * (self.nh * self.hd)
                for hh in range(self.nh):
                    gg = hh * kvn // self.nh
                    sc = [sum(qh[p][hh][d] * kh[pp][gg][d] for d in range(self.hd)) * scale for pp in range(p + 1)]
                    m = max(sc); ex = [self.glue.exp(s - m) for s in sc]; z = sum(ex) or 1e-9
                    b = hh * self.hd
                    for pp in range(p + 1):
                        w = ex[pp] / z; vv = vh[pp][gg]
                        for d in range(self.hd): ao[b + d] += w * vv[d]
                aos.append(ao)
            os_ = self.matmul_batch(f"blk.{li}.attn_output.weight", aos, "o")
            xs = [[xs[p][i] + os_[p][i] for i in range(self.ne)] for p in range(P)]
            fnw = self.normw(f"blk.{li}.ffn_norm.weight")
            h2s = [self.rmsnorm(x, fnw) for x in xs]
            gts = self.matmul_batch(f"blk.{li}.ffn_gate.weight", h2s, "gate")
            ups = self.matmul_batch(f"blk.{li}.ffn_up.weight", h2s, "up")
            acts = [[self.glue.silu(gts[p][i]) * ups[p][i] for i in range(len(gts[p]))] for p in range(P)]
            dns = self.matmul_batch(f"blk.{li}.ffn_down.weight", acts, "down")
            xs = [[xs[p][i] + dns[p][i] for i in range(self.ne)] for p in range(P)]
            if log: log(f"    layer {li+1}/{self.L}  resident={resident_mb():.1f}MB  {Meter.line()}")
        xf = self.rmsnorm(xs[-1], self.normw("output_norm.weight"))
        return self.matmul(self.lm_name, xf, "lm_head")

    def _forward_seq(self, tokens, log=None):
        """per-position path (used for MoE, where each position routes its own experts). builds KV across positions."""
        # ── AXIS-D LEVER: cache_prompt / PERSISTENT KV (PFC_LEVER_INDEX §D, [M] "prefill 5.7-6.8x") ─────────────────
        # `generate` calls forward(ids + out_ids) once per token, and this used to rebuild the KV cache from scratch
        # every call — so token n RE-RAN every earlier position. Cost was O(n*P + n^2/2) position-passes instead of
        # O(P + n). Keep the cache across calls whenever the new token list EXTENDS the one already cached, and process
        # only the genuinely new positions. Exact — it changes no arithmetic, it just stops redoing it.
        cached = getattr(self, "_kv_tokens", [])
        # ── cache_prompt, PROPERLY (CALIBRATION_FINDINGS #5 [M]: a stable σ-prefix reused prefills 5.7x faster —
        #    7.35 s vs 41.86 s cold). Reuse the LONGEST COMMON PREFIX, not only the exact-extension case. Every turn in
        #    the harness starts with the SAME σ operator, so turn 2's σ must not be re-prefilled just because the
        #    question after it changed. Attention is causal, so positions [0, lcp) are unaffected by anything later —
        #    keeping them is exact, not an approximation.
        lcp = 0
        if self._kv is not None:
            m = min(len(cached), len(tokens))
            while lcp < m and cached[lcp] == tokens[lcp]: lcp += 1
        if self._kv is not None and lcp > 0:
            kcache, vcache = self._kv; start = lcp
            # TRUNCATE TO `start` BEFORE EXTENDING. The cache lists are mutated in place but `_kv_tokens` is only
            # updated on success, so a pass that raised part-way through leaves them longer than the token list they
            # claim to describe. Re-entering would then attend over stale positions and quietly return WRONG logits —
            # a silent-wrong-answer bug, which is worse than a crash. Cutting back to `start` makes reuse idempotent.
            for li in range(self.L):
                del kcache[li][start:]; del vcache[li][start:]
        else:
            kcache = [[] for _ in range(self.L)]; vcache = [[] for _ in range(self.L)]; start = 0
        last_x = None
        if start >= len(tokens) and tokens:
            # every position is already cached (forward called twice on the same tokens — e.g. a re-Send). Recompute
            # only the final position rather than returning `last_x = None` into rmsnorm.
            start = len(tokens) - 1
            for li in range(self.L):
                del kcache[li][start:]; del vcache[li][start:]
        for pos in range(start, len(tokens)):
            tok = tokens[pos]
            x = self.g.deq_row(tok); Meter.addressed += 1
            for li in range(self.L):
                x_before = x if self.trace_layers is not None else None
                h = self.rmsnorm(x, self.normw(f"blk.{li}.attn_norm.weight"))
                # a shared-V layer reads the value cache of the nearest earlier layer that owns one (its group donor)
                vsh = None
                if f"blk.{li}.attn_v.weight" not in self.g.tensors:
                    d = li - 1
                    while d >= 0 and f"blk.{d}.attn_v.weight" not in self.g.tensors: d -= 1
                    vsh = vcache[d] if d >= 0 else None
                x = [x[i] + a for i, a in enumerate(self.attention(li, h, pos, kcache[li], vcache[li], vsh))]
                h2 = self.rmsnorm(x, self.normw(f"blk.{li}.ffn_norm.weight"))
                x = [x[i] + d for i, d in enumerate(self.ffn(li, h2))]
                if self.trace_layers is not None:
                    # LAYER-CONTRIBUTION TRACE (prerequisite for the early-exit lever, OPERATOR_CALIBRATION §3
                    # "routing runs only the EXACT tensors needed"). If the late layers barely move the hidden state,
                    # they are candidates to skip — but nobody has measured WHERE that happens on this engine. Cost is
                    # one pass over n_embd floats per layer, i.e. nothing next to a 394M-MAC layer.
                    n_now = math.sqrt(sum(v * v for v in x)) or 1e-9
                    d_norm = math.sqrt(sum((a - b) ** 2 for a, b in zip(x, x_before)))
                    self.trace_layers.append((pos, li, n_now, d_norm, d_norm / n_now))
                if log: log(f"    pos {pos} layer {li+1}/{self.L}  resident={resident_mb():.1f}MB  {Meter.line()}")
            last_x = x
        self._kv = (kcache, vcache); self._kv_tokens = list(tokens)   # persist for the next token (cache_prompt lever)
        xf = self.rmsnorm(last_x, self.normw("output_norm.weight"))
        return self.matmul(self.lm_name, xf, "lm_head")

    def argmax(self, logits):
        """THE TOKEN DECISION. `CIRCUIT_PFC.md`: "before writing ANY host-side loop or compare, search this file — if a
        circuit exists, WIRE IT and let the pfc run it." `pfc_argmax` (26,272 gates) has been baked since 07-23 and does
        exactly this. Driven bit-sliced (host/pfc_argmax_drive.py): a 32k vocab is 500 blocks of 64, and all 500 settle
        in ONE ripple because each block is a lane — 3 sweeps total, not 509. Measured byte-exact 5/5 vs the host loop
        this replaces, 129 ms/token (negligible against the matmuls). The host loop remains only as the fallback if the
        circuit is absent from the binary."""
        if self.pfc_argmax:
            try:
                from pfc_argmax_drive import argmax_on_pfc
                if self._argmax_cd is None:
                    import titan_circuit as TC
                    self._argmax_cd = TC.load("pfc_argmax")
                return argmax_on_pfc(logits, self._argmax_cd)[0]
            except Exception:
                self.pfc_argmax = False                      # circuit absent/unreadable -> fall through, never crash
        best = 0
        for j in range(1, len(logits)):
            if logits[j] > logits[best]: best = j
        return best

    def _memo_key(self, ids):
        """SYSTEM-1 MEMOIZE (INV-95, measured 34× @R=64): at temp 0 the model is a deterministic circuit, so a token
        already computed for this exact (model, token-prefix) is a pure function — serve it as an ADDRESSED READ (0
        ripple) instead of re-folding the whole forward pass. This is the memoize the engine loaded but never used."""
        return hashlib.blake2b(
            (os.path.basename(self.model_path) + "|" + ",".join(map(str, ids))).encode(), digest_size=16).hexdigest()

    def generate(self, prompt, n_new=1, log=print, verbose=False):
        ids = self.bpe.encode(prompt)
        log(f"  prompt {prompt!r} → {len(ids)} tokens {ids[:12]}{'…' if len(ids) > 12 else ''}")
        out_ids = []
        for step in range(n_new):
            key = self._memo_key(ids + out_ids) if self.memo_on else None
            # BINARY-BACKED MEMO (CIRCUIT_PFC: `memocache` = "memoize fold baked permanent; a HIT is an addressed
            # read"). Check the file's own bytes first — that hit travels with the binary, unlike a sidecar .json.
            if key is not None and key not in self.memo and self.memo_binary:
                try:
                    from pfc_memo_store import get as _mget
                    hit = _mget(os.path.basename(self.model_path), ids + out_ids)
                    if hit is not None:
                        self.memo[key] = hit; Meter.addressed += 1
                except Exception:
                    self.memo_binary = False
            if key is not None and key in self.memo:              # HIT: 0 forward passes, 0 ripple — instant
                nxt = int(self.memo[key]); Meter.memo_hits += 1; Meter.addressed += 1
            else:
                logits = self.forward(ids + out_ids, log=(log if verbose else None))
                nxt = self.argmax(logits)
                if key is not None:
                    self.memo[key] = nxt
                    if self.memo_binary:
                        try:
                            from pfc_memo_store import put as _mput
                            _mput(os.path.basename(self.model_path), ids + out_ids, nxt)
                        except Exception:
                            self.memo_binary = False
            out_ids.append(nxt)
            piece = self.bpe.decode([nxt], self.g)
            log(f"  ★ token {step+1}: id {nxt} = {piece!r}   [{Meter.line()}]")
        if self.memo_on:
            os.makedirs(os.path.dirname(MEMO), exist_ok=True)
            try: json.dump(self.memo, open(MEMO, "w"))
            except Exception: pass
        return self.bpe.decode(out_ids, self.g)


# ───────────────────────────────────────────── self-test (fast, no big run) ─────────────────────────────────────────────
def selftest(model=DEFAULT_MODEL):
    print("=== pfc_forward selftest — verify every piece vs a float reference (composition correctness) ===", flush=True)
    ok = True
    # 1) the substrate matmul vs an integer/float reference on a small case
    e = MatmulEngine(WB=8, XB=8)
    import random; random.seed(3)
    w = [[random.randint(-100, 100) for _ in range(BLK)] for _ in range(64)]
    x = [random.randint(-127, 127) for _ in range(BLK)]
    wcols, W = e.preslice_weights([[max(-127, min(127, wi)) for wi in row] for row in w])
    got = e.matmul_column_W([wcols], W, [x], ACCW=48)
    ref = [sum(w[j][i] * x[i] for i in range(BLK)) for j in range(64)]
    m1 = all(got[j] == ref[j] for j in range(64)); ok &= m1
    print(f"  [1] substrate bit-sliced matmul == integer dot: {m1}", flush=True)
    # 2) glue tables vs host math
    gl = Glue(res=8192); import math as _m
    m2 = (abs(gl.rsqrt(4.0) - 0.5) < 1e-6 and abs(gl.silu(1.0) - 1.0 / (1 + _m.exp(-1))) < 1e-6
          and abs(gl.sin(_m.pi / 2) - 1.0) < 2e-3 and abs(gl.cos(0.0) - 1.0) < 1e-9); ok &= m2
    print(f"  [2] glue tables (rsqrt/silu/sin/cos) ≈ host math: {m2}", flush=True)
    # 3) tokenizer round-trips on the real vocab
    if os.path.exists(model):
        g = GGUF(model); bpe = BPE(g)
        s = "The capital of France is"
        ids = bpe.encode(s); back = bpe.decode(ids, g)
        m3 = s in back; ok &= m3
        print(f"  [3] BPE encode/decode {s!r} → {ids} → {back!r}: round-trip {m3}", flush=True)
        # 4) one real matmul on the substrate vs a host-float reference. Check MANY neurons and score with an ABS-OR-REL
        #    tolerance (the old first-4-neurons rel_err exploded on a near-zero output: -0.0 vs -0.0 read as 0.10 "error").
        f = Forward(model, WB=8, XB=8, memo=False)
        name = "blk.0.attn_q.weight"; t = g.tensors[name]; n_in = int(t["dims"][0]); NCHK = min(64, int(t["dims"][1]))
        xv = g.deq_row(ids[-1])[:n_in]
        if len(xv) < n_in: xv = (xv + [0.0] * n_in)[:n_in]
        sub = f.matmul(name, xv)[:NCHK]
        base = g.data0 + t["off"]; rb = row_bytes(t["type"], n_in)
        refv = [sum(_deqw(g.mm[base + j * rb: base + j * rb + rb], t["type"], n_in)[i] * xv[i] for i in range(n_in))
                for j in range(NCHK)]
        scale = max((abs(v) for v in refv), default=0.0) or 1.0            # score against the largest real magnitude
        err = max(abs(sub[j] - refv[j]) for j in range(NCHK))             # absolute error (robust at near-zero)
        m4 = err < max(0.03 * scale, 1e-3); ok &= m4                       # abs-or-rel: 3% of scale, or 1e-3 absolute
        print(f"  [4] substrate vs host-float on real attn_q[0:{NCHK}]: max_abs_err {err:.5f} vs scale {scale:.3f} "
              f"(pass<{max(0.03*scale,1e-3):.5f} = {m4})", flush=True)
    else:
        print(f"  [3,4] skipped — model not found: {model}", flush=True)
    print(f"\n  SELFTEST {'PASS' if ok else 'FAIL'} — composition {'correct' if ok else 'has a mismatch'}.", flush=True)
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if not args or args[0] == "selftest":
        return selftest()
    model = DEFAULT_MODEL; n_new = 1; substrate = True; WB = 8; mode = None; trace = False   # WB=8 measured 1.66x faster than 16
    #   on REAL weight rows (host/pfc_fabsweep.py). WB=3 was 32% error on real rows — the doc's "3-bit accuracy-safe"
    #   does NOT hold with per-neuron scaling here, so 8 is the leanest circuit that keeps the answer (pfc_optimal rule).
    while args and args[0].startswith("--"):
        if args[0] == "--model": model = args[1]; args = args[2:]
        elif args[0] == "--new": n_new = int(args[1]); args = args[2:]
        elif args[0] == "--wb": WB = int(args[1]); args = args[2:]
        elif args[0] == "--ref": substrate = False; args = args[1:]   # fast float-dot composition check (not the pfc path)
        elif args[0] == "--mode": mode = args[1]; args = args[2:]     # prepend the HARNESS's sigma operator, verbatim
        elif args[0] == "--trace": trace = True; args = args[1:]      # record per-layer hidden-state movement
        else: args = args[1:]
    prompt = " ".join(args) if args else "The capital of France is"
    if mode:
        # Prepend the harness's sigma VERBATIM so the token ids this run computes are EXACTLY the ids the harness will
        # look up. Every token then lands in the binary memo (`memocache`) as a hit the harness finds instantly — the
        # System-1 memoize lever working ACROSS PROCESSES, through the file itself rather than a sidecar.
        try:
            from pfc_desktop import MODES
            prompt = MODES.get(mode, "") + prompt
            print(f"  sigma:{mode} prepended verbatim from the harness", flush=True)
        except Exception as e:
            print(f"  could not load harness MODES ({e}) — running without sigma", flush=True)
    mode = "pfc substrate" if substrate else "FLOAT REFERENCE (composition check, not the pfc)"
    print(f"=== pfc_forward — general forward pass [{mode}] ===", flush=True)
    print(f"  model {os.path.basename(model)} ({os.path.getsize(model)/1e9:.1f} GB)", flush=True)
    Meter.reset(); t0 = time.time()
    f = Forward(model, WB=WB, substrate=substrate)
    print(f"  arch={f.arch} L={f.L} n_embd={f.ne} heads={f.nh}/{f.nkv} head_dim={f.hd} ff={f.n_ff} "
          f"vocab={f.g.n_vocab} experts={f.n_expert}", flush=True)
    print(f"  substrate dot: {f.gates_per_sweep:,} gates/sweep (WB={f.WB} XB={f.XB}); glue=addressed tables (0 ripple)", flush=True)
    print(f"  resident baseline {resident_mb():.1f}MB (40+GB model addressed off storage, never resident)\n", flush=True)
    if trace:
        f.trace_layers = []
        print(f"  --trace on: recording per-layer hidden-state movement (early-exit data)", flush=True)
    flog = lambda s: print(s, flush=True)                        # flush so long runs stream per-layer progress
    text = f.generate(prompt, n_new=n_new, log=flog, verbose=True)
    print(f"\n  ★★ OUTPUT: {prompt!r} → {text!r}", flush=True)
    print(f"  ★ {Meter.line()}   ·   {time.time()-t0:.0f}s", flush=True)
    if trace and f.trace_layers:
        # WHERE DOES THE PASS STOP MATTERING? Average the relative hidden-state movement per layer across positions.
        # Layers with near-zero movement are early-exit candidates (OPERATOR_CALIBRATION §3: route only what is needed).
        per = {}
        for pos, li, n, d, r in f.trace_layers: per.setdefault(li, []).append(r)
        rows = [(li, sum(v) / len(v)) for li, v in sorted(per.items())]
        print(f"  layer contribution (avg relative movement of the hidden state):", flush=True)
        for li, r in rows: print(f"    layer {li:>2}: {r*100:7.3f}%{'   <- negligible' if r < 0.001 else ''}", flush=True)
        neg = [li for li, r in rows if r < 0.001]
        json.dump({"rows": rows, "negligible": neg}, open("C:/llm/sdc_out/pfc_layer_trace.json", "w"))
        print(f"  {len(neg)} of {len(rows)} layers moved the state <0.1% -> early-exit candidates. "
              f"saved to C:/llm/sdc_out/pfc_layer_trace.json", flush=True)
    print(f"  ripple is the metric to drive to 0: memoize (repeats), MoE routing, operator sparsity, and bit-slicing pull it down.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
