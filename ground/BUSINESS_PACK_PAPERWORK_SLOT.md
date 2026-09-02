# Business packs — paperwork is a shared factory slot

Bryce hub `C0BU51F1PL3` `1788327816.150299` (2026-09-02): packs help the customer with required paperwork. The checklist factory is a **shared slot**, not a sold instance.

CLEAR `cursor-plant-yard-greeting-pack-20260902-01`. LEAD `bc-23891c63` keeps LotRibbon paths. This card does not write `packs/lotribbon-greetings-20260902-01/**` or `ground/BUSINESS_PACK_PLANT.json`. It does not remint the landed checklist `cursor-business-pack-paperwork-20260902-01`.

An instance may **fill** the factory slot (registration, EIN, sales tax, license, insurance, contract). An instance may not **own** the factory. `paperwork` is not an instance fingerprint field like assets, brand, checkout, or instructions.

This is not legal advice and not a Commons login. Slots stay `OWNER_UNSET` / `HOLD_COUNSEL`. Checkout stays `NOT_MINTED`. No franchise vocabulary. No earnings copy. Possessing a Commons link is still authorization.

## Rules

1. `paperwork_home` is `factory` / `shared` / `slot` / `template`. That is `SHARED_SLOT_OK`.
2. `paperwork_home=instance` (or LotRibbon / plant owning the factory) is `INSTANCE_OWNED`.
3. Writing LEAD plant paths from this seat is `PLANT_INSTANCE_EXCLUDED`.
4. Rewriting the landed checklist factory files is `FACTORY_PATH_STOLEN`.
5. Legal-advice claims, franchise vocabulary, and earnings copy are flagged. They are not admission gates.

Machine map: [BUSINESS_PACK_PAPERWORK_SLOT.json](./BUSINESS_PACK_PAPERWORK_SLOT.json). Helper: [host/business_pack_paperwork_slot.py](../host/business_pack_paperwork_slot.py). Checklist factory (do not remint): [BUSINESS_PACK_PAPERWORK.json](./BUSINESS_PACK_PAPERWORK.json).
