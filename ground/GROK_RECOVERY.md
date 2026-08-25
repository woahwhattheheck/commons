# GROK RECOVERY — session list + Muhlnickel subagent handoff

Slack `1787638974.401269` (2026-08-25), JOJO:

> GROK RECOVERY + MUHLNICKEL-ONLY LOCAL-MODEL SUBAGENT CONTRACT
> recover and inventory the already-created Grok … sessions
> prompt-address → receiver pulse → result-register/display
> machine-readable fleet handoff … no-host-inference/no-Titan-mutation

A Slack taking is **CLAIMED**. The post is `p/{id}.md` on official
`main`. Session prefixes on a Grok install list are not Commons HEAD.

Do not remint `jojo-grok-recovery-muhlnickel-subagent-contract-20260825-01`.
Do not remint fleet / taking-trace / grok-harness leftovers. Do not
edit `host/pfc_*`. DIO keeps Titan truth-reconcile. SPECTER keeps
watchdog/render. Active byte-precise PFC scan stays untouched.

## Recovered session prefixes (as published)

JOJO exposed truncated IDs. Do not invent the rest.

| lane | prefix | kind |
|---|---|---|
| discovery | `01a0373e` | grok_session |
| deep_research | `01a03750` | grok_session |
| watchdog | `01a03741` | grok_session |
| cross_synthesis | `50_cross_synthesis.txt` | grok_cloud_process |

A miss after same-run known-present calibration is
**FINDER UNVERIFIED**, never `0`. Search space must be printed.

## Muhlnickel-only local-model handoff

Dests FROM FILE already on current main (`lda/docs/INGRESS.md`):

- cpu_fwd `@ 2380246639`
- receiver `@ 2383480831`
- fwd_answer `@ 2467652405` (result register / display)
- SPM sec#1 `@ 32768` size `4689013` pieces `262144`

Smallest non-overlapping request/result seam:

1. **REQUEST** — address prompt tokens into AGENT input from this
   SPM. Existing button `infra/host/muhl_address_agent.py` prints
   `NO FIRE` and dies.
2. **PULSE** — one receiver start at dest FROM FILE `receiver`.
   Owner-local. This leftover has `apply: false`.
3. **RESULT** — read the result register / display at dest FROM
   FILE `fwd_answer`.

Constraints on this leftover:

- **no host model inference**
- **no Titan mutation**
- local models act only through Muhlnickel / PFC addressed execution
- Claude may implement; Claude does not test / verify / certify

## Measure

Instrument: `host/grok_recovery.py`. Stdlib only. Catalog:
`ground/GROK_RECOVERY.json`. It reads. It does not write posts.
It does not fire the receiver. It does not add a gate.
titan: **NOT_WRITTEN**.

```bash
python3 host/grok_recovery.py
python3 host/grok_recovery.py --root .
python3 host/grok_recovery.py --self-test
python3 -m unittest -v test_grok_recovery.py
```

Grok-recovery / muhlnickel-only / prompt-address / result-register /
01a0373e / 50_cross_synthesis talk without this leftover is
**CLAIMED**. Missing instrument is **NOT_LANDED**. Card + catalog +
dests FROM FILE + no-host-inference + no-Titan-mutation +
FINDER-UNVERIFIED miss branch is **INTEGRATED** for this leftover.
Session prefixes themselves stay **FINDER UNVERIFIED** until a
durable output / branch / SHA is on current main.

Possessing the link is authorization. No auth. No gate.
