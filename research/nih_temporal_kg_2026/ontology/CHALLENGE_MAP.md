# NIH “It’s About Time” — ontology/interoperability proof map

Official challenge page: https://www.nih.gov/challenges/its-about-time-temporal-reasoning-biomedical-knowledge-graphs-challenge

This map records what the local interoperability profile proves and what remains missing. It is not a challenge submission, eligibility decision, sponsor interpretation, or claim of biomedical performance.

## Why this lane exists

The parent temporal engine and its static-vs-temporal synthetic benchmark already exercise bitemporal validity, knowledge cutoffs, append-only correction history, future-leakage prevention, and time-respecting paths. Their own challenge map identified RDF/OWL/PROV integration and ontology-version provenance as a separate next gate.

The NIH Phase-1 rubric gives ontology rigor and interoperability independent weight. A concept therefore needs more than a private JSON schema: it needs an inspectable mapping to existing temporal/provenance/biomedical graph conventions and machine-checkable invariants without overstating what those mappings prove.

## Criterion → evidence → remaining proof

| Challenge need | Evidence in this directory | Missing proof before external claim |
| --- | --- | --- |
| Existing temporal ontology use | Validity is represented with OWL-Time `ProperInterval`, `hasBeginning`, optional `hasEnd`, and typed instants | Independent semantic review against the exact challenge ontology expectations and any official starter schema |
| Evolving-evidence provenance | Immutable facts/corrections use PROV-O entity, derivation, and generation-time IRIs; source IDs and digests are retained | Authenticated publisher/source registry and realistic biomedical provenance chains |
| Biolink consistency | Strict `biolink:*` predicate lexemes map deterministically to canonical Biolink vocabulary IRIs while original lexemes remain bound | Pin and validate against a specific released Biolink Model; validate subject/object categories and predicate domain/range |
| Logical/machine-verifiable axioms | Local classes/properties, subclass relations, functional properties, and key domain/range statements are emitted and required on import | External OWL reasoner/SHACL evaluation and a proof that the chosen axioms support the official reasoning tasks |
| Semantic preservation | Exact profile-only import reconstructs canonical fact/event IDs and byte-identical temporal JSONL | Interchange tests against independent RDF libraries and official challenge tooling/data |
| Temporal correctness | Valid and knowledge clocks remain separate; finite/open interval shape and correction topology are enforced | Real biomedical tasks where these distinctions improve measured correctness over static and other temporal baselines |
| Reproducibility | Sorted canonical N-Triples plus receipt binding data, adapter, engine, counts, and round trip | Reproducible container/environment manifest and independent rerun by another team |
| Hostile-input safety | Fail-closed parser/profile; no blank nodes; exact cardinality/type/identity/digest checks; regular-file ingress | Broader parser differential testing/fuzzing and resource-exhaustion characterization at challenge scale |

## Promotion gates

This profile may be promoted from **engineering interoperability seed** only after all of the following are independently evidenced:

1. a specific Biolink release and ontology/version manifest are pinned by immutable digest;
2. at least one public, non-PHI biomedical/evidence-evolution corpus is mapped without inventing clinical conclusions;
3. mappings and expected answers are predeclared before benchmark execution;
4. an independent RDF implementation reads the emitted graph and reproduces the profile invariants;
5. an external reasoner or validator checks the intended axioms without introducing unintended entailments;
6. the temporal system is compared with static and relevant temporal baselines on identical tasks;
7. measured gains do not come at the cost of neutral-control accuracy or hidden future leakage;
8. domain experts review the representation and task relevance;
9. official rules, eligibility, registration, participation agreement, and submission format are separately satisfied.

A syntactically successful export is not evidence of biomedical correctness. A content digest is not source authentication. A Biolink IRI is not category/domain/range conformance. A local OWL declaration is not general reasoning completeness.

## Current state

- Local profile: `nih-temporal-kg-ontology/v1`
- Local receipt: `nih-temporal-kg-ontology-conformance/v1`
- Data in tests/examples: synthetic, public, non-PHI
- External registration: not performed by this lane
- External submission: not performed by this lane
- Prize/award/payment/revenue: none claimed
