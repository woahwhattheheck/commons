# Required paperwork — help the customer file it

Bryce hub `1788327816.150299`: this pack helps the operator complete required paperwork. Fill every Do X line for this instance. Do not invent an EIN, a Stripe URL, a tjlabs percent, or a legal ruling. Slots stay `OWNER_UNSET` / `HOLD_COUNSEL` until the owner or counsel pastes them. This sheet is not legal advice.

Vertical:
Operator name:
State:
City:

This is a **state-specific instance** checklist, not a national list. Fill the buyer's state (and city when the licence or sign ordinance needs it).

## Registration / DBA

1. Do X: look up the Secretary of State / county assumed-name (DBA) portal for the instance jurisdiction and file only if this vertical uses a business name. Public how-to: [SBA register your business](https://www.sba.gov/business-guide/launch-your-business/register-your-business). This is a pointer, not a completed filing. Do not invent a filing number.
Status: `OWNER_UNSET`

## EIN

1. Do X: apply using the official IRS EIN assistant (public how-to; this is not a completed filing): [IRS EIN](https://www.irs.gov/ein). Do not pay a reseller. Do not invent an EIN.
Status: `OWNER_UNSET`

## Sales tax permit

1. Do X: look up the state Department of Revenue / seller's-permit page for the instance jurisdiction. Services are often not taxable; rentals of tangible goods often are. Public how-to: [SBA licenses and permits](https://www.sba.gov/business-guide/launch-your-business/apply-licenses-permits). Do not invent a permit number or a tax rate.
Status: `OWNER_UNSET`
`HOLD_COUNSEL` for the state form.

## Local business license

1. Do X: look up the city or county business-license / home-occupation page for the instance jurisdiction. Public how-to: [SBA licenses and permits](https://www.sba.gov/business-guide/launch-your-business/apply-licenses-permits). Do not invent a license number.
Status: `OWNER_UNSET`

## Insurance

1. Do X: owner-review checklist (general liability / auto as the vertical needs). Ask what limits a commercial account wants. Do not invent a premium, a carrier, or a “fully insured” line.
Status: `OWNER_UNSET`

## Contract

1. Do X: instance contract / invoice / client-agreement template with OWNER/COUNSEL markers. The buyer fills their details. Point at LEAD ToS (`packs/_template/terms.md`) for tjlabs share slots — do not invent the percent.
Status: `OWNER_UNSET`
`HOLD_COUNSEL`

## Not a Commons seat

Possessing the Commons link is still authorization. That is not a Commons seat. Paperwork is operator work, never a login. Paid tjlabs support is optional contact.

## Paperwork included (door copy)

“Paperwork included” / “with the paperwork done” is true only when every slot above is filled. Empty slots make that line `PAPERWORK_CLAIM_UNSUBSTANTIATED`.

This pack is checklists, links, and templates. It is not tjlabs doing the filing as their lawyer. “We filed your LLC” stays `HOLD_COUNSEL` (`PAPERWORK_FILING_CLAIM`) until counsel clears.

Never on the door: “we handle your legal paperwork”, “we set up your LLC”, “compliance guaranteed”.

## Formation partner (empty by default)

Link: `OWNER_UNSET`
Empty loads nothing. Owner pastes a licensed formation-service link. On-page FTC disclosure when filled: if you use this link, they pay tjlabs; you pay the same. Agents do not invent the URL.

Keep earnings figures out of ads. Prices, time budgets, and pasted running costs only.
