# UIOWA-130 — acceptance criteria to artifact index

> **ARTIFACT CONFORMANCE EVIDENCE ONLY. The workshare this index refers to is PROPOSED / NOT ACCEPTED. Nothing here represents that the University of Iowa accepted any conclusion, that a subcontract was executed, or that any payment occurred. Supporting fixtures are synthetic and are not University findings.**

Source of the criteria: `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` @ sha256 `f6bc85c1d7d8f575…` — commercial status **PROPOSED / NOT ACCEPTED**. 17 numbered acceptance criteria and 20 deliverable items were extracted from that file, not transcribed by hand.

## How to read the status column

| Status | Meaning |
| --- | --- |
| `DEMONSTRABLE` | A check ran against a real artifact and passed. The observed value is recorded below. |
| `PARTIAL` | Some of the criterion is shown by an artifact; the rest is not. |
| `NOT_DEMONSTRATED` | A check ran and **failed**. The artifact exists and does not meet the criterion. |
| `NEEDS_ENGAGEMENT_EVIDENCE` | No file in this repository can demonstrate it. It needs a prime, a review window, or real University evidence. |
| `UNMAPPED` | No binding, or the bound artifacts are not on disk. |

Criterion tally: **DEMONSTRABLE** 11, **PARTIAL** 4, **NOT_DEMONSTRATED** 0, **NEEDS_ENGAGEMENT_EVIDENCE** 2, **UNMAPPED** 0.

## 1. Acceptance criteria

| Criterion | Package | Status | Basis |
| --- | --- | --- | --- |
| `AC-5.1.1` | 5.1 | **DEMONSTRABLE** | 2 passed, 0 failed, 0 unavailable |
| `AC-5.1.2` | 5.1 | **DEMONSTRABLE** | 1 passed, 0 failed, 0 unavailable |
| `AC-5.1.3` | 5.1 | **PARTIAL** | 1 passed, 1 failed, 0 unavailable |
| `AC-5.1.4` | 5.1 | **DEMONSTRABLE** | 2 passed, 0 failed, 0 unavailable |
| `AC-5.1.5` | 5.1 | **PARTIAL** | 1 passed, 1 failed, 0 unavailable |
| `AC-5.2.1` | 5.2 | **DEMONSTRABLE** | 1 passed, 0 failed, 0 unavailable |
| `AC-5.2.2` | 5.2 | **DEMONSTRABLE** | 2 passed, 0 failed, 0 unavailable |
| `AC-5.2.3` | 5.2 | **DEMONSTRABLE** | 3 passed, 0 failed, 0 unavailable |
| `AC-5.2.4` | 5.2 | **DEMONSTRABLE** | 1 passed, 0 failed, 0 unavailable |
| `AC-5.2.5` | 5.2 | **DEMONSTRABLE** | 2 passed, 0 failed, 0 unavailable |
| `AC-5.2.6` | 5.2 | **NEEDS_ENGAGEMENT_EVIDENCE** | no artifact in this repository can demonstrate this criterion |
| `AC-5.3.1` | 5.3 | **PARTIAL** | 1 passed, 1 failed, 0 unavailable |
| `AC-5.3.2` | 5.3 | **DEMONSTRABLE** | 1 passed, 0 failed, 0 unavailable |
| `AC-5.3.3` | 5.3 | **DEMONSTRABLE** | 2 passed, 0 failed, 0 unavailable |
| `AC-5.3.4` | 5.3 | **NEEDS_ENGAGEMENT_EVIDENCE** | no artifact in this repository can demonstrate this criterion |
| `AC-5.3.5` | 5.3 | **DEMONSTRABLE** | 2 passed, 0 failed, 0 unavailable |
| `AC-5.3.6` | 5.3 | **PARTIAL** | 1 passed, 0 failed, 0 unavailable; part of this criterion still needs engagement evidence |

## 2. Each criterion, with what was actually observed

### `AC-5.1.1` — DEMONSTRABLE

> the scope matrix explicitly covers all three identified system groups and all four technical dimensions

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| twelve-cell frame in the rehearsal matrix | `uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv` | **PASS** | all 12 cells present across 12 rows |
| twelve-cell frame in the 091 coverage matrix | `uiowa_rfq_18649_synthetic_collection/coverage_matrix.csv` | **PASS** | all 12 cells present across 12 rows |

### `AC-5.1.2` — DEMONSTRABLE

> requested source classes are mapped to assessment cells rather than collected without purpose

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| each evidence row names its source and its cell | `uiowa_rfq_18649_intake_rehearsal/artifacts/evidence_register.csv` | **PASS** | 4/4 concepts have a column (cell_area->area, cell_group->group, locator->locator, source->source_id) |

### `AC-5.1.3` — PARTIAL

> the source-register schema can identify source, custodian/owner, evidence reference, authorization/provenance, observation/currentness, and content digest

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| rehearsal source register schema | `uiowa_rfq_18649_intake_rehearsal/artifacts/source_register.csv` | **PASS** | 6/6 concepts have a column (authorization_or_provenance->authorization_basis, content_digest->content_sha256, custodian_or_owner->custodian_role, evidence_reference->path, observation_currentness->captured_at, source->source_id) |
| workshare synthetic evidence register schema | `uiowa_rfq_18649_workshare/methodology/23-synthetic-evidence-register.csv` | **FAIL** | 4/6 concepts have a column (authorization_or_provenance->enumerator_authority, evidence_reference->source_ref, observation_currentness->captured_at, source->evidence_id); NO COLUMN FOR: content_digest, custodian_or_owner |

### `AC-5.1.4` — DEMONSTRABLE

> missing or unavailable evidence is represented as a gap/HOLD dependency, not a fabricated observation

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| unsupported cells carry an explicit state | `uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv` | **PASS** | observed ['CONFLICT', 'DEMONSTRATED_STRENGTH', 'MIXED', 'OBSERVED_GAP', 'PARTIAL', 'UNKNOWN'] |
| the report states what UNKNOWN does not mean | `uiowa_rfq_18649_intake_rehearsal/artifacts/REHEARSAL_REPORT.md` | **PASS** | all 1 required phrase(s) present |

### `AC-5.1.5` — PARTIAL

> known prime-owned and buyer/University-owned dependencies are separately identified.

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| University-owned inputs are listed as UNKNOWN | `uiowa_rfq_18649_intake_rehearsal/README.md` | **PASS** | all 1 required phrase(s) present |
| prime-owned dependencies are separately identified | `uiowa_rfq_18649_intake_rehearsal/README.md` | **FAIL** | phrase(s) absent: ['prime-owned'] |

Still needs engagement evidence:

- The prime's own dependency list. This lane can show University-owned inputs; the prime-owned half needs the prime.

### `AC-5.2.1` — DEMONSTRABLE

> every populated technical conclusion can be traced to one or more source IDs in the delivered evidence register

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| conclusions carry source id + locator + version | `uiowa_rfq_18649_intake_rehearsal/artifacts/evidence_register.csv` | **PASS** | 5/5 concepts have a column (conclusion->observation_id, digest->content_sha256, locator->locator, source->source_id, version->source_version) |

### `AC-5.2.2` — DEMONSTRABLE

> the report covers the full 12-cell assessment frame, using explicit HOLD states for unsupported cells rather than implied completion

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| all twelve cells present | `uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv` | **PASS** | all 12 cells present across 12 rows |
| explicit HOLD-equivalent states are used | `uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv` | **PASS** | observed ['CONFLICT', 'DEMONSTRATED_STRENGTH', 'MIXED', 'OBSERVED_GAP', 'PARTIAL', 'UNKNOWN'] |

### `AC-5.2.3` — DEMONSTRABLE

> missing, stale, conflicting, or untrusted evidence is visibly bounded and cannot silently promote a cell to a supported state

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| outstanding evidence cannot read as supported | `uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv` | **PASS** | 1 row(s) carry outstanding evidence; none claims ['DEMONSTRATED_STRENGTH'] |
| conflicting evidence stays visible as conflict | `uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv` | **PASS** | observed ['CONFLICT', 'DEMONSTRATED_STRENGTH', 'MIXED', 'OBSERVED_GAP', 'PARTIAL', 'UNKNOWN'] |
| malformed-input diagnostics are delivered | `uiowa_rfq_18649_intake_rehearsal/artifacts/intake_diagnostics.csv` | **PASS** | uiowa_rfq_18649_intake_rehearsal/artifacts/intake_diagnostics.csv present, 1047 bytes |

### `AC-5.2.4` — DEMONSTRABLE

> source-universe/currentness checks and deterministic recompilation checks complete for the delivered draft generation, or the package explicitly reports the exact blocker preventing a current trusted result

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| deterministic recompilation of the delivered generation | `python3 rehearse_intake.py --collection sources --out artifacts --check-digest` | **PASS** | exit 0; REPRODUCIBLE: 6 artifacts match the recorded digests in artifacts/RUN_DIGEST.json |

### `AC-5.2.5` — DEMONSTRABLE

> draft findings and roadmap inputs remain within the technical workshare and do not claim bidder submission, contract, legal/compliance certification, award, final University-facing recommendation authority, or authority to recommend/endorse a specific commercial product or vendor

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| no authority the workshare does not hold | `uiowa_rfq_18649_intake_rehearsal/artifacts/REHEARSAL_REPORT.md` | **PASS** | none of the 5 forbidden phrases appear |
| scope limits are stated in the delivered report | `uiowa_rfq_18649_intake_rehearsal/artifacts/REHEARSAL_REPORT.md` | **PASS** | all 2 required phrase(s) present |

### `AC-5.2.6` — NEEDS_ENGAGEMENT_EVIDENCE

> prime review comments received during the agreed review window are either incorporated when they correct TJLabs artifact nonconformance, or recorded as a bounded decision/open item when they require prime judgment, new evidence, or scope change.

Still needs engagement evidence:

- A prospective prime, an agreed review window, and actual review comments. No file in this repository can demonstrate that comments were incorporated or recorded, because no comments have been received.
- UIOWA-094 builds the review/revision workflow; a rehearsal of it is not evidence that a real prime review occurred.

### `AC-5.3.1` — PARTIAL

> the delivered evidence register, technical matrix, findings/roadmap inputs, limitations, change log, and reproducibility/currentness material identify one coherent final generation

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| one generation identified by artifact digests | `uiowa_rfq_18649_intake_rehearsal/artifacts/RUN_DIGEST.json` | **PASS** | key(s) present: ['artifact_sha256'] |
| change log for the delivered generation | `uiowa_rfq_18649_intake_rehearsal/artifacts/CHANGE_LOG.md` | **FAIL** | uiowa_rfq_18649_intake_rehearsal/artifacts/CHANGE_LOG.md not present |

Still needs engagement evidence:

- A change log across generations requires more than one delivered generation. Only one exists.

### `AC-5.3.2` — DEMONSTRABLE

> every supported technical conclusion remains traceable to the delivered evidence universe

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| supported conclusions resolve to the evidence universe | `uiowa_rfq_18649_intake_rehearsal/artifacts/evidence_register.csv` | **PASS** | 3/3 concepts have a column (conclusion->observation_id, resolution->source_resolution, source->source_id) |

### `AC-5.3.3` — DEMONSTRABLE

> unresolved missing/stale/conflicting/untrusted evidence remains explicit rather than being rewritten as verified evidence

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| unresolved evidence is not rewritten as verified | `uiowa_rfq_18649_intake_rehearsal/artifacts/assessment_matrix.csv` | **PASS** | 1 row(s) carry outstanding evidence; none claims ['DEMONSTRATED_STRENGTH', 'OBSERVED_GAP'] |
| source resolution states are carried through | `uiowa_rfq_18649_intake_rehearsal/artifacts/source_register.csv` | **PASS** | observed ['RESOLVED', 'UNRESOLVED_MISSING'] |

### `AC-5.3.4` — NEEDS_ENGAGEMENT_EVIDENCE

> corrections for genuine TJLabs artifact nonconformance identified during acceptance review have been applied or a specific unresolved blocker has been documented

Still needs engagement evidence:

- An acceptance review by the prospective prime. Nothing in this repository can show that a nonconformance was identified and cured, because no acceptance review has taken place.

### `AC-5.3.5` — DEMONSTRABLE

> the final package contains no unsupported representation that the University accepted a conclusion, that Clark's Consulting has executed a subcontract, or that payment/revenue occurred

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| no claim of University acceptance, subcontract or payment | `uiowa_rfq_18649_intake_rehearsal/artifacts/REHEARSAL_REPORT.md` | **PASS** | none of the 7 forbidden phrases appear |
| the exhibit itself records PROPOSED / NOT ACCEPTED | `uiowa_rfq_18649_workshare/ACCEPTANCE_EXHIBIT.md` | **PASS** | all 1 required phrase(s) present |

### `AC-5.3.6` — PARTIAL

> the prime can independently identify what is complete, what remains held, what changed from draft, and which decisions remain prime-owned.

| Check | Target | Outcome | Observed |
| --- | --- | --- | --- |
| delivered material separates working from draft | `uiowa_rfq_18649_intake_rehearsal/README.md` | **PASS** | all 2 required phrase(s) present |

Still needs engagement evidence:

- 'What changed from draft' needs a draft and a final generation. Only one generation exists, so the changed-since-draft half of this criterion is not demonstrable yet.

## 3. Deliverable items

Deliverable tally: **DEMONSTRABLE** 15, **PARTIAL** 2, **NOT_DEMONSTRATED** 2, **NEEDS_ENGAGEMENT_EVIDENCE** 1, **UNMAPPED** 0.

| Item | Section | Status | Text |
| --- | --- | --- | --- |
| `DL-4.1.1` | 4.1 | **DEMONSTRABLE** | a 12-cell scope matrix covering ESS, RIS, and IAM across the four technical dimensions |
| `DL-4.1.2` | 4.1 | **DEMONSTRABLE** | a source-register structure with stable source IDs, source kind, source owner/custodian, |
| `DL-4.1.3` | 4.1 | **DEMONSTRABLE** | an evidence-request map showing which source classes are expected to support which asses |
| `DL-4.1.4` | 4.1 | **DEMONSTRABLE** | explicit markers for missing, stale, conflicting, untrusted, or not-yet-authorized evide |
| `DL-4.1.5` | 4.1 | **DEMONSTRABLE** | the current artifact-generation / authority-generation identifier used by the determinis |
| `DL-4.1.6` | 4.1 | **PARTIAL** | a dependency list for prime or University inputs that remain outstanding. |
| `DL-4.2.1` | 4.2 | **DEMONSTRABLE** | populated evidence register |
| `DL-4.2.2` | 4.2 | **DEMONSTRABLE** | deterministic 12-cell maturity/gap matrix or explicit HOLD states where authority is mis |
| `DL-4.2.3` | 4.2 | **DEMONSTRABLE** | draft technical findings tied to source IDs and the applicable assessment cell |
| `DL-4.2.4` | 4.2 | **DEMONSTRABLE** | prioritized, phased practice/process roadmap inputs suitable for prime review, excluding |
| `DL-4.2.5` | 4.2 | **DEMONSTRABLE** | reproducibility/currentness receipt material for the compiled technical package |
| `DL-4.2.6` | 4.2 | **DEMONSTRABLE** | a limitations/dependencies section identifying unresolved evidence gaps, source conflict |
| `DL-4.2.7` | 4.2 | **NOT_DEMONSTRATED** | a change log identifying material changes from the kickoff frame. |
| `DL-4.3.1` | 4.3 | **DEMONSTRABLE** | final evidence register for the evidence universe actually authorized and received |
| `DL-4.3.2` | 4.3 | **DEMONSTRABLE** | final deterministic 12-cell technical matrix with supported states and explicit HOLD sta |
| `DL-4.3.3` | 4.3 | **PARTIAL** | reconciled technical findings and prioritized roadmap matrices/inputs within TJLabs' wor |
| `DL-4.3.4` | 4.3 | **DEMONSTRABLE** | final limitations, unresolved-dependency, and evidence-conflict register |
| `DL-4.3.5` | 4.3 | **NOT_DEMONSTRATED** | final artifact change log |
| `DL-4.3.6` | 4.3 | **DEMONSTRABLE** | currentness/reproducibility verification material for the delivered generation |
| `DL-4.3.7` | 4.3 | **NEEDS_ENGAGEMENT_EVIDENCE** | corrections to genuine nonconformance in TJLabs-authored artifacts identified during acc |

## 4. Checked sample delivery packet

`output/sample_packet/` holds **9 files**, each included only because a check against it returned PASS. 2 bound artifact(s) were excluded because their check did not pass; they are listed in `MANIFEST.json` with the reason rather than dropped.

## 5. What this index does not say

- It does not say the workshare was accepted. The exhibit reads **PROPOSED / NOT ACCEPTED**.
- It does not say the University agreed with anything, that a subcontract exists, or that any payment occurred.
- A `DEMONSTRABLE` criterion means an artifact met a stated condition. It is not a score, a rating, a certification, or a professional judgement.
- Supporting fixtures in the bound lanes are synthetic. No real University record has been observed.
