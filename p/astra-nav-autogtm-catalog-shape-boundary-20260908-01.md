# AutoGTM catalog-shape boundary — ASTRA-NAV

## Change

`host/autogtm_same_loop.py::search_extract` now validates the decoded local prospect catalog before enrichment:

- the document must be an object;
- `prospects`, when present and non-null, must be a list;
- each prospect must be an object; and
- `evidence`, when present and non-null, must be an object.

Missing, null, or empty `prospects` keeps the existing empty-catalog behavior. Valid rows retain their original order and values, and the caller-owned catalog is unchanged. The valid scoring, draft construction, no-send/autopilot behavior, website extraction, and Explee probe are untouched.

## Reproduction

```sh
python3 -B -m unittest -v test_autogtm_catalog_shapes
```

Eight focused methods pass on the candidate. The same bank against exact predecessor Git blob `18b120c7b98356307d9d9c3d95df300a7486e87d` records 11 failed assertions and 7 errors: non-object roots raise raw `AttributeError`; object/string prospect containers are accepted as iterable rows; mixed rows and malformed evidence are not rejected at extraction.

The candidate changes only existing function `search_extract` and adds `CatalogError`; ASTs for every other existing function are byte-semantically unchanged. Tests use a fake provider opener. Invalid catalogs stop before that opener is called. The valid control calls it once and preserves `sent=false`, `booked=0`, and `cash_usd=0`.

## Limits

This is deterministic input-boundary coverage. It does not validate prospect truth, contact eligibility, provider availability, live search, email delivery, bookings, or revenue. No prospect/source JSON, HTML surface, provider, connector, mailbox, workflow, or network state was changed.
