# Format references and provenance limits

Research checked 2026-09-17/18. No bank/customer exports were obtained. The two shipped XML fixtures are generated synthetic examples; their presence is not proof of bank certification or complete XSD conformity.

## ISO 20022: Bank-to-Customer Cash Management MDR, 2018/2019

Primary reference:
https://www.iso20022.org/sites/default/files/documents/messages/mdr_part_2/ISO20022_MDRPart2_BankToCustomerCashManagement_2018_2019_v1_0.pdf

Relevant printed sections describe `camt.053.001.08`, booked statement entries and underlying detail, entry credit/debit direction and reversal indication, pagination, and the separate entry/detail amount roles. The statement scope is discussed on PDF page 38; statement pagination on page 46; direction/reversal on page 61 (PDF pages are one-based here). These anchor the no-double-counting and no-second-sign-flip decisions. They do not establish a particular bank's delivery completeness or accounting acceptance.

The supported version is explicit, not described as the latest. The official message archive was inspected, but schema download did not succeed in this execution environment. **No official-XSD validation result is claimed.** A future profile acceptance pass should retain the relevant official XSD plus applicable external code sets and bank-specific constraints, then validate the exact fixtures and buyer-approved cases.

## Westpac BankRec: ISO cash-management statement guide

Primary reference:
https://bankrec.westpac.com.au/docs/statements/iso/cash-management

This bank-published guide documents a .02 profile, multiple accounts and bulk entries with underlying detail. It informs the v2 field-shape examples, not an assertion that the generic workbench is certified for Westpac facilities. Its displayed closing-balance code includes `CLDB`; the generic extractor does not silently alias that to `CLBD`. Such a discrepancy needs facility-specific clarification rather than an invented normalization.

## What the hashes prove

Source SHA-256 values identify the exact retained bytes. Output digests and recompilation identify derived bytes under this implementation. Neither is a digital signature from ISO, a bank or a customer. The source publications were read through web tools; their original PDF/site bytes are not bundled or redistributed here. Production fixtures and mapping decisions must be tied to the buyer's actual bank profile and delivery generation.
