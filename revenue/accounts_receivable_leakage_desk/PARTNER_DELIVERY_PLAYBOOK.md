# AR diagnostics: partner qualification and delivery playbook

Internal seller/operator guide. This is a delivery method for existing desks, not
another product, a price change, a contract, or authority to contact a prospect.
Prepared 2026-09-17 by Z-Cairn-Astra-917E; operation
`AR-EXPLICIT-REMITTANCE-REVIEW-20260917`.

## Sell the review work, not an unsupported recovery promise

The paid deliverable is a reproducible explanation of supplied receivables and
remittance evidence: the source boundary, exact review queue, unresolved cases,
and an operator handoff. Do not sell a recovered-cash total, an automated posting
service, or a replacement for the partner's accounting team. The reusable software
reduces repeated implementation work; the paid service still needs a responsible
source owner and a bounded scope.

A suitable partner conversation tests whether the firm has an overflow or
exception-review problem that it would pay an outside specialist to resolve.
Already offering receivables services is evidence of workflow relevance, not
proof that the firm needs a subcontractor. Existing internal capability, client
confidentiality restrictions, or an inability to supply bounded exports may make
an otherwise relevant organization unsuitable.

## Choose one canonical offer before quoting

| Actual customer question | Existing route | Scope and commercial reference | Boundary that must survive the sale |
| --- | --- | --- | --- |
| Which invoices remain open or overdue after payments, credits and disputes? | Commons Accounts Receivable Leakage Desk | $2,500 fixed diagnostic reference; one sanitized USD export generation, up to 5,000 invoices | Raw invoice/event aging; unattributed payments remain unattributed. A recovery-candidate total is not collected cash. |
| Receipts exist, but remittance advice is missing, partial, competing or ambiguous. What should an operator investigate? | SMB Unapplied Cash & Remittance Matching Desk | $4,000 proposed fixed diagnostic; one entity, one currency, up to 500 receipts and 1,000 open invoices, one review generation | Its exact-amount single-invoice candidate is review-only. Preserve its own complete-generation and current-versus-historical rules. |
| The operator already has explicit payment-to-invoice instructions. Do splits and partial amounts fit the remaining balances, and what residuals remain? | Commons explicit-remittance review extension, PR #15868 | No separate SKU or additional price. Confirm inclusion in an accepted diagnostic scope; code capacity is not an offer expansion. | Supplied remaining-balance snapshots, USD only, no guessed matching or current-provider authority. Connected conflicts hold together. |

The Commons reference is documented in the [canonical README at the observed
base](https://github.com/woahwhattheheck/commons/blob/318f80cff57fbef7d026622db3a65ebebc38c07c/revenue/accounts_receivable_leakage_desk/README.md).
The distinct SMB scope is documented in [merged PR #287](https://github.com/woahwhattheheck/smb-showcase-inventory/pull/287),
merge `e98c63e08363727d8912b0eb885e46955743c493`. Re-read the live canonical offer
and relationship record before preparing a quote. These source references do not
establish buyer acceptance, cash, a reserved price, or a right to substitute one
scope for the other.

The extension's [source PR #15868](https://github.com/woahwhattheheck/commons/pull/15868)
was still open when this guide was prepared. Source/test blobs were independently
reviewed and locally executed, but hosted integration proof was incomplete.
Publishing this guide does not release that code. Use a demonstrably merged,
reviewed generation for a production delivery; label an evaluation candidate as
such and use only synthetic data for its demonstration.

**Never quote both desks independently to the same organization because different
agents found it.** Reconcile the earlier relationship and decide which problem is
actually being purchased. Do not use the extension's higher technical capacity to
undercut the earlier SMB proposal or silently widen either fixed-fee engagement.

## Qualification: six answers before bespoke work

Ask for business facts and sanitized schema examples, not the full client ledger
in an initial message. Record answers in the existing private relationship record;
keep client data and correspondence out of the public source repository.

| Question | What the answer decides |
| --- | --- |
| Is the problem aging/event reconciliation, missing advice, or checking explicit instructions? | Select the route above. Missing advice cannot be manufactured by the explicit-allocation extension. |
| What entity, currency, period, row counts and source systems are involved? | Check the canonical offer and technical limits. Mixed currencies, reversals and multiple entities are not silently coerced into a supported snapshot. |
| Can an authorized operator supply stable native IDs, remaining invoice balances, unapplied receipt balances and the actual instruction references? | Decide whether the evidence can support this review at all. A gross bank deposit is not automatically an available amount. |
| Who owns the export boundary and who will decide disputed or ambiguous cases? | Establish an accountable source owner and a human recipient of the exception queue. We do not make the customer's posting decisions. |
| Can the parties agree an appropriate private transfer, access, retention and deletion arrangement? | Confirm that the work can be done without credentials, uncontrolled copies, or public client-data exposure. Do not promise a certification or a specific retention policy that has not been adopted. |
| Who can accept a fixed-fee diagnostic, what deliverables matter, and what would make the result unusable? | Find a real buying path. A useful conversation, a technical PASS, and commercial acceptance are three different events. |

Stop the presales build when the answer is “build an ERP connector first, then we
might buy.” A synthetic demonstration and a schema discussion are reusable
presales work; a bespoke adapter, full client-ledger cleanup, or unpaid production
trial is a new scope decision. Quote that work explicitly rather than hiding it
inside the diagnostic.

## Source preparation for the explicit-allocation route

Use one agreed snapshot generation. The source owner retains the original exports
and the mapping from opaque review IDs back to its systems. The operator keeps
that mapping in the agreed private environment, not in the deliverable's free-text
fields. IDs being syntactically safe does not prove they contain no personal data.

| Review field | Required interpretation | Reject or clarify instead of guessing |
| --- | --- | --- |
| `snapshot_id` | Same agreed generation on all three files and every row | Files exported across an unexplained change of period or ledger state |
| Invoice `remaining_minor` | Invoice balance still available to this proposal after already-posted source activity | Original face value, a signed reversal, or a computed balance with no explained source boundary |
| Payment `available_minor` | Receipt amount not already applied in the source system | Gross deposit amount when earlier applications are unknown |
| `source_event_id` | Stable native source identity, unique within the invoice or payment input | A new display ID used to import the same native event twice |
| `account_id` | Consistent opaque customer/account identity across the two sources | Name-only similarity or an assumed cross-account transfer |
| `amount_minor` | Positive integer USD cents explicitly proposed for the named pair | Decimal dollars, negative amounts, FX conversions, inferred discounts or write-offs |
| `remittance_ref` | Opaque reference to the owner's retained explicit instruction | An amount/date coincidence relabeled as customer advice |
| `analysis_date` | Agreed analytical horizon | A claim that the program checked the bank today or authenticated completeness |

The program can check internal consistency but cannot independently establish the
truth of an ERP or bank export. Export counts and totals should be reconciled with
the source owner before delivery, including any excluded rows and the reason for
each exclusion. Do not silently discard unsupported cases to obtain a clean run.
If the required boundary cannot be explained, return an intake exception report
rather than a favorable reconciliation conclusion.

Microsoft's own [manual customer-entry application documentation](https://learn.microsoft.com/en-us/dynamics365/business-central/receivables-how-apply-sales-transactions-manually)
describes explicit partial and multiple-entry amounts. That supports the workflow
shape, not an integration claim. This review service deliberately stops before
any posting operation described there.

## Delivery sequence and acceptance evidence

**1. Confirm the paid work boundary.** Retain the accepted scope and source-owner
instructions through the existing commercial process. Specify the chosen desk,
entity/currency, snapshot, limits, deliverables, exclusions and treatment of
out-of-scope normalization. Do not invent an acceptance receipt, reserve Bryce's
time, promise a delivery date on Bryce's behalf, or mark money received from a
conversation alone.

**2. Preserve and normalize.** Receive only the authorized, sanitized source set
through the agreed private channel. Keep the exact originals and a transformation
record: source columns, ID mapping location, unit conversion, source totals,
excluded rows, and generation boundary. Use a new output directory. Never reuse
old “approved” flags or a prior snapshot as current evidence.

**3. Compile and verify.** For a released explicit-remittance generation, follow
its pinned operator documentation for JSON or three-CSV intake. Retain the exact
command, runtime, source generation, source hashes, report and queues. Run the
bundle verifier; a self-hash check alone is not sufficient. The verifier must
regenerate JSON, CSV, Markdown and the manifest from the retained inputs.

**4. Review the exceptions with the operator.** Triage by connected component, not
CSV order. Identify unknown references, duplicate native events or pairs, account
conflicts, unsupported currency, chronology, invoice status and capacity issues.
Keep unreferenced receipts visible. Correct facts only from the responsible source
owner's evidence, retain the predecessor, and rerun as a new generation. Never
repair a report directly to make its totals look acceptable.

**5. Deliver the review and residuals.** Include a brief explaining scope and
limitations, the normalized source, original sanitized input bytes, allocation
queue, payment residuals, invoice residuals, every finding, canonical report and
manifest. The external package should contain no internal Slack conversation,
Commons/customer backlink, credentials, or hidden tracking mechanism.

**6. Obtain operational acceptance separately.** Ask the named recipient to confirm
that the agreed files are usable, the source boundary is understood, exceptions
are visible, and the next human actions are assigned. Technical PASS is not their
acceptance. A buyer's acceptance is not proof of settlement; use the existing
finance/commercial evidence process for any payment claim.

### Reusable demonstration and delivery checks

The synthetic clean example has 18,000 cents of invoice remaining balances and
17,000 cents of available receipts. Explicit instructions propose 13,000 cents;
hypothetical invoice and payment residuals are 5,000 and 4,000 cents respectively.
No actual cash, client data or savings is represented by these fixture values.

In a connected-conflict demonstration, over-requesting invoice 2 and receipt 2
holds the instructions sharing invoices 1/2 and receipts 1/2. A separate valid
receipt 3 to invoice 3 instruction can still propose 3,000 cents. Merely sorting
the CSV differently must not let the first request win.

| Acceptance check | Evidence to retain |
| --- | --- |
| All supplied rows are accounted for | Source counts/totals, normalization record, exclusion explanations and visible unknown/unreferenced queues |
| Money is conserved without posting | For every payment: available = proposed + hypothetical unapplied. For every invoice: remaining = proposed + hypothetical remaining. |
| Conflicts propagate deterministically | Connected-conflict demonstration, independent control, and row-permutation proof |
| Artifacts match their inputs | Successful full bundle verification from retained raw inputs, including CSV and Markdown |
| The recipient can act | Named human ownership of unresolved cases and an explicit acceptance response for the agreed deliverables |
| Commercial reporting is truthful | Quote, acceptance, invoice and settlement remain separately evidenced events; no synthetic amount enters a sales or cash total |

## Partner research: reuse the earlier account lane

Supporting Strategies is a workflow-relevant research candidate: its [May 28,
2026 AR article](https://www.supportingstrategies.com/blog/when-should-a-small-business-outsource-accounts-receivable/)
discusses payment application, receivables reporting and month-end coordination.
Its [service page](https://www.supportingstrategies.com/services/) advertises AR and
operational services and explicitly states that it is not a CPA firm. These are
first-party descriptions, checked 2026-09-17, not an inbound lead, a statement of
unmet need, or evidence of purchasing authority.

An earlier internal research-only lane already included this organization:
`SMB-UNAPPLIED-CASH-COMMERCIAL-ZLHK8P4-20260914`, preserved by ZLH-K8P4 and tied to
SMB #287. This guide donates qualification and delivery material to that earlier
lane; it does not claim the organization or initiate a parallel pursuit. Reconcile
its current carrier and any later contact before using this research. Historical
“no messages found” is not a permanent contact clearance.

An internal draft of the commercial question, to adapt only after qualification
and authorization, is:

> We offer fixed-fee receivables reconciliation diagnostics for bounded, sanitized
> export generations. The deliverable is an evidence-backed exception queue and
> operator handoff, not an automated posting service or free custom integration.
> Does your team ever use outside support for overflow remittance or close-review
> work, or is this handled entirely in-house?

This is not a send-ready email, a chosen recipient, or a claim of partnership.
Before any outbound, recensus the exact organization/domain, existing inbox/sent/
draft records and relationship state; obtain Muse's current single-sender
adjudication for the exact proposed contact; preserve any buyer-specific or owner
approval requirement. Muse prevents duplicates; it cannot accept a scope, change a
price, book Bryce, approve a financial action, or convert a hot lead's draft into
owner approval. A queued request, silence, an expired selection, or another
agent's send is not permission to send again.

## Productive follow-on work after a real qualification event

The next useful deliverable is a paid, agreed source-mapping and exception-review
engagement using one existing desk. With real sanitized samples and an accepted
scope, create a retained schema mapping, a customer-independent regression fixture,
and a tested normalization path. Record every unsupported case instead of
extending currency or posting semantics implicitly.

A recurring-close proposal should follow observed delivery: show the operator
which steps repeat, the review workload actually incurred, the unresolved cases
and the proposed next snapshot. Use measured work to discuss price and cadence;
do not claim hypothetical recovered dollars or extrapolate one synthetic example
into a recurring revenue forecast. This keeps expansion tied to buyer value rather
than adding more unsold products.
