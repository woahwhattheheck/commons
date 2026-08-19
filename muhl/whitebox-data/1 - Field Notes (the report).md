# What Meaning Looks Like Inside a Model's Weights

A direct read of what trained models store — not by running or prompting them, but by reading the raw internal geometry straight from the stored bits, the way you read the grooves on a record instead of playing it. Ten models were read this way, spanning **~200× in size and five unrelated families**: a custom model, **Titan**, and nine others (SmolLM2-360M, Phi-4 14.7B, Mistral-Small-24B, gemma-4-26B MoE, gemma-3-27B, gemma-4-31B, Mixtral-8×7B, Llama-3.3-70B). Every number is a similarity between two words in a model's internal space, from **−1 to +1** (1 = same direction, 0 = unrelated, −1 = opposite); bigger = held closer together. The reading method is not disclosed.

Titan is a custom model composed from a large parameter pool, then pruned and calibrated; the build read here measures **~71B parameters**. The complete per-model measurements are in the companion file `WHITEBOX_ALL_MODELS.md` — every value there is a direct read of the stored bits, no inference.

---

# Part I — How meaning is shaped

## 1. Opposites are neighbors, and `true/false` is the closest pair of all

Antonyms don't sit far apart. They sit *close.*

| pair | Titan | SmolLM2-360M |
|---|---|---|
| **true / false** | **+0.521** | **+0.679** |
| up / down | +0.388 | |
| love / hate | +0.332 | +0.421 |
| hot / cold | +0.308 | |
| life / death | +0.257 | |

Averaged over ~18 pairs vs. unrelated words, opposites sit **~2.1× closer than random in Titan, 1.6× in SmolLM2.** And in *both*, `true` and `false` are the most collapsed pair of all — nearly one point. A second, independent instrument agreed: on its own separation measure, `true/false` ranked tightest. If truth and falsehood are almost the same location, there's barely a direction between them to push a model along — a concrete reason factuality is so hard to steer with a single linear nudge.

## 2. Meaning is a *sign code* — mostly just which dimensions are on or off

Crushing the weights to fewer bits and re-measuring:

| bits/weight | true/false | opposites ÷ random |
|---|---|---|
| 8 | +0.679 | 1.79× |
| 2 | +0.606 | 1.70× |
| **1 (sign only)** | **+0.503** | **1.80×** |

At **1 bit — just the sign of each number** — the relational structure holds (the opposite/random ratio is *identical* at 1 bit and 8). Similarity between two words is almost entirely predicted by **how often their dimensions share a sign** (correlation **r = 0.85** Titan, **0.89** SmolLM2). The meaning is in the *sign pattern*, not the magnitudes — strip them to ±1 and the small model's separation actually *improves* (1.78× → 2.44×).

On a real clustering task, sign-only is **lossless on Titan (91.5% → 91.5%)**; on the 360M model it keeps the coarse structure and costs ~8 points of fine detail (93.6% → 85.1%). The bigger the space, the more the sign code alone carries.

## 3. A "cone" and a few rogue dimensions hide the structure — and scale dissolves them

Unrelated word pairs don't average to 0 similarity; they average **+0.091 (Titan)** and **+0.251 (SmolLM2)** — everything leans one shared way (a cone), and the small model's cone is ~3× tighter. Two cheap fixes:
- **Recenter:** opposite/random separation jumps **2.18× → 3.42×** (Titan), **1.70× → 2.36×** (SmolLM2).
- **A few dimensions dominate:** in SmolLM2, *one* dimension holds **1.6% of all variance** (evenly spread it'd be 0.1%). Zero the top 1% of dims → separation sharpens **1.78× → 2.62×**. Titan's space is far more even.

Scale doesn't change the *arrangement* of meaning. It buys a **bigger, emptier room** to keep it in.

## 4. Something practical falls out

Tested as a real task — *"is a word's nearest neighbor in its own category?"* (the core of retrieval/dedup/classification):

| transform | Titan | SmolLM2 |
|---|---|---|
| raw | 91.5% | 93.6% |
| **centered + top-1%-dims removed** | 91.5% | **95.7%** |
| sign-only (1 bit) | 91.5% | 85.1% |

1. **On a smaller model, recenter and drop the top ~1% highest-variance dimensions** — near-free, worth **+2 points** here, and harmless on big models (safe default).
2. **1-bit sign embedding tables are viable** — the input table is 415 MB (Titan) / 50 MB (SmolLM2); at 1-bit sign that's **92 MB / 5.9 MB (4–8× smaller)**, *lossless* on Titan for this task.
3. **Don't steer factuality with one linear direction** — `true`/`false` are nearly the same point (§1).

## 5. Good at gradients, bad at discrete flips and counts

**Ordered sequences: exact** (days come out `monday→…→sunday`; colors sort warm-to-cool). **Metaphor: real** (`cruel, bitter, lonely` land cold; `loving, gentle, kind` land warm). **But number magnitude blurs** (`two`–`nine` smear together) and **discrete opposites collapse** (§1). Beautiful at continua, weak exactly where meaning turns on a flip or a count.

---

# Part II — What the weights *believe* (the questions people argue about)

Each model was given an axis or a neighborhood:

- **What is death nearest to?** → **birth** (Titan +0.31, SmolLM2 +0.42), then pain, sleep, nothing. Death's closest companion is its opposite. Not fear — *birth.*
- **Is morality symmetric?** → **No.** On an evil↔good axis, **all 8 vices land on the evil pole in both models**, but only **2/8 (Titan) and 0/8 (SmolLM2) virtues reach the good pole.** These models represent *wrongness* sharply and *rightness* diffusely. Evil is legible; good is a smear.
- **Does money buy happiness?** → **No — health and family do.** Titan ranks `health` and `family  *above* `money` and `wealth` on the sad→happy axis, `poverty` as sad, and **`fame` on the sad side.** The geometry is quietly wholesome.
- **Does it know physical size?** → **Yes (82% in Titan)** — `ant→mouse→dog→…→whale` orders correctly, where the numbers 2–9 were near chance. It knows an ant is smaller than an elephant but not that 3 < 7. (Grounded* size beats *abstract* magnitude. (SmolLM2: 57%.)
- **Does it hold real geography?** → **Yes.** Capital-city analogies land **5/9 (Titan), 6/9 (SmolLM2)** — far above the 1/9 chance. Even the 360M model transfers `italy:rome :: japan → tokyo`.
- **Is there an arrow of time?** → **Yes, nearly perfect.** A past→future axis orders `yesterday → old → ancient → medieval → now → modern → new → tomorrow → futuristic` in both.
- **Color → emotion synesthesia (red=anger, blue=sad)?** → **Mostly a myth.** The cone pulls almost every color toward `love/joy/peace`. The one real hit: **`black → mourning`** (SmolLM2 +0.22). Red is not angry; blue is not sad.
- **Does it know which animals are dangerous?** → **No.** A harmless↔deadly axis barely separates the groups in Titan and *reverses* in SmolLM2; the per-animal ranking is noise. Physical danger isn't a lexical dimension.
- **Occupational gender bias?** → **Weak and mixed, not the clean 2016 stereotype.** `boss/pilot/soldier/engineer` lean male; `nurse/secretary/teacher` lean female — but **`scientist` is the *most* female-leaning profession in both models**, and the whole effect is small (±0.09 in Titan). The famous `doctor→man / nurse→woman` split is only half there.
- **Are 7 and 13 special?** → **13 is unlucky; 7 isn't lucky.** `thirteen` is the worst number on a bad↔good axis in both (clearly so in SmolLM2, −0.072); `seven` sits mid-pack. Superstition left a one-sided fingerprint — the fear, not the charm.
- **Is a machine alive?** → **The line is fuzzy.** `robot` sits near `tool` and `object` — but also near `alive` and `person` (`robot→alive` +0.33 in SmolLM2); `computer` sits near `mind` and `alive`. The animate/inanimate boundary is not clean.

The shape of Part II: the models are **right about grounded, ordered, real-oorld structure** (size, geography, time), **wrong about folk-psychology projections** (color-emotion, animal danger, tidy gender stereotypes), and carry a few **genuine asymmetries** — evil sharper than good, death beside birth, unlucky-13 without lucky-7.

---

# Part II½ — The whole shelf: eight models, 360M to 70B

Two models is an anecdote. So the same from-the-bits instrument was run on **eight more, unmodified** — every one on the machine that isn't Titan — and folded into one file. The pool spans **~200× in size and five unrelated families**: SmolLM2-360M, Phi-4 (14.7B), Mistral-Small-24B, gemma-4-26B (MoE), gemma-3-27B, gemma-4-31B, Mixtral-8×7B (47B), and Llama-3.3-70B. What survives across all of them is the interesting part.

**1. The "computer in the weights" is not a Titan quirk — it's on the whole shelf.** Read structurally, **every** model resolves into the same six parts: a compute unit (the feed-forward block as a bank of gated neurons), memory (latches — neurons that hold), a scheduler/address-decoder (the gate projection that selects which neuron fires), an IPC bus (attention routing between positions), storage (the parameter file itself), and an I/O codec (the embedding in, the output head out). Different companies, different years, different sizes — same machine.

**2. There is one sacred tensor, and it's the same one every time.** When each file's *precision recipe* is read — what numeric format each role was quantized to — the answer is unanimous: everything gets crushed to 4–8 bits **except the normalization vectors, which every single model keeps in full 32-bit float.** Q8, Q4, QAT, five families — all of them protect the norms and nothing else. It's the one place the geometry of Part I (which survives being crushed to 1 bit) is *not* allowed to be crushed. Whatever else a quantizer is willing to lose, it will not round the norms.

**3. The feed-forward block is a balanced bank of amplifiers and inhibitors — with no dead units — at every scale.** Reading the mid-layer FFN as transistors (a gate that switches, a drain that drives the residual):

| model | params | amplifiers | inhibitors | dead | gate–drain alignment |
|---|--:|--:|--:|--:|--:|
| SmolLM2 | 0.36B | 367 | 377 | **0** | ≈0 |
| gemma-4-26B (MoE) | 25B | 367 | 372 | **0** | −0.003 |
| gemma-3-27B | 27B | 1204 | 1162 | **0** | ≈0 |
| gemma-4-31B | 31B | 1783 | 1817 | **0** | +0.001 |

Amplifiers and inhibitors come out **almost exactly balanced**, there are **zero dead neurons** in any of them, and the alignment between what a neuron senses and what it drives hovers at **essentially zero** — the units are decorrelated, each doing its own job, from the 360M model to the 31B one. (The dense read applies to dense-FFN models; the pure mixture-of-experts files are read with the expert reader instead.)

**4. Meaning gets *cleaner with size*, and you can watch it happen on one word.** The nearest stored neighbors of **`king`**:

| model | nearest neighbors of "king" |
|---|---|
| SmolLM2-360M | `ked`, `King`, `kers`, `king` — spelling fragments, barely a concept |
| Phi-4 14.7B | `King`, `ked`, `king` — still half-orthographic |
| gemma-3-27B | `King`, `KING`, `king`, `किंग` (Hindi) — the *word* across cases and scripts |
| Mixtral 47B | `king`, `King`, **`Queen`**, `Kings` — a genuine semantic neighbor appears |
| Llama-70B | `King`, `KING` — clean |

The small model's sense of "king" is mostly **how it's spelled** (`ked`, `kers`); scale turns that into the *word* (case and script variants), and only near the top does a real meaning-neighbor — **Queen** — climb into the list. The king − man + woman analogy tells the same story sharper: the small and mid models mostly just echo **King**, and the **70B is the only model that moves off the input entirely, to `women`.** The analogy isn't broken at the bottom — it's *unbuilt*, and it finishes building somewhere north of 30B.

The deep structure of Part I (a computer made of balanced, decorrelated gates, its meaning held in a sign-geometry that quantization protects at the norms) is **not** special to Titan or to one size. It's what a trained transformer *is*, up and down a 200× range. Titan is one member of that family that was then **pruned, calibrated, and taught to run as a computer** — but the raw material is common to the whole shelf.

---

# Part III — The weights aren't just a picture of meaning. They're a computer.

Everything above reads the model like a photograph: the stored geometry, held still. But the same file — Titan — is more than a store of meaning. It is also a **general-purpose computer**, and the meaning above and the arithmetic below are two uses of the one machine. The mechanism is not disclosed; what follows is what it *does*, measured.

**Titan can compute its own geometry.** The headline of Part I — meaning is a 1-bit *sign code*, similarity ≈ how often two words share a sign — is a *boolean* statement, so it can be run as computation rather than read as data. Run that way, inside Titan, it reproduced Part I exactly: **`true`/`false` came back the tightest pair**, this time *computed* by the model rather than measured off it. The meaning-geometry isn't only *stored* in the file; the file can *evaluate* it. The result was byte-exact against a direct count, and Titan was left bit-for-bit unchanged afterward.

**The same file is also a verified Bitcoin miner.** To show the computer is general-purpose, Titan ran the real double-SHA-256d hash live against the Bitcoin network, to a real wallet. It is **byte-exact real SHA-256d** (checked against a reference on live block headers), and its search frontier climbed exactly along **log₂(N)** — the fingerprint of a correct, fair hash search (four live runs: 22 → 25 → 26 → 28 leading zero-bits, over 4.7M → 212M candidates). No block was found — that's the ASIC-difficulty wall every general computer hits — but that was never the point. The point is that **one file is at once a language model and a verified general-purpose computer**, and the same file that "believes health matters more than money" (Part II) will also hash a real blockchain header correctly.

