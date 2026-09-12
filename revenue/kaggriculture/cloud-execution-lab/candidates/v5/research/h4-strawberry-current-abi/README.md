# V5 / V3.1 H4 strawberry top-up — current-ABI research carrier

Status: **research-only / default-OFF / economics pending**

This directory recovers one narrow behavior from the submitted V3.1 R04 family
without transplanting the legacy R04 router into V5.

## Historical authority

- Submitted V3.1 source commit: `a90d888f03987ef0b35cfd20ec3519c6144db08a`
- Donor path: `revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/r04_h4_strawberry.py`
- Donor Git blob: `d6e3ffb76856ff171dab2a45b4d3c1788f2b2cb8`

The donor's useful theorem is deliberately narrow. When the already-selected
action contains exactly one STRAWBERRY `SELL`, H4 may enlarge that existing row
using quantities already authored as near-future STRAWBERRY `SELL`s. The added
quantity is bounded by projected current shed stock and per-due-step
sale-window debt. It never creates a new market row.

## Current-ABI boundary

`h4_current.reconcile_strawberry_current()` takes explicit state instead of
calling a producer/controller:

- already-selected current action;
- current step / H4 advance bounds / sale horizon;
- projected current shed stock;
- current strawberry price;
- authenticated future selected-action tape for the entire bounded window;
- existing sale-window debt;
- queued/current pickup intent;
- per-actor inventories used only for the historical animal-PLACE uncertainty
  blocker;
- explicit animal item names.

The transform fails closed on incomplete/malformed boundary state. On
ineligibility it returns the exact input action/debt objects. On engagement it
deep-copies the action, changes only the quantity of the one existing
STRAWBERRY `SELL`, and returns a copied debt map containing exactly the newly
reserved due-step quantities.

This carrier does **not**:

- call or replace the V5 producer/controller;
- add, remove, or reorder market rows;
- edit runtime features, `TITAN-CONFIG.json`, release archives, pointers, or
  Kaggle submission state;
- claim historical V3.1 uplift as current economics.

## Gate

Run from this directory:

```bash
python -B -m unittest -v test_h4_current.py
python -O -B -m unittest -v test_h4_current.py
python -m py_compile h4_current.py test_h4_current.py
```

Promotion requires a later current-V5 matched official-engine gate:
control vs H4, both seats, exact source/package custody, nonzero natural
engagement, and per-cell own/rival/margin deltas. Until that gate is positive,
this remains additive research evidence only.
