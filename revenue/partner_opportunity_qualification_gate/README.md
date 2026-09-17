# Partner Opportunity Qualification Gate

Issue: #15596  
Operation: `PARTNER-OPPORTUNITY-QUALIFICATION-GATE-ZFO1404-20260917`

This package sits **after** `revenue/procurement_runway_gate`. The existing runway gate answers whether an opportunity has usable proposal runway and whether a plausible partner has evidenced delivery capacity. This gate answers a different question:

> Is there enough source-bound bidder/partner qualification evidence to bring this opportunity to a partner without pretending the partner is eligible, registered, insured, referenced, locally present, screened, or otherwise qualified when those facts are still unknown?

A timing-ready opportunity is not automatically qualification-ready.

## Output states

Per partner, the compiler emits exactly one bounded state:

- `READY_FOR_MUSE_ELECTION_ONLY` — upstream runway is `READY`; upstream relationship/collision policy admits a separate Muse election; all `PRE_OUTREACH` hard gates are satisfied by current evidence of each gate's explicitly required evidence kind; registration/screening is not closed/unknown; and a paid TJLabs workshare is defined.
- `READY_FOR_CAPACITY_MUSE_ELECTION_ONLY` — the same qualification conditions hold, but the upstream runway gate is `ASK_CAPACITY_FIRST`. This authorizes nothing; it says only that a separately elected capacity question is the next possible external edge.
- `HOLD_SOURCE` — solicitation-control evidence is stale/unknown.
- `HOLD_RUNWAY` — the upstream runway state/partner selection does not admit the partner.
- `HOLD_CONTACT_POLICY` — upstream DNR, inbound-only, unknown relationship, or collision state dominates.
- `HOLD_REGISTRATION` — registration/screening is unknown, closed, expired, or supported by stale evidence.
- `HOLD_HARD_GATE` — a pre-outreach gate is unsatisfied, unknown, or backed by stale evidence.
- `HOLD_NO_PAID_SEAM` — qualification is otherwise bounded but no paid TJLabs specialist workshare is defined.

Unknown is never upgraded to satisfied.

## Exact evidence binding

Every retained source has:

- `source_id`
- a role (`SOLICITATION_CONTROL`, `PARTNER_EVIDENCE`, `REGISTRATION_EVIDENCE`, or `OWNER_WORKSHARE_EVIDENCE`)
- `CURRENT | STALE | UNKNOWN`
- exact HTTP(S) URL
- exact SHA-256 of the retained bytes
- `observed_on`
- `subject_partner`

`PARTNER_EVIDENCE` and `REGISTRATION_EVIDENCE` must name exactly one `subject_partner` that exists in the packet. `SOLICITATION_CONTROL` and `OWNER_WORKSHARE_EVIDENCE` must keep `subject_partner: null`. This is a retained operator classification used for deterministic routing; it is **not** an external certification that the evidence is true or legally sufficient.

Every source reference carries **both source ID and SHA-256**. Reusing the same source ID after its bytes change therefore creates a new semantic generation; an old receipt cannot verify against it. The same retained URL or bytes cannot be relabeled across evidence kind or partner subject, so duplicate aliases cannot turn an RFP into partner proof or transplant one partner's evidence onto another candidate.

Hard-gate definitions must cite at least one `SOLICITATION_CONTROL` source, and every solicitation-control URL must also be present in the exact upstream runway opportunity's `source_urls`. This prevents a hard-gate packet for one solicitation from being transplanted onto another runway row.

Each hard gate must also declare one closed `required_evidence_kind`:

- `PARTNER_EVIDENCE`, or
- `REGISTRATION_EVIDENCE`.

A decided disposition (`SATISFIED` or `UNSATISFIED`) must cite current exact-digest evidence of **that gate's declared kind bound to that exact partner**. A generic partner capability source cannot satisfy a registration-specific gate, registration evidence cannot satisfy a gate explicitly requiring ordinary partner evidence, another partner's evidence cannot satisfy this partner's gate, and the RFP/addendum that defines the requirement cannot prove the partner's disposition.

Registration deliberately separates:

- `requirement_refs`: controlling `SOLICITATION_CONTROL` evidence that says what registration/screening is required; and
- `evidence_refs`: partner-specific evidence that the requirement is actually complete.

`registration.state = COMPLETE` requires at least one exact `REGISTRATION_EVIDENCE` source whose `subject_partner` is the partner being evaluated. An RFP, generic `PARTNER_EVIDENCE`, `OWNER_WORKSHARE_EVIDENCE`, or another partner's registration source cannot mint registration completion.

## Gate phases

Each solicitation gate is classified as:

- `PRE_OUTREACH`
- `PRE_SUBMISSION`
- `PRE_AWARD`

Only unresolved `PRE_OUTREACH` gates block a partner approach. Later unresolved gates are retained in the output as later-stage holds; a `READY_*` state is **not** submission readiness, award eligibility, or a certification that a partner satisfies those later gates.

The phase, requirement text, and required evidence kind are retained owner interpretations of the controlling packet. The compiler does not read legal text or determine eligibility itself.

## Upstream runway composition

The input embeds exactly one ordinary `procurement-runway-gate-input/v1` packet. This compiler normalizes the exact upstream runway input document, invokes the canonical upstream compiler, creates its deterministic receipt, runs the upstream semantic verifier, and binds the normalized upstream input, upstream output, and upstream receipt SHA-256 values into the qualification output and receipt. A semantic runway-input generation change therefore cannot replay an older qualification receipt merely because it happens to compile to the same runway output.

The qualification packet's `as_of` and `opportunity_id` must match that upstream packet exactly.

## Authority ceiling

Every output row, top-level output, and receipt hard-carries false authority for:

- partner contact
- buyer contact
- Muse election result
- account registration
- eligibility certification
- portal submission
- signature
- contracting
- award
- payment
- cash received
- revenue recognition

`READY_FOR_MUSE_ELECTION_ONLY` means exactly what it says: a separate current collision census + exact Muse single-writer election is still required before any message. It is not send authority.

The compiler is offline metadata integrity. It does not fetch URLs, log into SAM or procurement portals, validate insurance policies, run background checks, certify bidder eligibility, submit bids, or contact anybody.

## Synthetic reference packet

`synthetic_input.json` is intentionally fictional. It demonstrates:

- one source-bound solicitation;
- exact upstream runway composition;
- an active-SAM example as a `PRE_OUTREACH` hard gate;
- explicit gate-specific required evidence kinds;
- a three-reference gate retained for `PRE_SUBMISSION`;
- registration requirement evidence separated from exact registration-completion evidence;
- explicit per-source partner-subject binding for partner/registration evidence;
- a bounded `$5,000` owner-authored TJLabs workshare;
- all external/commercial authority false.

Do not treat the synthetic URLs or values as a live lead.

## CLI

```bash
out="$(mktemp -d)/qualification"
python -m revenue.partner_opportunity_qualification_gate compile \
  revenue/partner_opportunity_qualification_gate/synthetic_input.json \
  --output-dir "$out"

python -m revenue.partner_opportunity_qualification_gate verify \
  revenue/partner_opportunity_qualification_gate/synthetic_input.json \
  --output-dir "$out"
```

`compile` creates its output directory exclusively and writes canonical `qualification.json` + `receipt.json`. `verify` recompiles both this gate and the upstream runway gate and rejects drift.

## Validation

```bash
python -m py_compile revenue/partner_opportunity_qualification_gate/*.py
python -m unittest -v revenue.partner_opportunity_qualification_gate.test_gate
python -O -m unittest -v revenue.partner_opportunity_qualification_gate.test_gate
python -m unittest -v test_partner_opportunity_qualification_gate.py
```

The hostile suite covers upstream-input generation remint with unchanged runway output, source-digest remint, solicitation-source transplant, stale source/evidence, registration requirement-vs-completion separation, generic partner evidence attempting to mint registration completion, cross-partner SAM/registration evidence transplant, orphan/nonpartner subject claims, source identity retyping/rebinding, missing/invalid gate evidence-kind declarations, cross-kind gate evidence transplant, unknown/expired registration, unknown pre-outreach gates, DNR dominance, missing paid seam, missing/duplicate gates, strict integer typing, duplicate JSON keys, order invariance, semantic receipt verification, and the separate capacity-question state.
