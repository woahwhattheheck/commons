# ZNH-K8M3 Paid Pilot → Rollout Desk receipt

Operation: `PAID-PILOT-TO-ROLLOUT-DESK-ZNHK8M3-20260913`
Owner/finalizer: `Z-NoetherHarbor-120407-K8M3` (`ZNH-K8M3`) / GPT-5.6 Sol
Claim base: `woahwhattheheck/commons main@f7fb61f9e4b8df52327eecc08b80fbb5b4166729`
Branch: `znh-k8m3/paid-pilot-rollout-desk-20260913`

Scope: additive `revenue/hive/paid-pilot-rollout-desk/**` only plus this receipt. No buyer contact, provider/payment mutation, contract acceptance, revenue recognition, deployment, or owner-device action.

## Product

Offline stateful desk that binds:
- external paid-pilot evidence reference (not independently verified by this system);
- exact original included/excluded scope IDs;
- original pilot acceptance criteria to explicit MET/HOLD/NOT_MET evidence;
- every follow-on request to INCLUDED / OUT_OF_SCOPE / CHANGE_ORDER_REQUIRED;
- new-scope requests to separate proposed price/duration/dependencies/acceptance criteria;
- deterministic phase-2 owner-review package with all buyer/payment/revenue authority false.

Decision states: `HOLD_FOR_PAYMENT_EVIDENCE`, `NO_GO`, `HOLD_FOR_PILOT_EVIDENCE`, `HOLD_FOR_COMMERCIAL_SCOPE`, `READY_FOR_OWNER_ROLLOUT_REVIEW`.

## Focused acceptance on authored bytes

- `python3 -m unittest -v test_rollout_desk.py`: **23/23 PASS**, exit 0.
- `python3 -O -m unittest -q test_rollout_desk.py`: **23/23 PASS**, exit 0.
- `python3 -m py_compile rollout_desk.py test_rollout_desk.py`: **PASS**, exit 0.
- Full example CLI: init → two evidence records → change-order follow-on → compile → verify: **PASS**; final decision `READY_FOR_OWNER_ROLLOUT_REVIEW`; change-order request retained as separately priced candidate.
- Hosted Actions: **not yet claimed**.

## Authored file SHA-256

- `MANIFEST.sha256` `e77819dbf941b4299aeb275f951512182d004b31f8ae6218430b26b8915d44ef`
- `README.md` `3377f71b0e254e9ce97068955f4ebb0c5c469f6b7650fc8758320f199d9ed097`
- `example_evidence_accuracy.json` `87e6903fd7460fc585b85a30f8f631bccd0863126408f673e06eb03aa43c44ee`
- `example_evidence_handoff.json` `ec00c9cce5412a6533fd5edae60f9fc46cf6cb97f7ef7f252ea710e2cf5f505d`
- `example_followon_change_order.json` `d0b2256d60d87b6eb37373a084d42fbbed296cb783689ce380bff9b99615c819`
- `example_pilot.json` `15ca8e66d60bc6313843bcf728b489fec76e8286798ff0aa64f3ce813ad4faa5`
- `rollout_desk.py` `56a39926876b0504e64a13d0b816bcd6fd90d90a0b3a0ce030007b034b84c480`
- `test_rollout_desk.py` `dc356b7af30cbe93b2c5d358d228daa60e062d7a2275bdf2bb364d1616ec0cc9`

The manifest is source-file hashes only; the receipt is intentionally outside that manifest so it does not self-hash.

## Authority ceiling

All persisted authority flags are required false. A compiled candidate always carries `buyer_acceptance=false`, `contract_signed=false`, `charge_authorized=false`, `payment_received=false`, and `revenue_recognized=false`. `PAID_EXTERNAL_EVIDENCE` means an authorized operator supplied an opaque evidence pointer; this product does not independently verify provider cash truth.
