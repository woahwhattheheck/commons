#!/usr/bin/env python3
"""Canonical right-now revenue compiler with credential-host Stripe authority.

The frozen core preserves the historical compiler and replay contracts. Current
checkout truth is authorized only by a fresh Stripe readback emitted by a fixed,
host-owned collector outside the repository trust domain. Repository-retained
receipts remain audit evidence only and cannot mint current provider truth.
Human reply and scope-acceptance truth is captured from one canonical source
generation and bound into the final control manifest.
"""
