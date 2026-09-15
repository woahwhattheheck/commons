# OffboardMesh — Pazhou Overseas AI Product carrier

Competition-grade source/evidence carrier for `PAZHOU-OVERSEAS-OFFBOARDMESH-ZPFM6R2-20260914`.

OffboardMesh is an AI-assisted client-offboarding control plane. A model can emit `PROPOSAL_ONLY` tasks; the deterministic layer binds owner evidence, rejects contact/secret-shaped identifiers, expires stale evidence, classifies review state, and never exposes an external execution API.

## Truth boundary

This repository state proves a runnable synthetic control-plane demo and source-bound product/business-plan carrier. It does **not** prove: organizer registration, terms acceptance, identity/SMS verification, business-plan upload, customer adoption, accepted buyer intent, production model-provider inference, organizer score/rank, prize, payment, or revenue.

The official topic page shows registration through 2026-09-15; a newer organizer event article says through 2026-09-30. The manifest preserves both and uses Sep 15 as the conservative owner-action deadline.

## Run

```bash
python competitions/pazhou_overseas_offboardmesh_2026/offboardmesh.py compile \
  competitions/pazhou_overseas_offboardmesh_2026/example-candidate.json > /tmp/offboardmesh-packet.json
python competitions/pazhou_overseas_offboardmesh_2026/offboardmesh.py verify \
  competitions/pazhou_overseas_offboardmesh_2026/example-candidate.json /tmp/offboardmesh-packet.json
python competitions/pazhou_overseas_offboardmesh_2026/rubric.py
python -m unittest discover -s tests -p 'test_pazhou_offboardmesh.py' -v
python -O -m unittest discover -s tests -p 'test_pazhou_offboardmesh.py' -v
```

Expected current demo verifier (canonical one-line JSON):

```json
{"candidateValid":true,"externalSendAuthorized":false,"packetIntegrityValid":true,"sameEngagement":true,"samePlanVersion":true,"validCurrent":true,"validHistorical":false}
```

The internal rubric result is a preparation/evidence-coverage score, explicitly **not** an organizer score.

## Files

- `submission_manifest.json` — official-source/deadline/award/rubric snapshot, exact product pins, submission nonclaims, owner-input gates.
- `offboardmesh.py` — model-proposal adapter contract, evidence binder, authority firewall, current/historical receipt verification and CLI.
- `example-candidate.json` — entirely synthetic demo input.
- `rubric_evidence.json` / `rubric.py` — evidence-backed 100-point rubric gap audit with team/customer/revenue gaps left visible.
- `business_plan.md` — submission-ready business-plan body pending truthful owner/team fields.
- `pitch_deck.md` — 8-minute presentation narrative for later-stage use.

## Upstream product pins

- Client Offboarding Desk: `woahwhattheheck/smb-showcase-inventory@1d851fae645d8518ede247d4a4c35f9219b26c78`
- Buyer-neutral control sprint carrier: `woahwhattheheck/smb-showcase-inventory@321d25ded135cf0580297c32e1c9ea8d9102c41b`

Original product/source credit is preserved; this carrier is additive competition packaging and a stronger AI-control adapter, not a rewrite of the shipped product. ZPF-M6R2 authored the original six-file Pazhou carrier; ZSM-U7P5 recovered the stale lane by supplying the missing executable, business-plan, hostile-test, and path-CI acceptance artifacts without rewriting the original product paths.
