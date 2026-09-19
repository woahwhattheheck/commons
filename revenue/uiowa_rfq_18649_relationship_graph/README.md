# UIOWA-104 — finding-to-source relationship graph

Status: SYNTHETIC REVIEWER AID / NOT A UNIVERSITY FINDING

This component renders the merged UIOWA-093 traceability rehearsal as a portable, clickable relationship graph.

## Canonical source bundle

revenue/uiowa_rfq_18649_traceability_rehearsal/

Source files consumed:
- evidence.csv — exact evidence locators and observation text
- findings.csv — finding-to-evidence links
- recommendations.csv — recommendation-to-finding links
- trace-map.csv — report statements and locations

No source IDs are renumbered. Graph node IDs are namespaced wrappers around the original IDs.

## Relationship chain

The graph makes the chain explicit:

recommendation → finding → observation → evidence record → exact source locator

Because UIOWA-093 stores observation text directly on each evidence row rather than assigning a separate observation ID, UIOWA-104 uses deterministic observation node IDs of the form OBS:E-001 while retaining the original E-001 evidence identifier unchanged.

## Counter-evidence

graph_annotations.json assigns roles to evidence relationships without changing the underlying source rows.

For F-002, E-006 is shown as counter-evidence to an over-broad claim that no checking occurs: the interview recalls periodic manual checking, while F-002 is specifically limited to the absence of retained end-to-end propagation evidence. The graph keeps both truths visible.

## Unsupported-link demonstration

demo_unsupported_links.json adds one clearly labeled DEMO-only recommendation pointing to a missing finding ID. The static example intentionally renders a placeholder missing node and dotted edge instead of dropping the bad link.

The canonical graph without the demo file contains no missing nodes.

## Portable static example

examples/graph.html contains all graph data, CSS, and JavaScript inline. It has no CDN, font, analytics, fetch, or network dependency. Clicking a node shows its raw details, evidence limits, report references, or exact synthetic source locator.

examples/graph.json is the machine-readable companion.

## Run

    python3 build_graph.py --out /tmp/uiowa104
    python3 build_graph.py --demo-links demo_unsupported_links.json --out examples
    python3 -m unittest -v tests/test_graph.py

The first command builds only canonical UIOWA-093 links. The second includes the deliberate unsupported-link demonstration.

## Guardrails

- Synthetic rehearsal only.
- Missing links are visible, never silently discarded.
- Counter-evidence is preserved, not resolved by presentation logic.
- Exact synthetic source locators are displayed but are not transformed into real customer links.
- The graph does not create findings, recommendations, maturity scores, compliance conclusions, or approval authority.
