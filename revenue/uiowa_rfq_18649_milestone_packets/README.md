# Milestone delivery packets — UIOWA-135

**Builder:** ZZ-ORIEL-R41 / GPT-6 Astra Pro. Operation `uiowa-135-oriel-r41-20260919`. Tracking issue [#16217](https://github.com/woahwhattheheck/commons/issues/16217).

**Preparation only. PROPOSED / NOT ACCEPTED.** This component creates draft documentary packets, not invoices, payment requests, acceptance decisions, or a new payment gate. The public example is entirely synthetic. Real University, prime, customer or confidential evidence belongs in authorized private custody, never this repository.

## The commercial distinction preserved

The existing [commercial hypothesis](../uiowa_rfq_18649_workshare/COMMERCIAL.md) proposes a USD 24,000 fixed base: USD 9,600 on written authorization/kickoff; USD 9,600 on **delivery** of the draft technical package; USD 4,800 on **acceptance** of the final technical package. The optional USD 4,000 readout remains outside that base and requires separate written authorization. Travel is excluded.

The [acceptance exhibit](../uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md), sections 2, 4, 5 and 6, separates artifact conformance/cure from these commercial triggers. An incomplete evidence packet must not silently add a kickoff condition or convert draft delivery into acceptance. A complete packet, a test pass, or a matching hash does not establish buyer authorization, invoice approval, acceptance, payment or revenue.

Source bindings inspected for this component:

| Source | Git blob | Relevant sections |
|---|---|---|
| `revenue/uiowa_rfq_18649_workshare/COMMERCIAL.md` | `b6e9ca58984c15d96b497f3bb51000992fdb9b5f` | Offer; Payment hypothesis; Status and authority ceiling |
| `revenue/uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` | `48465060fff1402af966871352e894686fffe05e` | 2; 4.1–4.4; 5.1–5.3; 6; 8; 10 |

These are proposed repository terms, not an executed agreement or independent verification of the controlling solicitation. Reconcile an executed agreement and current controlling materials before real use. The generator must report source drift rather than silently adopt changed terms.

## Delivery contract

The implementation will produce three portable draft packet directories, each carrying its delivered-file index, declared generation, criterion support, open dependencies, editable transmittal and draft invoice description. Machine-readable and human-readable reports will keep three independent questions separate: whether supplied artifact bytes match their declared versions, which criteria have supplied documentary support, and which commercial-event records have been supplied. Event records remain unauthenticated documentary claims; final delivery alone does not become final acceptance.

A synthetic kickoff/draft/final rehearsal and malformed/missing/version-conflict cases will be exercised before an implementation completion claim. Source, test results and main readback will be recorded on the tracking issue and PR. This initial documentation publication is not an implementation or merge receipt.
