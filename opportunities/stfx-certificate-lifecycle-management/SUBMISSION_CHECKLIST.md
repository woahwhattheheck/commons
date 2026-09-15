# Bid / submission control checklist

This is an internal control surface. Checking a box requires evidence; it does not authorize external contact or submission.

## A. Controlling procurement package

- [ ] Canonical buyer/portal opportunity record captured.
- [ ] Full solicitation downloaded and hashed.
- [ ] All appendices/schedules/forms downloaded and hashed.
- [ ] All addenda/amendments downloaded and hashed.
- [ ] Q&A / bidder notices downloaded and hashed.
- [ ] Closing date, exact time and timezone confirmed from controlling source.
- [ ] Question deadline/channel confirmed.
- [ ] Mandatory meeting/demo/site-visit requirement confirmed.
- [ ] Submission portal registration and file-format/size limits confirmed.
- [ ] Evaluation method, rated criteria and mandatory pass/fail criteria captured.

## B. Bid/no-bid legal and commercial gates

- [ ] Eligible bidding entity identified.
- [ ] Geographic / registration / Canadian-presence requirements satisfied or explicitly not required.
- [ ] Conflicts, debarment, declarations and supplier registrations reviewed.
- [ ] Insurance requirements evidenced.
- [ ] Contract terms reviewed by authorized owner; exceptions tracked.
- [ ] Currency, taxes, payment terms and pricing form confirmed.
- [ ] Initial term, renewal/options and termination terms confirmed.
- [ ] Data residency, privacy, security, breach-notification and subcontracting terms confirmed.
- [ ] Accessibility requirements confirmed.
- [ ] Required references and permission to use them confirmed.

## C. Product / partner gates

- [ ] Named CLM product and commercial route (resell/partner/subcontract) confirmed.
- [ ] Official product evidence mapped to each mandatory technical requirement.
- [ ] Required CA integrations confirmed.
- [ ] Required target/platform integrations confirmed.
- [ ] Identity/RBAC integration confirmed.
- [ ] API/export/audit capabilities confirmed.
- [ ] Key-custody and cryptographic architecture reviewed.
- [ ] Hosting/subprocessors/data location evidenced for SaaS/hybrid solution.
- [ ] Security certifications/attestations evidenced only if current and applicable.
- [ ] Vendor support and SLA commitments approved for quotation.
- [ ] Partner authorization / deal registration / quote validity evidenced if applicable.

## D. Technical response assembly

- [ ] Requirement matrix reconciled from PUBLIC to exact RFP section/page.
- [ ] Solution architecture edited to match the selected product and actual StFX environment facts.
- [ ] Integration matrix contains only confirmed systems and supported connectors.
- [ ] Discovery methodology and coverage assumptions stated.
- [ ] Lifecycle automation covers issue → deploy → validate → renew/revoke → retire.
- [ ] Failure/rollback behavior is explicit.
- [ ] Security/IAM/audit model is explicit.
- [ ] Implementation waves and acceptance gates align to buyer schedule.
- [ ] Training, documentation and handover match requested quantities/formats.
- [ ] Support model matches contract requirements.
- [ ] No claim depends solely on a third-party procurement mirror.

## E. Pricing control

- [ ] Official pricing form used without structural modification unless permitted.
- [ ] Software/license/subscription basis confirmed.
- [ ] Implementation/professional services hours or fixed fees approved.
- [ ] Support/maintenance included per required term.
- [ ] Optional services clearly separated if permitted.
- [ ] Currency and taxes confirmed.
- [ ] Travel/on-site assumptions confirmed.
- [ ] Renewal/escalation assumptions confirmed.
- [ ] Partner/vendor quote expiration exceeds buyer validity requirement.
- [ ] Margin/contingency reviewed by authorized commercial owner.
- [ ] Arithmetic independently checked.

## F. Final red-team

- [ ] Every mandatory requirement has an answer and evidence locator.
- [ ] No fabricated certification, client, integration, feature, SLA, price, legal status or staff commitment.
- [ ] Names/resumes/references have authorization to be submitted.
- [ ] Dates and version numbers agree across cover letter, technical response, forms and pricing.
- [ ] Exceptions/deviations are intentional and approved.
- [ ] Addenda acknowledgment complete.
- [ ] Required signatures complete.
- [ ] File names/formats/page limits followed.
- [ ] Portal upload validated before deadline; final files hashed/archived.
- [ ] Submission authority explicitly granted by owner.

## Immediate next handoff

1. Recover the buyer-controlled StFX/Nova Scotia procurement package and addenda without contacting the buyer unless an authorized owner directs it.
2. Update `SOURCES.md` with immutable metadata/hashes.
3. Replace PUBLIC/GATE rows in `REQUIREMENTS.md` with exact RFP references.
4. Decide product/partner route. If no defensible existing CLM solution can satisfy mandatory requirements, close NO-BID rather than proposing an unsafe greenfield security product on a procurement deadline.
5. Only after those gates, create pricing and proposal narrative.
