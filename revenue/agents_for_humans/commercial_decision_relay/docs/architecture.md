# Architecture

```mermaid
flowchart LR
    A[Normalized offer/reply evidence] --> B[Strands orchestration agent]
    B --> C[ingest_batch tool]
    C --> D[Deterministic evidence engine]
    B --> E[reconcile_evidence tool]
    E --> D
    D --> F[All-false-authority receipt]
    F --> G{Decision queue}
    G -->|routine| H[Stay quiet]
    G -->|exact accept / counter / ambiguity / expiry / conflict| I[Human decision card]
    B --> J[verify_current_receipt tool]
    J --> D
    K[Audit hooks] -. hash-only tool audit .-> B
    I --> L[Human closer]
    L -. no execution capability .-> M[External contracting / payment systems]
```

## Trust and authority boundary

The model never determines commercial truth. Strands selects deterministic tools; the tools validate normalized evidence and produce a receipt. `HUMAN_CLOSING_READY` means only that a human-reviewed response exactly matches the current offer before expiry. The relay has no capability to sign, execute a contract, create checkout/invoices, charge, start fulfillment, or recognize revenue.

The independent receipt digest and source batch are separate trust inputs during verification. The receipt's own SHA-256 is only an integrity checksum, never authenticity by itself.
