# NUMIH AI SAD admission-readiness compiler

Implementation successor to Commons #13751 for NUMIH / GIP MiPih dynamic purchasing system `2025-0154-00-00-MPF`.

The predecessor qualification identified four AI categories, a published 100-point admission rubric (20 legal/compliance, 30 recent AI references, 30 security/ethics/AI compliance, 20 economic/financial capacity), a 50-point admission threshold, and group/cotraitance / third-party-capacity mechanisms. The stated €75M HT overall need is system context, **not** an award, contract, or revenue result.

This package converts applicant + partner evidence into deterministic readiness artifacts. It never contacts NUMIH, logs into PLACE, certifies DUME, signs, prices, deposits a submission, predicts admission, or claims award/payment/revenue.

## Guarantees

- strict bounded JSON; duplicate keys, unknown fields, bool/int aliases and non-finite values fail closed;
- every `EVIDENCED` row has source locator, SHA-256 and generation;
- applicant-only legal evidence cannot be transplanted from a partner;
- partner capacity composes only with same-party evidenced commitment;
- weighted output is explicitly **published-rubric evidence coverage, not sponsor score**;
- categories 1–4 stay independently `EVIDENCED` or `HOLD`;
- unresolved non-French artifacts enter an owner translation/certification queue;
- DCE currentness is always `CURRENTNESS_UNVERIFIED`; caller metadata cannot self-mint PLACE freshness;
- receipt binds exact input and semantic result;
- all external mutation/admission/award/payment/revenue authority bits are false.

## Run

```bash
python -m revenue.numih_ai_sad_admission_readiness.cli \
  revenue/numih_ai_sad_admission_readiness/examples/fictional_partner_packet.json \
  --json-out /tmp/numih-readiness.json \
  --markdown-out /tmp/numih-readiness.md
```

Outputs are create-exclusive. The fixture is fictional and synthetic.

## Verify

```bash
python -m unittest discover -s revenue/numih_ai_sad_admission_readiness/tests -v
python -O -m unittest discover -s revenue/numih_ai_sad_admission_readiness/tests -v
python -m py_compile revenue/numih_ai_sad_admission_readiness/compiler.py revenue/numih_ai_sad_admission_readiness/cli.py
```

Before any real admission action, the owner must name/verify the actual applicant entity, refresh the authoritative PLACE DCE, confirm current foreign bidder and certificate/translation rules, verify partner commitments/capacity and current DUME/security/SSI/confidentiality materials, and handle any pricing/declaration/e-signature/deposit in the provider surface.
