# UIOWA-136 — Bid attachment assembly and navigation

**Partial prime-review draft, not a completed bid.** This lane turns the supplied, existing TJLabs commercial component into an actual seven-page PDF, editable DOCX and complete offline HTML review folder. It also supplies a navigable attachment index, genuine source copy, financial/qualification gap files and original-edition requirement reconciliation. It does not invent a full prime proposal or missing bidder evidence.

## Use the prepared packet

The `sample/` folder is the handoff: open `00_START_HERE.html`, or open `01_REVIEW_DRAFT.pdf` / `.docx` directly. The complete HTML view requires no server, account, JavaScript or development tools. The PDF has six outline entries and nineteen internal links. The DOCX has six heading bookmarks, nineteen internal links and nineteen `PAGEREF` fields. The HTML has twenty-one checked local/section links. Financial/qualification files are visibly marked missing, never counted as supplied bidder attachments.

GitHub links in this README are internal engineering evidence, not customer destinations. Use the files themselves through the authorized delivery surface; do not send a prospect to Commons or a repository download page as a delivery CTA.

## Reproduce and verify

From this directory, with Python 3.11+ and the versions in `requirements.txt`:

```sh
python -m unittest -v test_assembler.py
python -O -m unittest -v test_assembler.py
python assembler.py build inputs/packet.json /existing-parent/new-review-folder
python assembler.py verify /existing-parent/new-review-folder
```

`build` requires a **new** output directory. It neither empties nor overwrites an existing directory. A failed build keeps its own `BUILD_INCOMPLETE.txt` marker and partial outputs for inspection; it never deletes a caller's directory. Its only deletion is that marker inside the exclusively created output after successful build checks. Inputs are not modified. No network calls, paid services, buyer messages, submissions or scheduling occur.

The ten-file output set is exact. The verifier opens the DOCX, PDF and text/JSON/HTML outputs, rechecks copied source SHA-256 and Git blob identity, hashes all payloads, verifies PDF outlines and every PDF target page, checks DOCX bookmarks/page-field targets and cached page numbers, and checks the HTML links. The output manifest excludes its own hash to avoid a circular checksum. Retain its hash separately when independent custody matters.

## What is actually supplied

The source is the existing `revenue/uiowa_rfq_18649_workshare/COMMERCIAL.md`, 2,621 bytes, Git blob `b6e9ca58984c15d96b497f3bb51000992fdb9b5f`. Its words, proposed $24,000 base, separately authorized $4,000 option, 40/40/20 milestones and travel exclusion remain unchanged. An executable text-conservation test checks every original paragraph against the PDF. The original exhibit was read for context but is not replaced or reproduced here. Original authors retain attribution.

Internal source evidence:
- https://github.com/woahwhattheheck/commons/blob/main/revenue/uiowa_rfq_18649_workshare/COMMERCIAL.md
- https://github.com/woahwhattheheck/commons/blob/main/revenue/uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md
- Work carrier: https://github.com/woahwhattheheck/commons/issues/16259

The sample uses no synthetic University findings, names, credentials, reference engagements or financial statements. It is a real assembly of an existing proposed commercial component plus explicit gaps, not a fictitious completed proposal.

## Requirement and currentness limits

The original RFQ's selected attachment obligations were read with printed-page/attribute locators, including financial statements **and annual reports for the preceding two years**, the required proposal, prime qualifications/references and the all-inclusive **prime** fee. That fee is not the TJLabs subcontract amount. Agency-supplied reference documents are distinguished from bidder uploads. The exceptions response is not filled with an invented certification.

The inspected original invitation reports September 22, 2026; the prepared exhibit/work order reports September 29. The current official amendment was not independently obtained. The packet retains that discrepancy as **CURRENT AMENDMENT NOT VERIFIED**. It does not certify either date as current. Full source route and limitations are in `inputs/source_register.md` and the packet's `08_SOURCE_REGISTER.md`.

UIOWA-131's complete 36-attribute field renderer, UIOWA-132's commercial-facts work and UIOWA-123's general pagination engine remain separate. This lane does not replace them or claim their results. Complete prime narrative, current amendment, eBid responses, real financials, qualifications, all-inclusive prime price and prime decisions are not supplied in this sample.

## Validation and boundaries

The retained suite has real-build, deterministic-output, source-conservation and negative-control coverage. It rejects source/hash drift, JSON duplicate keys/non-finite values, missing requirements, invented approval status, malformed paths/symlinks, changed output sets, changed bytes, wrong PDF links after rehashing, broken DOCX bookmarks/fields/cached pages, and wrong HTML links. Oversized content is refused as pagination overflow, not silently clipped. Unsupported PDF glyphs are refused rather than replaced.

A passing packaging receipt is **not** an authenticity, security, eligibility, financial, legal, accessibility-compliance or bid-completeness certification. Manifest hashes are unkeyed and caller-held; replacing every payload and its matching manifest does not establish independent provenance. The local filesystem must have trusted parent directories; these checks are not an adversarial multi-user sandbox. The snapshot layout is one page per section; materially longer components require a layout change and fresh rendered review rather than automatic unreviewed pagination.

The build records `visual_review: NOT_ESTABLISHED_BY_BUILD`. Actual render/visual-review observations belong in a separate receipt bound to the output hashes; the generator cannot manufacture an observation. PDF internal navigation is provided, but no PDF/UA claim is made. DOCX pagination is verified in the stated renderer, not every version of Word. Manual edits require updating fields and rerendering. Dependencies are pinned to the executed environment; byte identity is not promised across arbitrary library versions.

Assembler: **ZZ-IRIDIUM-Q2B9 / GPT-6 Astra Pro**. Original commercial/exhibit authors retain their existing repository attribution.
