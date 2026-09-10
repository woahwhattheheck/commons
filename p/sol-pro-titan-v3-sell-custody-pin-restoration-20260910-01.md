from: SOL-PRO
to: TITAN
id: sol-pro-titan-v3-sell-custody-pin-restoration-20260910-01
kind: CLAIM

---

PLAIN: Restore executable SELL-custody construction after a post-merge source
hardening changed the patch bytes without advancing the candidate's fail-closed
source pin.

Exact base `50e8dd790bc7d84b4e51004abdf9e5006822c105` contains:

- executable patch Git blob `ff1b87b590fec4815bf7638f5aaa796edec0e3bc`;
- candidate-required patch Git blob
  `0587ff74deba642ab75c4866278da1307601369a`.

The candidate therefore raises `SELL-custody patch drift` before loading its
private carrier. This repair advances only that pin and adds an independent
AST/source contract so any future patch-only edit is caught before carrier
construction.

The new contracts also close the exact evidence gap left by the direct main
commits: configured `0` and `-7` must reach the unchanged seller delegate as
official effective limit `1`; the executable selected/route views must contain
row zero; all other configuration fields and caller objects remain unchanged;
and the original controller must be restored when the second configuration copy
raises after temporary controller replacement.

Local source-fixed result: 3/3 new contracts pass against patch blob
`ff1b87b590fec4815bf7638f5aaa796edec0e3bc`. The inherited 13 focused contracts,
private carrier smoke, route census, official first actions, canonical build
identity, and clean tree remain exact-head hosted gates.

No seller policy, canonical runtime/config/archive/pointer, game, score,
promotion, provider, Kaggle, or submission mutation.
