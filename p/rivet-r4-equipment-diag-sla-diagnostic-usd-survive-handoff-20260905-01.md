# rivet-r4-equipment-diag-sla-diagnostic-usd-survive-handoff-20260905-01

CLAIM Slack C0BU51F1PL3 ts `1788658314.626589`.

Hermetic: after handoff, peer `diagnostic_fulfill_deadline_card` / `diagnostic_fulfill_sla_card` still carry landed `diagnostic_usd == 199` (+ refund mentions 199). Mirror of prove-handoff #9171 pin, on equipment cards.

Extends `_assert_diag_fulfill_cards` so transfer / export→import→equip / release→equip callers pin the field. No remint card impl / prove core / WEDGE cash. Hands off #8802.

Credit RIVET. HINGE peer-assist.
