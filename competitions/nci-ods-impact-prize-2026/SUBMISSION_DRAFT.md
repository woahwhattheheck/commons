# Track-1 submission carrier — ReuseLedger

**Status: DRAFT / NOT SUBMITTED**

Reconcile this material to the live official form before entry. It deliberately does not invent fields hidden behind the currently inaccessible detailed NIH challenge page.

## Working title

**ReuseLedger: Make the complete research-output graph reusable, not just discoverable**

## Opportunity / gap

Cancer research results rarely consist of one object. A reusable result may depend on a dataset, code version, model, protocol, analysis workflow, publication, and access or rights statements distributed across different repositories. Each object can be individually “shared” while a new user still has to reconstruct which exact versions belong together, what can be reused, what is restricted, and what dependencies are missing.

The proposed gap is therefore not “build another data repository.” It is the last-mile handoff between existing repositories: a compact, machine-checkable reuse packet that binds related research outputs into one explicit dependency graph and makes missing reuse conditions visible before a project calls the bundle ready.

## Proposed idea

ReuseLedger is an open, repository-agnostic metadata compiler and verifier. A research team, repository, core facility, or community curator provides a small manifest listing the research outputs behind a result. Each entry names a persistent or stable identifier, output type, HTTPS landing page, access state, license or rights statement, data-use/access statement when relevant, optional byte-level fixity, and dependencies on other outputs.

The compiler produces a canonical graph of the linked outputs, deterministic reuse-readiness findings, exact source-manifest and semantic hashes, a tamper-evident packet another system can verify, and a human-readable report explaining blockers and warnings.

The prototype intentionally does not copy patient data or controlled datasets. It packages metadata and provenance around outputs wherever they already live. That makes the concept compatible with institutional repositories, domain repositories, Git/DOI software archives, protocols, publications, and restricted resources whose metadata can be shared while access remains appropriately controlled.

## Why this could matter

A machine-readable output graph makes common release failures observable:

- a publication points to data but not the exact analysis software version;
- code is public but no reuse license or immutable release is recorded;
- a controlled dataset is listed without a clear access/data-use statement;
- a model or workflow depends on an output that is not actually enumerated;
- a project updates one artifact but cannot show whether its reuse packet changed.

The operational proposition is simple: turn “please document everything needed to reuse this work” into a deterministic check that can run before publication, repository deposit, handoff, or archival release.

## Equity and broad reuse

The design does not require a new proprietary platform or paid API. A small JSON file and standard-library verifier can be produced and consumed locally. That lowers infrastructure barriers for less-resourced laboratories, librarians, patient advocates, citizen scientists, and downstream researchers who otherwise have to manually chase relationships across project pages.

Equity benefits must be tested rather than asserted. A future evaluation should include users with different levels of repository and computational experience and measure whether the packet reduces reconstruction failures without adding unreasonable author burden.

## Evaluation plan

1. Sample heterogeneous public cancer-research projects with linked data, software, protocols, models, and publications.
2. Ask independent curators to construct ReuseLedger manifests from published information and record missing/ambiguous fields.
3. Measure inter-curator agreement, manifest completion time, unresolved dependency count, and verifier findings.
4. Give new users either ordinary project landing materials or the ReuseLedger packet and compare exact-output identification success and time.
5. Publish fixtures, scoring scripts, failure taxonomy, and negative results so the concept can be assessed even if it does not improve reuse.
6. Iterate the schema against repository/librarian feedback instead of hard-coding one institution's workflow.

No numerical improvement is claimed before such a study is run.

## Interoperability / adoption path

ReuseLedger should map outward rather than become a competing metadata universe. Future adapters can translate common fields to and from DataCite and research-object packaging conventions while keeping repository-native identifiers authoritative. A repository or CI system could run the verifier at release time; a project page could link the packet; a search/index system could consume the dependency graph; and an archive could retain the packet beside existing deposits.

The smallest useful adoption unit is one project and one static manifest, so an organization can experiment without migrating data or granting a new service access to controlled assets.

## Prototype evidence

The checked-in prototype demonstrates deterministic normalization, dependency/cycle validation, exact-key/type fences, reuse license/data-use/fixity findings, byte and semantic hashing, tamper detection, exact-manifest verification, human-readable reporting, hostile tests, and a fail-closed external-submission gate. The example fixture is synthetic and contains no participant or clinical data.

The validated carrier test receipt is 15/15 passing under normal Python and 15/15 under `python -O`; the checked-in readiness gate remains intentionally blocked.

## Limits / risks

- Metadata quality still depends on truthful, knowledgeable curators.
- License/right statements can be complex; the prototype records them but does not provide legal advice.
- Fixity proves byte identity, not scientific correctness.
- Access restrictions and privacy/consent rules remain governed by the authoritative repository, institution, study, and applicable policy.
- A lightweight schema becomes burdensome if it duplicates mature repository metadata; adapters and minimal required fields are preferable to a central replacement.
- The proposal requires human review and live-rule reconciliation before submission. It is not an autonomous clinical or regulatory system.

## Human contribution / disclosure boundary

AI-assisted engineering and drafting were used to accelerate this carrier. Before external submission, a human entrant must substantively review, edit, and own the problem framing, engineering claims, evidence interpretation, and final narrative; confirm eligibility; and follow the competition's exact disclosure and legal requirements.

## Current external truth

No NCI registration, terms acceptance, submission, judging outcome, prize, payment, or revenue is claimed by this repository state.
