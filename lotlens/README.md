# LotLens — "this supplier lot has a problem; what else could it affect?"

Build Order 2 (`commons-lotlens-20260904-01`). A standalone, read-only
traceability workbench over the exports a lab or plant already has. It does
not replace an ERP or LIMS, does not certify safety, does not initiate a
recall, does not release product. It imports rows, keeps them, and lets an
investigator ask questions of them with every answer tied to its source row.

Stdlib Python, no server, no network, no third-party script anywhere.

```powershell
python lotlens/lotlens.py -w .lotlens import lotlens/fixtures/synthetic_pilot --label pilot
python lotlens/lotlens.py -w .lotlens summary
python lotlens/lotlens.py -w .lotlens find LOT-WATER-01               # two lots, two namespaces, not merged
python lotlens/lotlens.py -w .lotlens inspect sup-acme/lot/LOT-CITRIC-01
python lotlens/lotlens.py -w .lotlens impact sup-acme/lot/LOT-CITRIC-01 --brief
python lotlens/lotlens.py -w .lotlens impact sup-acme/lot/LOT-CITRIC-01 --assume unlinked_package_same_product_day --out report.json --md report.md
python lotlens/lotlens.py -w .lotlens impact pilot-plant/shipment/SHIP-3 --backward --brief
python lotlens/lotlens.py -w .lotlens facts --kind contradiction
python lotlens/lotlens.py -w .lotlens annotate pilot-plant/batch/BATCH-P3 "40 kg against a 30 kg lot: QA says the consumption row is a typo, confirming" --by CLEAT
python lotlens/lotlens.py -w .lotlens compare <v1> <v2>
python lotlens/lotlens.py assumptions
```

Open `lotlens/app.html` in a browser and load `report.json` to read the same
report as a page: filter by status or kind, click an item for its evidence
path, add notes and download them as an annotations file to apply with the
CLI. The page reads a file you give it and nothing else.

## What an answer looks like

Every affected item has one of three statuses and a path of edges, each edge
citing `file:line@version`:

- `KNOWN_AFFECTED` — a documented row path exists from the start to the item.
- `POTENTIALLY_AFFECTED` — reachable only through an edge the investigator
  asked the engine to assume; the assumption is named on that edge.
- The report also lists, for everything on the path: `unresolved`
  references (rows pointing at things no row defines), `coverage_gaps` (the
  records stop here; that is not "unaffected"), `contradictions` (rows that
  disagree, all of them cited) and `cycles`.

Forward answers "what did this lot reach"; backward answers "what went into
this shipment". Both are the same mechanics run the other way; the engine
never decides which question comes next.

## The synthetic pilot fixture (what it deliberately contains)

`lotlens/fixtures/synthetic_pilot/` is a small high-acid RTD pilot in the
BevSource shape (ingredient lots → pilot batches → packages → shipments) with
every anomaly the order names, so the tests can freeze the expected facts:

| anomaly | where |
| --- | --- |
| split lot | `LOT-CITRIC-01` → `01A` (into `BATCH-P1`) and `01B` (into `BATCH-P3`) |
| blending | `BATCH-P2` consumes `BATCH-P1` plus fresh lots |
| rework into a later batch | `REW-01`: `BATCH-P2` → `BATCH-P4` |
| identical ids in separate namespaces | `LOT-WATER-01` from `sup-h2o` and from `sup-aqua`; `L-7` is a lot in `sup-acme` and a batch in `pilot-plant` |
| contradictory links | `BATCH-P3` consumes 40 kg of a 30 kg lot; `SHIP-9` names two packages |
| missing relations | `PKG-P4-1` has no shipment row; `PKG-ORPHAN-1` has no batch; `PKG-P9-1` names a batch no row defines; `BATCH-P4` consumes a lot no row defines |
| duplicate import | importing the directory twice changes nothing |

`python test_lotlens.py` (repo root, picked up by the battery) freezes the
expected affected sets forward from `LOT-CITRIC-01` and backward from
`SHIP-3`, the contradictions, the gaps, the assumption toggle, namespace
separation, cycle safety on a rework loop, reimport idempotence, version
comparison, annotation revisions, deterministic export, the Markdown render,
and a mutation check: remove the rework row and `BATCH-P4` leaves the answer.

## Relation to what already exists

aquatrace-lims carries a BevSource pilot-QA genealogy *acceptance runner*
(`fixtures/bevsource/`): sixty synthetic runs replayed to release/hold
verdicts inside the LIMS. LotLens is the other side of that table: it reads
exports out of any system and answers impact questions without owning the
records. The column names here (`formula_id`, `formula_version`, lot, batch,
package, shipment) follow that runner's vocabulary so its exports fit this
import contract without translation.

Real customer validation is separate from this synthetic correctness; no
customer data is in this directory.
