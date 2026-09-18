# Buyer requirements gap and source-recovery ledger — 2026-09-17

This file records what is known, what is secondary, and what remains impossible to decide without the literal MMSD solicitation packet.

## Source recovery attempted

| Source / route | 2026-09-17 result | Authority |
|---|---|---|
| Indexed MMSD solicitation landing page | Search index still returns current buyer text; direct fetch returns 404 | Buyer text authoritative when indexed; direct current availability failed |
| Page's `Bid Document` link | Link target not exposed by current direct route | Unknown |
| Exact filename `FINAL-RFP-Comprehensive-AI-Policy-Development-1.pdf` on buyer domain | No authoritative PDF hit surfaced in current search | Not recovered |
| PublicBidSearch solicitation index | Current page identifies filename/timetable/scope and says 5 required items | Secondary only |
| WordPress JSON/media discovery routes | Not retrievable through the available web route in this recovery | No buyer bytes recovered |

### Required interpretation

`SOURCE_RECOVERY_BLOCKED` does **not** mean `CANCELLED`.

The buyer's indexed landing copy still describes a live October 16 deadline. Cancellation, replacement, amended schedule, or revised packet requires buyer-authoritative evidence.

## Decision matrix

| Requirement | State | Current evidence | What closes it |
|---|---|---|---|
| Buyer / opportunity identity | VERIFIED | MMSD indexed official page | Recheck buyer surface before external action |
| Qualified-consulting-firm framing | VERIFIED | MMSD indexed official page | None |
| GenAI + Operational AI scope | VERIFIED | MMSD indexed official page | None |
| Data sovereignty / public-record objective | VERIFIED | MMSD indexed official page | None |
| Proposal deadline 2026-10-16 16:00 CT | VERIFIED from indexed buyer page | MMSD indexed official page | Recheck for addendum |
| Email route + required subject | VERIFIED from indexed buyer page | `rfp@madsewer.org`, `Comprehensive AI Policy RFP` | Recheck for addendum |
| Proposal contents public record | VERIFIED | MMSD indexed official page | None |
| Questions deadline 2026-09-28 16:00 CT | SECONDARY | PublicBidSearch | Buyer PDF/addendum |
| Issue date 2026-08-31 | SECONDARY | PublicBidSearch | Buyer PDF metadata |
| No pre-bid meeting | SECONDARY | PublicBidSearch | Buyer PDF/addendum |
| Expected award ~2026-11-30 | SECONDARY | PublicBidSearch | Buyer PDF/addendum |
| Six-month term | SECONDARY | PublicBidSearch | Buyer PDF/contract |
| Shadow/embedded-AI audit | SECONDARY | PublicBidSearch | Buyer PDF |
| Stakeholder interviews | SECONDARY | PublicBidSearch | Buyer PDF |
| Vendor procurement framework | SECONDARY | PublicBidSearch | Buyer PDF |
| Incident response framework | SECONDARY | PublicBidSearch | Buyer PDF |
| Staff training / AI literacy | SECONDARY | PublicBidSearch | Buyer PDF |
| Exact five mandatory proposal items | **BLOCKED** | Index says five, hides checklist | Literal buyer PDF |
| Evaluation criteria / weights | **BLOCKED** | Not public in recovered text | Literal buyer PDF |
| Minimum firm experience | **BLOCKED** | Only generic "qualified consulting firm" is verified | Literal buyer PDF |
| Reference count / recency / sector | **BLOCKED** | Unknown | Literal buyer PDF |
| Subcontractor/team eligibility | **BLOCKED** | Unknown | Literal buyer PDF/contract |
| Prime-only vs team-combined qualifications | **BLOCKED** | Unknown | Literal buyer PDF/Q&A |
| Insurance / indemnity | **BLOCKED** | Unknown | Literal buyer PDF/contract |
| Required forms / signatures | **BLOCKED** | Unknown | Literal buyer PDF |
| Pricing format / budget | **BLOCKED** | Unknown | Literal buyer PDF |
| On-site / travel expectations | **BLOCKED** | Unknown | Literal buyer PDF |
| Contract/IP/confidentiality terms | **BLOCKED** | Unknown | Literal buyer PDF/contract |

## Commercial consequence

The correct present state is:

`TEAM_GO / PRIME_HOLD / FUNTO_PUBLIC_FIT_GO / FUNTO_QUALIFICATION_HOLD / OUTBOUND_HOLD`

The exact missing packet is now the dominant commercial blocker. Building another AI-governance engine would not close it.

## Packet acquisition ladder

Use the least noisy authoritative route that becomes available:

1. buyer landing page restored with working `Bid Document` target;
2. buyer Contracting Center replacement/current listing;
3. buyer-hosted PDF discovered under a canonical or attachment URL;
4. buyer addendum/Q&A page naming/replacing the packet;
5. only if the public packet remains unavailable and internal coordination authorizes it, one source-access question through the buyer's published RFP route, after Muse arbitration and collision census.

Do **not** scrape behind paywalls, treat third-party summaries as controlling, guess upload URLs into evidence, or infer requirements from unrelated MMSD solicitations.

## Time gate

If the secondary question deadline of **2026-09-28 16:00 Central** is confirmed, source recovery must occur early enough to:

1. identify only genuinely unanswered questions;
2. decide prime vs team;
3. let a proposed prime validate its own eligibility;
4. request clarification before the deadline without pitching or duplicating outreach.

## Exact next decision after packet recovery

Within one source-bound review, produce:

- document URL + SHA-256 + page count;
- addenda/Q&A list and precedence;
- five mandatory proposal items with page citations;
- all pass/fail firm qualifications;
- all reference requirements;
- all insurance/contract/form/signature requirements;
- all evaluation criteria/weights;
- all pricing/travel requirements;
- explicit subcontract/team rules;
- contradiction list against the retained packet;
- revised `PRIME_GO / TEAM_GO / NO_BID` state;
- revised Funto workshare and only then a candidate Muse-gated partner message.

No external communication is required to complete this internal recovery carrier.
