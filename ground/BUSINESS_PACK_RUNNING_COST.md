# Business packs — running cost rides with “for this price”

SCOUT `#business-packs` `C0BU7JAPUH3` `1788327466.578309` (2026-09-02, owner creative direction relayed): any “for this price” line must carry the running cost the runbook already states. X and TikTok reject ads that omit expenses the customer will incur. “We did most of the work for you” is true only when the asset list is complete. “Become a business owner” waits on the owner’s ToS shape (LEAD `cursor-tjlabs-pack-tos-20260902-01`, slots `OWNER_UNSET`).

This is a factory-lane law. It is not a Commons login. Possessing a Commons link is still authorization. Agents do not invent a running-cost dollar, a tjlabs percent, or an equity fraction.

## Rules

1. Ads and doors that say **for this price** also state the **running cost**. Empty slot is `OWNER_UNSET` until the owner pastes it. Missing the cost on a price line is `EXPENSE_OMITTED`.
2. Do not invent the dollar amount. A number without `owner_pasted_running_cost` is `RUNNING_COST_INVENTED`.
3. Copy that calls the buyer a **business owner** / their own boss waits until ToS percent and ownership slots are owner-pasted. Until then: `OWNERSHIP_COPY_WAITS`.
4. “We did most of the work” needs a nonempty **asset list**. Otherwise `WORK_CLAIM_UNSUBSTANTIATED`.
5. Earnings figures stay out of ads. Checkout stays `NOT_MINTED`. This card does not write SCOUT `MESSAGING_ANGLE.md`, TALLY desk files, or thanks-channel helpers.

Machine map: [BUSINESS_PACK_RUNNING_COST.json](./BUSINESS_PACK_RUNNING_COST.json). Helper: [host/business_pack_running_cost.py](../host/business_pack_running_cost.py). Sheet: [packs/_template/running-cost.md](../packs/_template/running-cost.md). Unique-pack law: [BUSINESS_PACKS.json](./BUSINESS_PACKS.json). ToS (LEAD): [TJLABS_PACK_TERMS.json](./TJLABS_PACK_TERMS.json).
