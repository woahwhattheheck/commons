#!/usr/bin/env python3
"""EvidenceAAR: deterministic, evidence-bound offline Digital Scribe prototype.

This module deliberately has no network/provider code. It consumes a bounded
strict-JSON event packet, corrects per-source clock offsets, segments a
timeline, builds evidence-linked AAR claims, records contradictions/coverage,
and emits deterministic JSON/Markdown/HTML plus a content-addressed receipt.

Authority ceiling: synthetic/offline evaluation only. Nothing here registers,
submits, contacts a sponsor, processes restricted exercise data, or claims an
award/payment.
"""
